from pathlib import Path
from typing import Tuple
import numpy as np
import pandas as pd
import pytest

from backend.app.ml.models.random_forest import RandomForestClassifierModel
from backend.app.ml.training.random_forest_trainer import RandomForestTrainer
from backend.app.ml.inference.random_forest_predictor import (
    RandomForestPredictor,
    RandomForestPrediction,
)
from backend.app.ml.evaluation.random_forest_evaluator import RandomForestEvaluator
from backend.app.ml.registry.model_registry import ModelRegistry
from backend.app.ml.data.preprocessing.pipeline import NetworkDataPipeline
from backend.app.services.random_forest_service import RandomForestService


@pytest.fixture
def synthetic_labeled_data() -> Tuple[pd.DataFrame, pd.Series, pd.Series]:
    """Generate synthetic labeled feature matrix with normal and attack records."""
    np.random.seed(42)
    n_normal = 40
    n_known_attack = 20
    n_unseen_attack = 10
    n_features = 6

    # Normal samples centered around 0.0
    X_normal = np.random.normal(loc=0.0, scale=0.8, size=(n_normal, n_features))
    # Known attack samples shifted to +3.5
    X_known = np.random.normal(loc=3.5, scale=0.9, size=(n_known_attack, n_features))
    # Unseen attack samples shifted to -4.0
    X_unseen = np.random.normal(loc=-4.0, scale=1.0, size=(n_unseen_attack, n_features))

    X_all = np.vstack([X_normal, X_known, X_unseen]).astype(np.float32)
    feature_names = [f"feat_{i}" for i in range(n_features)]
    X_df = pd.DataFrame(X_all, columns=feature_names)

    # Binary labels (0 = normal, 1 = attack)
    y_binary = pd.Series([0] * n_normal + [1] * (n_known_attack + n_unseen_attack))
    # Category labels
    y_category = pd.Series(
        ["normal"] * n_normal
        + ["dos"] * n_known_attack
        + ["zero_day_unseen"] * n_unseen_attack
    )

    return X_df, y_binary, y_category


# ---------------------------------------------------------------------------
# 1. Model Initialization & Hyperparameters
# ---------------------------------------------------------------------------
def test_random_forest_initialization():
    """Verify default configurations and uninitialized state."""
    model = RandomForestClassifierModel(
        n_estimators=120,
        max_depth=10,
        min_samples_split=4,
        class_weight="balanced",
        decision_threshold=0.45,
    )
    assert model.n_estimators == 120
    assert model.max_depth == 10
    assert model.min_samples_split == 4
    assert model.class_weight == "balanced"
    assert model.decision_threshold == 0.45
    assert not model.is_trained
    assert model.model is None


# ---------------------------------------------------------------------------
# 2. Supervised Training on Labeled Features
# ---------------------------------------------------------------------------
def test_random_forest_supervised_training(synthetic_labeled_data):
    """Verify supervised training on normal + attack labeled examples."""
    X_df, y_binary, _ = synthetic_labeled_data

    model = RandomForestClassifierModel(n_estimators=30, random_state=42)
    model.train(X_df, y_binary)

    assert model.is_trained
    assert model.model is not None
    assert model.feature_count_ == X_df.shape[1]
    assert len(model.classes_) == 2
    assert len(model.feature_importances_dict_) == X_df.shape[1]


# ---------------------------------------------------------------------------
# 3. Probability Estimation & Score Normalization
# ---------------------------------------------------------------------------
def test_random_forest_probabilities_and_scores(synthetic_labeled_data):
    """Verify predict_proba and 0-100 anomaly scores."""
    X_df, y_binary, _ = synthetic_labeled_data
    model = RandomForestClassifierModel(n_estimators=30, random_state=42)
    model.train(X_df, y_binary)

    # Probabilities
    probs = model.predict_proba(X_df)
    assert probs.shape == (len(X_df), 2)
    np.testing.assert_allclose(probs.sum(axis=1), np.ones(len(X_df)), atol=1e-5)

    # Attack probability
    p_attack = model.predict_attack_probability(X_df)
    assert len(p_attack) == len(X_df)
    assert (p_attack >= 0.0).all() and (p_attack <= 1.0).all()

    # Anomaly Scores (0 - 100)
    scores = model.compute_anomaly_scores(X_df)
    assert (scores >= 0.0).all() and (scores <= 100.0).all()
    # Attacks should have significantly higher predicted attack probability than normal samples
    assert p_attack[y_binary == 1].mean() > p_attack[y_binary == 0].mean()


# ---------------------------------------------------------------------------
# 4. Feature Importance Extraction & Ranking
# ---------------------------------------------------------------------------
def test_random_forest_feature_importances(synthetic_labeled_data):
    """Verify Gini feature importance extraction, sorting, and ranking."""
    X_df, y_binary, _ = synthetic_labeled_data
    model = RandomForestClassifierModel(n_estimators=30, random_state=42)
    model.train(X_df, y_binary)

    ranked_features = model.get_feature_importances(top_n=3)
    assert len(ranked_features) == 3
    assert ranked_features[0]["rank"] == 1
    assert ranked_features[0]["importance"] >= ranked_features[1]["importance"]
    assert all("feature" in item and "importance" in item for item in ranked_features)


# ---------------------------------------------------------------------------
# 5. Threshold Handling & Validation Optimization
# ---------------------------------------------------------------------------
def test_random_forest_threshold_tuning(synthetic_labeled_data):
    """Verify decision threshold optimization on validation data."""
    X_df, y_binary, _ = synthetic_labeled_data
    model = RandomForestClassifierModel(n_estimators=30, random_state=42)
    model.train(X_df.iloc[:50], y_binary.iloc[:50])

    tuned_thresh = model.determine_threshold(X_df.iloc[50:], y_binary.iloc[50:], strategy="f1_optimal")
    assert 0.0 < tuned_thresh < 1.0
    assert model.optimal_threshold_ == tuned_thresh

    preds = model.predict_binary(X_df)
    assert len(preds) == len(X_df)
    assert set(np.unique(preds)).issubset({0, 1})


# ---------------------------------------------------------------------------
# 6. Model Artifact Serialization & Reloading (.joblib)
# ---------------------------------------------------------------------------
def test_random_forest_save_and_load(synthetic_labeled_data, tmp_path: Path):
    """Verify model persistence with joblib and exact probability reproduction."""
    X_df, y_binary, _ = synthetic_labeled_data
    model = RandomForestClassifierModel(n_estimators=30, random_state=42)
    model.train(X_df, y_binary)

    model_file = tmp_path / "test_rf.joblib"
    model.save(model_file)
    assert model_file.exists()

    reloaded = RandomForestClassifierModel.load(model_file)
    assert reloaded.is_trained
    assert reloaded.feature_count_ == model.feature_count_
    assert reloaded.decision_threshold == model.decision_threshold

    probs_orig = model.predict_proba(X_df)
    probs_reload = reloaded.predict_proba(X_df)
    np.testing.assert_allclose(probs_orig, probs_reload, atol=1e-5)


# ---------------------------------------------------------------------------
# 7. Trainer Lifecycle Workflow
# ---------------------------------------------------------------------------
def test_random_forest_trainer_workflow(synthetic_labeled_data, tmp_path: Path):
    """Verify RandomForestTrainer handles supervised training, threshold tuning, and registry."""
    X_df, y_binary, _ = synthetic_labeled_data
    X_train = X_df.iloc[:50]
    y_train = y_binary.iloc[:50]
    X_val = X_df.iloc[50:]
    y_val = y_binary.iloc[50:]

    trainer = RandomForestTrainer(
        dataset_name="synthetic_test",
        version="1.0.0",
        n_estimators=25,
        tune_threshold=True,
        random_state=42,
    )

    trainer.train(
        X_train_proc=X_train,
        y_train_binary=y_train,
        X_val_proc=X_val,
        y_val_binary=y_val,
    )

    assert trainer.model.is_trained
    model_path, meta_path = trainer.save_artifacts(output_dir=tmp_path / "models")
    assert model_path.exists()
    assert meta_path.exists()


# ---------------------------------------------------------------------------
# 8. Predictor Single & Batch Inference
# ---------------------------------------------------------------------------
def test_random_forest_predictor_inference(synthetic_labeled_data, tmp_path: Path):
    """Verify RandomForestPredictor executes single and batch flow classification."""
    X_df, y_binary, _ = synthetic_labeled_data

    # 1. Fit & save preprocessing pipeline
    pipeline = NetworkDataPipeline(dataset_name="rf_pred_test", scaling_strategy="standard", selection_strategy="none")
    pipeline.fit(X_df)
    pipe_dir = pipeline.save(tmp_path / "preprocessing" / "rf_pred_test")

    # 2. Train & save classifier
    model = RandomForestClassifierModel(n_estimators=25, random_state=42)
    model.train(pipeline.transform(X_df), y_binary)
    model_file = tmp_path / "models" / "random_forest_rf_pred_test_v1.0.0.joblib"
    model.save(model_file)

    # 3. Predictor
    predictor = RandomForestPredictor(
        dataset_name="rf_pred_test",
        model_path=model_file,
        preprocessing_dir=pipe_dir,
    )
    predictor.load()

    # Single-record inference
    single_record = X_df.iloc[0].to_dict()
    pred_single = predictor.predict_single(single_record)
    assert isinstance(pred_single, RandomForestPrediction)
    assert pred_single.model_name == "random_forest"
    assert pred_single.prediction in ("normal", "attack")
    assert 0.0 <= pred_single.anomaly_score <= 100.0
    assert 0.5 <= pred_single.confidence_score <= 1.0
    assert pred_single.processing_time_ms >= 0.0

    # Batch inference
    batch_preds = predictor.predict_batch(X_df.head(10))
    assert len(batch_preds) == 10
    assert all(isinstance(p, RandomForestPrediction) for p in batch_preds)


# ---------------------------------------------------------------------------
# 9. Invalid Inputs & Exception Handling
# ---------------------------------------------------------------------------
def test_invalid_input_and_error_handling(synthetic_labeled_data):
    """Verify appropriate error handling for unfitted models, NaNs, and missing files."""
    model = RandomForestClassifierModel()

    # Unfitted error
    with pytest.raises(RuntimeError):
        model.predict_proba(np.array([[1.0, 2.0]]))

    # Train and test dirty inputs
    X_df, y_bin, _ = synthetic_labeled_data
    model.train(X_df, y_bin)

    dirty_nan = np.array([[1.0, np.nan, 3.0, 4.0, 5.0, 6.0]])
    with pytest.raises(ValueError):
        model.predict_proba(dirty_nan)

    missing_pred = RandomForestPredictor(dataset_name="nonexistent", model_path="missing.joblib")
    with pytest.raises(FileNotFoundError):
        missing_pred.load()


# ---------------------------------------------------------------------------
# 10. Model Registry Enrollment & Retrieval
# ---------------------------------------------------------------------------
def test_random_forest_model_registry_operations(tmp_path: Path):
    """Verify registry stores and discovers random_forest model metadata."""
    reg_file = tmp_path / "test_registry.json"
    registry = ModelRegistry(registry_file=reg_file)

    registry.register_model(
        model_name="random_forest",
        dataset="cicids2017",
        version="1.0.0",
        artifact_path="/path/to/rf_cicids2017_v1.0.0.joblib",
        feature_count=35,
        set_active=True,
    )

    meta = registry.get_model("random_forest", dataset="cicids2017")
    assert meta is not None
    assert meta["model_name"] == "random_forest"
    assert meta["dataset"] == "cicids2017"
    assert meta["version"] == "1.0.0"
    assert meta["is_active"] is True

    models = registry.list_models(model_name="random_forest")
    assert len(models) == 1


# ---------------------------------------------------------------------------
# 11. Supervised & Unseen Zero-Day Evaluation Metrics
# ---------------------------------------------------------------------------
def test_random_forest_evaluator_metrics(synthetic_labeled_data, tmp_path: Path):
    """Verify calculation of supervised metrics, PR-AUC, and unseen zero-day response."""
    X_df, y_binary, y_category = synthetic_labeled_data
    model = RandomForestClassifierModel(n_estimators=30, random_state=42)
    # Train only on normal + known attacks (exclude unseen attacks from training)
    train_mask = (y_category != "zero_day_unseen")
    model.train(X_df[train_mask], y_binary[train_mask])

    report = RandomForestEvaluator.evaluate(
        model=model,
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
    assert "balanced_accuracy" in report["metrics"]
    assert "precision" in report["metrics"]
    assert "recall_detection_rate" in report["metrics"]
    assert "f1_score" in report["metrics"]
    assert "roc_auc" in report["metrics"]
    assert "pr_auc" in report["metrics"]
    assert "top_feature_importances" in report
    assert "zero_day_evaluation" in report

    zd = report["zero_day_evaluation"]
    assert "zero_day_unseen" in zd["category_breakdown"]
    assert zd["category_breakdown"]["zero_day_unseen"]["is_unseen_zero_day"] is True


# ---------------------------------------------------------------------------
# 12. Service Layer Integration
# ---------------------------------------------------------------------------
def test_random_forest_service_interface(synthetic_labeled_data, tmp_path: Path):
    """Verify RandomForestService provides decoupled sync and async flow prediction."""
    X_df, y_bin, _ = synthetic_labeled_data

    pipeline = NetworkDataPipeline(dataset_name="srv_rf_test", scaling_strategy="standard", selection_strategy="none")
    pipeline.fit(X_df)
    pipe_dir = pipeline.save(tmp_path / "preprocessing" / "srv_rf_test")

    model = RandomForestClassifierModel(n_estimators=20, random_state=42)
    model.train(pipeline.transform(X_df), y_bin)
    model_file = tmp_path / "models" / "random_forest_srv_rf_test_v1.0.0.joblib"
    model.save(model_file)

    service = RandomForestService(default_dataset="srv_rf_test")
    predictor = RandomForestPredictor(
        dataset_name="srv_rf_test",
        model_path=model_file,
        preprocessing_dir=pipe_dir,
    )
    service.predictors["srv_rf_test"] = predictor

    pred = service.predict_flow(X_df.iloc[0].to_dict(), dataset="srv_rf_test")
    assert isinstance(pred, RandomForestPrediction)
    assert pred.dataset == "srv_rf_test"
    assert pred.model_name == "random_forest"
