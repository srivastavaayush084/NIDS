import pytest
import numpy as np
import pandas as pd
from pathlib import Path
import tempfile
import json

from backend.app.ml.evaluation.metrics import StandardizedMetricsCalculator, StandardizedMetrics
from backend.app.ml.evaluation.unified_evaluator import UnifiedModelEvaluator
from backend.app.ml.evaluation.comparison_visualizer import ComparisonVisualizer
from backend.app.ml.evaluation.model_comparator import ModelComparator
from backend.app.ml.models.isolation_forest import IsolationForestDetector
from backend.app.ml.models.autoencoder import AutoencoderDetector
from backend.app.ml.models.lstm_autoencoder import LSTMAutoencoderDetector
from backend.app.ml.models.random_forest import RandomForestClassifierModel


@pytest.fixture
def synthetic_eval_data():
    """Generates synthetic test data with normal, known attack, and unseen zero-day flows."""
    np.random.seed(42)
    n_samples = 30
    n_features = 8

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

    X = np.vstack([X_norm, X_known, X_unseen])
    y_binary = np.concatenate([y_norm, y_known, y_unseen])
    y_category = np.concatenate([cat_norm, cat_known, cat_unseen])

    feature_cols = [f"feature_{i}" for i in range(n_features)]
    X_df = pd.DataFrame(X, columns=feature_cols)

    return {
        "X": X_df,
        "y_binary": pd.Series(y_binary, name="binary"),
        "y_category": pd.Series(y_category, name="category"),
        "unseen_categories": ["zero_day_unseen"],
        "n_features": n_features,
    }


def test_standardized_metrics_calculator_perfect():
    y_true = np.array([0, 0, 1, 1, 0, 1])
    y_pred = np.array([0, 0, 1, 1, 0, 1])
    scores = np.array([0.1, 0.2, 0.8, 0.9, 0.15, 0.85])

    metrics = StandardizedMetricsCalculator.calculate_metrics(
        y_true=y_true,
        y_pred=y_pred,
        continuous_scores=scores,
        inference_time_ms=10.0,
    )

    assert metrics.accuracy == 1.0
    assert metrics.precision == 1.0
    assert metrics.recall == 1.0
    assert metrics.f1_score == 1.0
    assert metrics.roc_auc == 1.0
    assert metrics.false_positive_rate == 0.0
    assert metrics.false_negative_rate == 0.0
    assert metrics.true_positives == 3
    assert metrics.true_negatives == 3
    assert metrics.total_samples == 6


def test_standardized_metrics_missing_class_graceful():
    # Only normal samples (single class)
    y_true = np.array([0, 0, 0, 0])
    y_pred = np.array([0, 0, 0, 0])
    scores = np.array([0.1, 0.2, 0.15, 0.05])

    metrics = StandardizedMetricsCalculator.calculate_metrics(
        y_true=y_true,
        y_pred=y_pred,
        continuous_scores=scores,
        inference_time_ms=5.0,
    )

    assert metrics.accuracy == 1.0
    assert metrics.roc_auc is None  # Undefined for single class
    assert "roc_auc" in metrics.metric_diagnostics
    assert metrics.false_negative_rate is None  # No attack samples present
    assert "false_negative_rate" in metrics.metric_diagnostics


def test_unified_model_evaluator_isolation_forest(synthetic_eval_data):
    X = synthetic_eval_data["X"]
    y_bin = synthetic_eval_data["y_binary"]
    y_cat = synthetic_eval_data["y_category"]
    unseen = synthetic_eval_data["unseen_categories"]

    # Train a quick Isolation Forest on normal samples
    if_model = IsolationForestDetector(n_estimators=20, contamination=0.1, random_state=42)
    if_model.train(X[y_bin == 0])

    res = UnifiedModelEvaluator.evaluate_model(
        model=if_model,
        X_test=X,
        y_test_binary=y_bin,
        y_test_category=y_cat,
        unseen_categories=unseen,
        dataset_name="synthetic",
        evaluation_type="all",
    )

    assert res["model_name"] == "isolation_forest"
    assert "standard_metrics" in res
    assert "scenario_metrics" in res
    assert "known_attack" in res["scenario_metrics"]
    assert "unseen_attack" in res["scenario_metrics"]
    assert "zero_day_unseen" in res["category_breakdown"]
    assert res["category_breakdown"]["zero_day_unseen"]["is_unseen_during_training"] is True


def test_unified_model_evaluator_autoencoder(synthetic_eval_data):
    X = synthetic_eval_data["X"]
    y_bin = synthetic_eval_data["y_binary"]
    y_cat = synthetic_eval_data["y_category"]
    unseen = synthetic_eval_data["unseen_categories"]

    ae_model = AutoencoderDetector(
        input_dim=synthetic_eval_data["n_features"],
        latent_dim=4,
        epochs=5,
        batch_size=8,
        random_seed=42,
    )
    ae_model.train(X[y_bin == 0].to_numpy())

    res = UnifiedModelEvaluator.evaluate_model(
        model=ae_model,
        X_test=X,
        y_test_binary=y_bin,
        y_test_category=y_cat,
        unseen_categories=unseen,
        dataset_name="synthetic",
        evaluation_type="all",
    )

    assert res["model_name"] == "autoencoder"
    assert res["standard_metrics"]["classification"]["accuracy"] is not None
    assert "unseen_attack" in res["scenario_metrics"]


def test_unified_model_evaluator_lstm_autoencoder(synthetic_eval_data):
    X = synthetic_eval_data["X"]
    y_bin = synthetic_eval_data["y_binary"]
    y_cat = synthetic_eval_data["y_category"]
    unseen = synthetic_eval_data["unseen_categories"]

    lstm_model = LSTMAutoencoderDetector(
        input_dim=synthetic_eval_data["n_features"],
        seq_len=5,
        encoder_units=16,
        latent_dim=8,
        epochs=3,
        batch_size=2,
        random_seed=42,
    )
    # Fit on sequence representation of normal samples
    X_norm_seq = np.random.normal(size=(5, 5, synthetic_eval_data["n_features"]))
    lstm_model.train(X_norm_seq)

    res = UnifiedModelEvaluator.evaluate_model(
        model=lstm_model,
        X_test=X,
        y_test_binary=y_bin,
        y_test_category=y_cat,
        unseen_categories=unseen,
        dataset_name="synthetic",
        evaluation_type="all",
    )

    assert res["model_name"] == "lstm_autoencoder"
    assert res["input_unit"] == "sequences"
    assert res["standard_metrics"]["classification"]["accuracy"] is not None


def test_unified_model_evaluator_random_forest(synthetic_eval_data):
    X = synthetic_eval_data["X"]
    y_bin = synthetic_eval_data["y_binary"]
    y_cat = synthetic_eval_data["y_category"]
    unseen = synthetic_eval_data["unseen_categories"]

    rf_model = RandomForestClassifierModel(n_estimators=10, random_state=42)
    rf_model.train(X, y_bin)

    res = UnifiedModelEvaluator.evaluate_model(
        model=rf_model,
        X_test=X,
        y_test_binary=y_bin,
        y_test_category=y_cat,
        unseen_categories=unseen,
        dataset_name="synthetic",
        evaluation_type="all",
    )

    assert res["model_name"] == "random_forest"
    assert res["raw_predictions"]["probabilities"] is not None
    assert res["standard_metrics"]["classification"]["recall"] is not None


def test_data_leakage_detection(synthetic_eval_data):
    X = synthetic_eval_data["X"].copy()
    X["label"] = synthetic_eval_data["y_binary"]  # Inject leakage

    rf_model = RandomForestClassifierModel(n_estimators=5, random_state=42)
    with pytest.raises(ValueError, match="DATA LEAKAGE DETECTED"):
        UnifiedModelEvaluator.evaluate_model(
            model=rf_model,
            X_test=X,
            y_test_binary=synthetic_eval_data["y_binary"],
        )


def test_model_comparator_multi_model(synthetic_eval_data):
    X = synthetic_eval_data["X"]
    y_bin = synthetic_eval_data["y_binary"]
    y_cat = synthetic_eval_data["y_category"]
    unseen = synthetic_eval_data["unseen_categories"]

    # Train lightweight models
    if_model = IsolationForestDetector(n_estimators=10, random_state=42)
    if_model.train(X[y_bin == 0])

    rf_model = RandomForestClassifierModel(n_estimators=10, random_state=42)
    rf_model.train(X, y_bin)

    with tempfile.TemporaryDirectory() as temp_dir:
        # Evaluate pre-instantiated models
        res_if = UnifiedModelEvaluator.evaluate_model(
            model=if_model, X_test=X, y_test_binary=y_bin, y_test_category=y_cat, unseen_categories=unseen
        )
        res_rf = UnifiedModelEvaluator.evaluate_model(
            model=rf_model, X_test=X, y_test_binary=y_bin, y_test_category=y_cat, unseen_categories=unseen
        )

        eval_map = {
            "isolation_forest": res_if,
            "random_forest": res_rf,
        }

        std_df = ModelComparator._build_standard_comparison_table(eval_map, "synthetic")
        unseen_df = ModelComparator._build_unseen_comparison_table(eval_map, "synthetic")
        overall_df = ModelComparator._build_overall_comparison_table(std_df, unseen_df)

        assert len(std_df) == 2
        assert len(unseen_df) == 2
        assert "Model" in std_df.columns
        assert "F1-Score" in std_df.columns

        rankings = ModelComparator._compute_rankings(eval_map, ModelComparator.DEFAULT_COMPOSITE_WEIGHTS)
        assert "ranking_standard_f1" in rankings
        assert "ranking_zero_day_resilience" in rankings
        assert "composite_ranking" in rankings
        assert len(rankings["composite_ranking"]) == 2

        # Test visualization generation
        plots = ComparisonVisualizer.generate_all_comparison_plots(
            evaluation_results=eval_map,
            dataset_name="synthetic",
            output_dir=Path(temp_dir) / "plots",
        )
        assert len(plots) >= 4
        for p in plots:
            assert Path(p).exists()
