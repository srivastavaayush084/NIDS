import pytest
import numpy as np
import pandas as pd
from pathlib import Path
import tempfile
import json

from backend.app.ml.ensemble.schemas import (
    ModelContribution,
    ModelAgreement,
    LatencyBreakdown,
    EnsemblePrediction,
)
from backend.app.ml.ensemble.score_normalizer import ScoreNormalizer
from backend.app.ml.ensemble.severity import SeverityClassifier
from backend.app.ml.ensemble.risk_scorer import EnsembleRiskScorer
from backend.app.ml.ensemble.ensemble_detector import EnsembleDetector
from backend.app.services.ensemble_service import EnsembleService
from backend.app.ml.evaluation.unified_evaluator import UnifiedModelEvaluator
from backend.app.ml.models.isolation_forest import IsolationForestDetector
from backend.app.ml.models.autoencoder import AutoencoderDetector
from backend.app.ml.models.lstm_autoencoder import LSTMAutoencoderDetector
from backend.app.ml.models.random_forest import RandomForestClassifierModel


@pytest.fixture
def synthetic_ensemble_data():
    """Generates synthetic dataset and trained lightweight models for ensemble verification."""
    np.random.seed(42)
    n_samples = 30
    n_features = 6

    # Normal samples (15)
    X_norm = np.random.normal(loc=0.0, scale=0.5, size=(15, n_features))
    y_norm = np.zeros(15, dtype=int)
    cat_norm = ["normal"] * 15

    # Known attack samples (10)
    X_known = np.random.normal(loc=3.0, scale=0.8, size=(10, n_features))
    y_known = np.ones(10, dtype=int)
    cat_known = ["dos"] * 10

    # Unseen zero-day attack samples (5)
    X_unseen = np.random.normal(loc=6.0, scale=1.0, size=(5, n_features))
    y_unseen = np.ones(5, dtype=int)
    cat_unseen = ["zero_day_unseen"] * 5

    X = np.vstack([X_norm, X_known, X_unseen]).astype(np.float32)
    y_binary = np.concatenate([y_norm, y_known, y_unseen])
    y_category = np.concatenate([cat_norm, cat_known, cat_unseen])

    feature_cols = [f"feature_{i}" for i in range(n_features)]
    X_df = pd.DataFrame(X, columns=feature_cols)

    # Train lightweight models
    if_model = IsolationForestDetector(n_estimators=10, random_state=42)
    if_model.train(X[y_binary == 0])

    ae_model = AutoencoderDetector(input_dim=n_features, latent_dim=3, epochs=3, batch_size=4, random_seed=42)
    ae_model.train(X[y_binary == 0])

    lstm_model = LSTMAutoencoderDetector(input_dim=n_features, seq_len=4, encoder_units=8, latent_dim=4, epochs=3, batch_size=2, random_seed=42)
    X_norm_seq = np.random.normal(size=(5, 4, n_features)).astype(np.float32)
    lstm_model.train(X_norm_seq)

    rf_model = RandomForestClassifierModel(n_estimators=10, random_state=42)
    rf_model.train(X, y_binary)

    return {
        "X": X_df,
        "y_binary": pd.Series(y_binary, name="binary"),
        "y_category": pd.Series(y_category, name="category"),
        "unseen_categories": ["zero_day_unseen"],
        "n_features": n_features,
        "if_model": if_model,
        "ae_model": ae_model,
        "lstm_model": lstm_model,
        "rf_model": rf_model,
    }


# ---------------------------------------------------------------------------
# 1. Score Normalization & Direction Handling
# ---------------------------------------------------------------------------
def test_score_normalizer_isolation_forest():
    normalizer = ScoreNormalizer()

    # Case A: Raw decision function where lower = anomalous (e.g. -0.2 -> anomalous, +0.2 -> normal)
    score_anom = normalizer.normalize("isolation_forest", raw_score=-0.2)
    score_norm = normalizer.normalize("isolation_forest", raw_score=0.2)
    assert score_anom > score_norm
    assert 0.0 <= score_anom <= 100.0
    assert 0.0 <= score_norm <= 100.0

    # Case B: Precomputed 0-100 anomaly score with threshold at 60.0
    score_th = normalizer.normalize("isolation_forest", raw_score=60.0, threshold=60.0, method="threshold_relative")
    assert pytest.approx(score_th, 0.1) == 50.0

    score_high = normalizer.normalize("isolation_forest", raw_score=80.0, threshold=60.0, method="threshold_relative")
    assert score_high > 50.0


def test_score_normalizer_reconstruction():
    normalizer = ScoreNormalizer()
    th = 0.05

    # Sub-threshold: error = 0.025 (halfway to threshold) -> risk score should be ~25.0
    score_sub = normalizer.normalize("autoencoder", raw_score=0.025, threshold=th, method="threshold_relative")
    assert pytest.approx(score_sub, 0.1) == 25.0

    # Exact threshold: error = 0.05 -> risk score should be exactly 50.0
    score_th = normalizer.normalize("autoencoder", raw_score=0.05, threshold=th, method="threshold_relative")
    assert pytest.approx(score_th, 0.1) == 50.0

    # Supra-threshold: error = 0.10 -> risk score should be > 50.0
    score_supra = normalizer.normalize("autoencoder", raw_score=0.10, threshold=th, method="threshold_relative")
    assert score_supra > 50.0


def test_score_normalizer_random_forest():
    normalizer = ScoreNormalizer()
    th = 0.50

    # Probability at threshold 0.50 maps to 50.0
    score_th = normalizer.normalize("random_forest", raw_score=0.50, threshold=th, method="threshold_relative")
    assert pytest.approx(score_th, 0.1) == 50.0

    # High attack probability 0.90 maps to high risk score
    score_high = normalizer.normalize("random_forest", raw_score=0.90, threshold=th, method="threshold_relative")
    assert score_high >= 80.0


def test_score_normalizer_calibration_save_load():
    normalizer = ScoreNormalizer()
    val_scores = {
        "isolation_forest": [10.0, 20.0, 30.0, 50.0, 75.0],
        "autoencoder": [0.01, 0.02, 0.03, 0.05, 0.12],
        "random_forest": [0.05, 0.10, 0.15, 0.50, 0.95],
    }
    normalizer.calibrate_from_validation(val_scores, thresholds={"isolation_forest": 50.0, "autoencoder": 0.05, "random_forest": 0.5})

    with tempfile.TemporaryDirectory() as temp_dir:
        calib_path = Path(temp_dir) / "calibration.json"
        normalizer.save_calibration(calib_path)
        assert calib_path.exists()

        loaded_norm = ScoreNormalizer.load_calibration(calib_path)
        assert "autoencoder" in loaded_norm.calibration
        assert loaded_norm.calibration["autoencoder"]["threshold"] == 0.05


# ---------------------------------------------------------------------------
# 2. Severity Classification
# ---------------------------------------------------------------------------
def test_severity_classifier():
    classifier = SeverityClassifier(low_max=24.99, medium_max=49.99, high_max=74.99, critical_min=75.0)

    assert classifier.classify(0.0) == "LOW"
    assert classifier.classify(24.99) == "LOW"
    assert classifier.classify(25.0) == "MEDIUM"
    assert classifier.classify(49.99) == "MEDIUM"
    assert classifier.classify(50.0) == "HIGH"
    assert classifier.classify(74.99) == "HIGH"
    assert classifier.classify(75.0) == "CRITICAL"
    assert classifier.classify(100.0) == "CRITICAL"


# ---------------------------------------------------------------------------
# 3. Risk Scorer, Weight Renormalization & Agreement
# ---------------------------------------------------------------------------
def test_risk_scorer_weight_renormalization():
    weights = {
        "isolation_forest": 0.25,
        "autoencoder": 0.25,
        "lstm_autoencoder": 0.25,
        "random_forest": 0.25,
    }
    scorer = EnsembleRiskScorer(weights=weights, decision_threshold=50.0)

    # 4 models all available with normalized score 80.0
    contribs_all = {
        m: ModelContribution(
            model_name=m,
            prediction="attack",
            is_anomaly=True,
            native_score=80.0,
            normalized_score=80.0,
            configured_weight=0.25,
            effective_weight=0.0,
            decision_threshold=50.0,
            is_available=True,
        )
        for m in weights
    }

    pred_all = scorer.aggregate(contribs_all)
    assert pytest.approx(pred_all.risk_score, 0.1) == 80.0
    assert pred_all.is_anomaly is True
    assert pred_all.severity == "CRITICAL"
    assert pred_all.agreement.models_available == 4
    assert pred_all.agreement.agreement_ratio == 1.0

    # 1 model unavailable (e.g. lstm_autoencoder)
    contribs_missing = dict(contribs_all)
    contribs_missing["lstm_autoencoder"] = ModelContribution(
        model_name="lstm_autoencoder",
        prediction="normal",
        is_anomaly=False,
        native_score=0.0,
        normalized_score=0.0,
        configured_weight=0.25,
        effective_weight=0.0,
        decision_threshold=50.0,
        is_available=False,
        error="Sequence window not provided",
    )

    pred_missing = scorer.aggregate(contribs_missing)
    # Remaining 3 models each have score 80.0 -> renormalized risk score should remain 80.0
    assert pytest.approx(pred_missing.risk_score, 0.1) == 80.0
    assert pred_missing.agreement.models_available == 3
    assert "lstm_autoencoder" in pred_missing.missing_models
    assert pred_missing.contributions["isolation_forest"].effective_weight == pytest.approx(0.3333, 0.01)


# ---------------------------------------------------------------------------
# 4. Ensemble Detector Inference (Single-record & Batch)
# ---------------------------------------------------------------------------
def test_ensemble_detector_single_prediction_no_sequence(synthetic_ensemble_data):
    detector = EnsembleDetector(
        isolation_forest=synthetic_ensemble_data["if_model"],
        autoencoder=synthetic_ensemble_data["ae_model"],
        lstm_autoencoder=synthetic_ensemble_data["lstm_model"],
        random_forest=synthetic_ensemble_data["rf_model"],
    )

    # Predict single flow without sequence window
    row = synthetic_ensemble_data["X"].iloc[0]
    pred = detector.predict_single(row)

    assert isinstance(pred, EnsemblePrediction)
    assert 0.0 <= pred.risk_score <= 100.0
    assert pred.severity in ("LOW", "MEDIUM", "HIGH", "CRITICAL")
    assert "lstm_autoencoder" in pred.missing_models  # Marked missing gracefully without error
    assert len(pred.participating_models) == 3


def test_ensemble_detector_single_prediction_with_sequence(synthetic_ensemble_data):
    detector = EnsembleDetector(
        isolation_forest=synthetic_ensemble_data["if_model"],
        autoencoder=synthetic_ensemble_data["ae_model"],
        lstm_autoencoder=synthetic_ensemble_data["lstm_model"],
        random_forest=synthetic_ensemble_data["rf_model"],
    )

    # Predict single flow with sequence window provided
    row = synthetic_ensemble_data["X"].iloc[5]
    seq_win = synthetic_ensemble_data["X"].iloc[0:4].to_numpy()
    pred = detector.predict_single(row, sequence_window=seq_win)

    assert isinstance(pred, EnsemblePrediction)
    assert len(pred.participating_models) == 4
    assert len(pred.missing_models) == 0
    assert "lstm_autoencoder" in pred.contributions
    assert pred.contributions["lstm_autoencoder"].is_available is True


def test_ensemble_detector_batch_prediction(synthetic_ensemble_data):
    detector = EnsembleDetector(
        isolation_forest=synthetic_ensemble_data["if_model"],
        autoencoder=synthetic_ensemble_data["ae_model"],
        lstm_autoencoder=synthetic_ensemble_data["lstm_model"],
        random_forest=synthetic_ensemble_data["rf_model"],
    )

    y_preds, risk_scores, pred_objs = detector.predict_batch(synthetic_ensemble_data["X"])

    assert len(y_preds) == len(synthetic_ensemble_data["X"])
    assert len(risk_scores) == len(synthetic_ensemble_data["X"])
    assert len(pred_objs) == len(synthetic_ensemble_data["X"])
    assert np.all((risk_scores >= 0.0) & (risk_scores <= 100.0))


# ---------------------------------------------------------------------------
# 5. Service & Unified Evaluator Integration
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_ensemble_service_sync_and_async(synthetic_ensemble_data):
    service = EnsembleService(default_dataset="synthetic")
    # Manually inject trained detector
    detector = EnsembleDetector(
        isolation_forest=synthetic_ensemble_data["if_model"],
        autoencoder=synthetic_ensemble_data["ae_model"],
        lstm_autoencoder=synthetic_ensemble_data["lstm_model"],
        random_forest=synthetic_ensemble_data["rf_model"],
    )
    service.detectors["synthetic"] = detector

    row = synthetic_ensemble_data["X"].iloc[0]
    pred_sync = service.predict_flow(row, dataset="synthetic")
    assert isinstance(pred_sync, EnsemblePrediction)

    pred_async = await service.predict_flow_async(row, dataset="synthetic")
    assert isinstance(pred_async, EnsemblePrediction)
    assert pred_async.risk_score == pred_sync.risk_score


def test_unified_model_evaluator_ensemble(synthetic_ensemble_data):
    detector = EnsembleDetector(
        isolation_forest=synthetic_ensemble_data["if_model"],
        autoencoder=synthetic_ensemble_data["ae_model"],
        lstm_autoencoder=synthetic_ensemble_data["lstm_model"],
        random_forest=synthetic_ensemble_data["rf_model"],
    )

    res = UnifiedModelEvaluator.evaluate_model(
        model=detector,
        X_test=synthetic_ensemble_data["X"],
        y_test_binary=synthetic_ensemble_data["y_binary"],
        y_test_category=synthetic_ensemble_data["y_category"],
        unseen_categories=synthetic_ensemble_data["unseen_categories"],
        dataset_name="synthetic",
        evaluation_type="all",
    )

    assert res["model_name"] == "ensemble"
    assert "standard_metrics" in res
    assert "scenario_metrics" in res
    assert "unseen_attack" in res["scenario_metrics"]
    assert res["standard_metrics"]["classification"]["accuracy"] is not None
