from pathlib import Path
from typing import Tuple
import numpy as np
import pandas as pd
import pytest

from backend.app.ml.models.isolation_forest import IsolationForestDetector
from backend.app.ml.training.isolation_forest_trainer import IsolationForestTrainer
from backend.app.ml.inference.isolation_forest_predictor import (
    IsolationForestPredictor,
    IsolationForestPrediction,
)
from backend.app.ml.evaluation.isolation_forest_evaluator import IsolationForestEvaluator
from backend.app.ml.registry.model_registry import ModelRegistry
from backend.app.ml.data.preprocessing.pipeline import NetworkDataPipeline
from backend.app.ml.data.loaders.synthetic_loader import SyntheticSampleLoader
from backend.app.services.isolation_forest_service import IsolationForestService


@pytest.fixture
def synthetic_data() -> Tuple[pd.DataFrame, pd.Series, pd.Series]:
    """Generate synthetic network feature matrix and labels."""
    np.random.seed(42)
    n_samples = 40
    n_features = 6

    # Normal samples centered around 0.0
    X_normal = np.random.normal(loc=0.0, scale=1.0, size=(25, n_features))
    # Known attack samples shifted to +4.0
    X_known_attack = np.random.normal(loc=4.0, scale=1.0, size=(10, n_features))
    # Unseen zero-day attack samples shifted to -5.0
    X_unseen_attack = np.random.normal(loc=-5.0, scale=1.2, size=(5, n_features))

    X_all = np.vstack([X_normal, X_known_attack, X_unseen_attack]).astype(np.float32)
    feature_names = [f"metric_{i}" for i in range(n_features)]
    X_df = pd.DataFrame(X_all, columns=feature_names)

    # Binary labels (0 = normal, 1 = attack)
    y_binary = pd.Series([0] * 25 + [1] * 15)
    # Category labels
    y_category = pd.Series(["normal"] * 25 + ["dos"] * 10 + ["zero_day_unseen"] * 5)

    return X_df, y_binary, y_category


# ---------------------------------------------------------------------------
# 1. Model Initialization & Hyperparameters
# ---------------------------------------------------------------------------
def test_isolation_forest_initialization():
    """Verify hyperparameter configuration and default states."""
    detector = IsolationForestDetector(
        n_estimators=120,
        contamination=0.03,
        random_state=123,
        anomaly_threshold=65.0,
    )
    assert detector.n_estimators == 120
    assert detector.contamination == 0.03
    assert detector.random_state == 123
    assert detector.anomaly_threshold == 65.0
    assert not detector.is_trained
    assert detector.model is None


# ---------------------------------------------------------------------------
# 2. Training on Normal Traffic Only
# ---------------------------------------------------------------------------
def test_training_on_normal_traffic_only(synthetic_data):
    """Verify Isolation Forest fits properly on normal baseline traffic."""
    X_df, y_binary, _ = synthetic_data
    normal_mask = (y_binary == 0)
    X_normal = X_df[normal_mask]

    detector = IsolationForestDetector(n_estimators=50, random_state=42)
    detector.train(X_normal)

    assert detector.is_trained
    assert detector.model is not None
    assert detector.feature_count_ == len(X_df.columns)
    assert detector.score_min_ < detector.score_max_


# ---------------------------------------------------------------------------
# 3. Model Artifact Saving & Loading
# ---------------------------------------------------------------------------
def test_model_artifact_saving_and_loading(synthetic_data, tmp_path: Path):
    """Verify serialization to joblib and exact parameter reload."""
    X_df, y_binary, _ = synthetic_data
    detector = IsolationForestDetector(n_estimators=50, random_state=42)
    detector.train(X_df[y_binary == 0])

    model_file = tmp_path / "test_iso_forest.joblib"
    detector.save(model_file)
    assert model_file.exists()

    reloaded = IsolationForestDetector.load(model_file)
    assert reloaded.is_trained
    assert reloaded.n_estimators == 50
    assert reloaded.feature_count_ == detector.feature_count_

    scores_orig = detector.compute_anomaly_scores(X_df)
    scores_reload = reloaded.compute_anomaly_scores(X_df)
    np.testing.assert_allclose(scores_orig, scores_reload, atol=1e-5)


# ---------------------------------------------------------------------------
# 4. Anomaly Score Normalization (0 - 100 Scale)
# ---------------------------------------------------------------------------
def test_anomaly_score_normalization_bounds(synthetic_data):
    """Verify that transformed anomaly scores are strictly bounded within [0, 100]."""
    X_df, y_binary, _ = synthetic_data
    detector = IsolationForestDetector(n_estimators=50, random_state=42)
    detector.train(X_df[y_binary == 0])

    scores = detector.compute_anomaly_scores(X_df)
    assert isinstance(scores, np.ndarray)
    assert (scores >= 0.0).all()
    assert (scores <= 100.0).all()

    # Normal samples should on average have significantly lower anomaly scores than attack samples
    normal_mean_score = scores[y_binary == 0].mean()
    attack_mean_score = scores[y_binary == 1].mean()
    assert attack_mean_score > normal_mean_score


# ---------------------------------------------------------------------------
# 5. Threshold Decision Behavior
# ---------------------------------------------------------------------------
def test_threshold_decision_behavior(synthetic_data):
    """Verify binary prediction flips correctly based on threshold."""
    X_df, y_binary, _ = synthetic_data
    detector = IsolationForestDetector(n_estimators=50, random_state=42)
    detector.train(X_df[y_binary == 0])

    scores = detector.compute_anomaly_scores(X_df)
    
    # Strict low threshold (almost everything flagged)
    preds_strict = detector.predict_binary(X_df, threshold=10.0)
    assert np.sum(preds_strict == 1) >= np.sum(detector.predict_binary(X_df, threshold=90.0) == 1)

    # Standard threshold
    preds_standard = detector.predict_binary(X_df, threshold=50.0)
    assert len(preds_standard) == len(X_df)


# ---------------------------------------------------------------------------
# 6. Single-Record & Batch Prediction Integration
# ---------------------------------------------------------------------------
def test_predictor_single_and_batch_inference(synthetic_data, tmp_path: Path):
    """Verify IsolationForestPredictor handles both single-flow and batch inference."""
    X_df, y_binary, _ = synthetic_data
    
    # 1. Prepare and save mock pipeline
    pipeline = NetworkDataPipeline(dataset_name="test_ds", scaling_strategy="standard", selection_strategy="none")
    pipeline.fit(X_df)
    pipe_dir = pipeline.save(tmp_path / "preprocessing" / "test_ds")

    # 2. Train and save model
    detector = IsolationForestDetector(n_estimators=50, random_state=42)
    detector.train(pipeline.transform(X_df[y_binary == 0]))
    model_file = tmp_path / "models" / "isolation_forest_test_ds_v1.0.0.joblib"
    detector.save(model_file)

    # 3. Instantiate predictor
    predictor = IsolationForestPredictor(
        dataset_name="test_ds",
        model_path=model_file,
        preprocessing_dir=pipe_dir,
    )
    predictor.load()

    # Test single-record prediction
    single_record = X_df.iloc[0].to_dict()
    pred_single = predictor.predict_single(single_record)
    assert isinstance(pred_single, IsolationForestPrediction)
    assert pred_single.model_name == "isolation_forest"
    assert pred_single.prediction in ("normal", "anomaly")
    assert 0.0 <= pred_single.anomaly_score <= 100.0
    assert pred_single.processing_time_ms >= 0.0

    # Test batch prediction
    batch_preds = predictor.predict_batch(X_df.head(10))
    assert len(batch_preds) == 10
    assert all(isinstance(p, IsolationForestPrediction) for p in batch_preds)


# ---------------------------------------------------------------------------
# 7. Invalid Input & Missing Artifact Handling
# ---------------------------------------------------------------------------
def test_invalid_input_and_error_handling(synthetic_data):
    """Verify proper exceptions on invalid inputs and missing models."""
    detector = IsolationForestDetector()
    
    # Unfitted error
    with pytest.raises(RuntimeError):
        detector.score_samples(np.array([[1.0, 2.0]]))

    # NaN / Inf input error
    X_df, y_bin, _ = synthetic_data
    detector.train(X_df[y_bin == 0])
    
    dirty = np.array([[1.0, np.nan, 3.0, 4.0, 5.0, 6.0]])
    with pytest.raises(ValueError):
        detector.compute_anomaly_scores(dirty)

    # Missing model file error
    missing_pred = IsolationForestPredictor(dataset_name="nonexistent_dataset", model_path="does_not_exist.joblib")
    with pytest.raises(FileNotFoundError):
        missing_pred.load()


# ---------------------------------------------------------------------------
# 8. Model Registry Operations
# ---------------------------------------------------------------------------
def test_model_registry_operations(tmp_path: Path):
    """Verify registry saves, discovers, and filters models."""
    reg_file = tmp_path / "test_registry.json"
    registry = ModelRegistry(registry_file=reg_file)

    registry.register_model(
        model_name="isolation_forest",
        dataset="nsl_kdd",
        version="1.0.0",
        artifact_path="/path/to/model.joblib",
        feature_count=41,
        set_active=True,
    )

    meta = registry.get_model("isolation_forest", dataset="nsl_kdd")
    assert meta is not None
    assert meta["dataset"] == "nsl_kdd"
    assert meta["version"] == "1.0.0"
    assert meta["is_active"] is True

    models_list = registry.list_models(model_name="isolation_forest")
    assert len(models_list) == 1


# ---------------------------------------------------------------------------
# 9. Evaluation Engine & Unseen Zero-Day Metrics
# ---------------------------------------------------------------------------
def test_evaluator_unseen_zero_day_metrics(synthetic_data, tmp_path: Path):
    """Verify calculation of security metrics and unseen zero-day breakdown."""
    X_df, y_binary, y_category = synthetic_data
    detector = IsolationForestDetector(n_estimators=50, random_state=42)
    detector.train(X_df[y_binary == 0])

    report = IsolationForestEvaluator.evaluate(
        detector=detector,
        X_test=X_df,
        y_test_binary=y_binary,
        y_test_category=y_category,
        unseen_categories=["zero_day_unseen"],
        dataset_name="synthetic_test",
        output_dir=tmp_path / "exp",
        generate_plots=False,
    )

    assert "metrics" in report
    assert "accuracy" in report["metrics"]
    assert "precision" in report["metrics"]
    assert "recall_detection_rate" in report["metrics"]
    assert "roc_auc" in report["metrics"]
    assert "zero_day_evaluation" in report
    
    zd = report["zero_day_evaluation"]
    assert "zero_day_unseen" in zd["category_breakdown"]
    assert zd["category_breakdown"]["zero_day_unseen"]["is_unseen_zero_day"] is True


# ---------------------------------------------------------------------------
# 10. Service Layer Integration
# ---------------------------------------------------------------------------
def test_isolation_forest_service_interface(synthetic_data, tmp_path: Path):
    """Verify IsolationForestService provides decoupled prediction."""
    X_df, y_bin, _ = synthetic_data
    
    # Prepare and register pipeline + model
    pipeline = NetworkDataPipeline(dataset_name="service_test", scaling_strategy="standard", selection_strategy="none")
    pipeline.fit(X_df)
    pipe_dir = pipeline.save(tmp_path / "preprocessing" / "service_test")

    detector = IsolationForestDetector(n_estimators=30, random_state=42)
    detector.train(pipeline.transform(X_df[y_bin == 0]))
    model_file = tmp_path / "models" / "isolation_forest_service_test_v1.0.0.joblib"
    detector.save(model_file)

    service = IsolationForestService(default_dataset="service_test")
    predictor = IsolationForestPredictor(
        dataset_name="service_test",
        model_path=model_file,
        preprocessing_dir=pipe_dir,
    )
    service.predictors["service_test"] = predictor

    pred = service.predict_flow(X_df.iloc[0].to_dict(), dataset="service_test")
    assert isinstance(pred, IsolationForestPrediction)
    assert pred.dataset == "service_test"
