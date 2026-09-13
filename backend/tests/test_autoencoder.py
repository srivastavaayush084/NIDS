from pathlib import Path
from typing import Tuple
import numpy as np
import pandas as pd
import pytest
import torch

from backend.app.ml.models.autoencoder import AutoencoderDetector, DenseAutoencoderNetwork
from backend.app.ml.training.autoencoder_trainer import AutoencoderTrainer
from backend.app.ml.inference.autoencoder_predictor import (
    AutoencoderPredictor,
    AutoencoderPrediction,
)
from backend.app.ml.evaluation.autoencoder_evaluator import AutoencoderEvaluator
from backend.app.ml.registry.model_registry import ModelRegistry
from backend.app.ml.data.preprocessing.pipeline import NetworkDataPipeline
from backend.app.services.autoencoder_service import AutoencoderService


@pytest.fixture
def synthetic_data() -> Tuple[pd.DataFrame, pd.Series, pd.Series]:
    """Generate synthetic network feature matrix and labels."""
    np.random.seed(42)
    n_samples = 60
    n_features = 8

    # Normal samples centered around 0.0
    X_normal = np.random.normal(loc=0.0, scale=0.5, size=(40, n_features))
    # Known attack samples shifted to +3.5
    X_known_attack = np.random.normal(loc=3.5, scale=0.8, size=(12, n_features))
    # Unseen zero-day attack samples shifted to -4.5
    X_unseen_attack = np.random.normal(loc=-4.5, scale=1.0, size=(8, n_features))

    X_all = np.vstack([X_normal, X_known_attack, X_unseen_attack]).astype(np.float32)
    feature_names = [f"feat_{i}" for i in range(n_features)]
    X_df = pd.DataFrame(X_all, columns=feature_names)

    # Binary labels (0 = normal, 1 = attack)
    y_binary = pd.Series([0] * 40 + [1] * 20)
    # Category labels
    y_category = pd.Series(["normal"] * 40 + ["dos"] * 12 + ["zero_day_unseen"] * 8)

    return X_df, y_binary, y_category


# ---------------------------------------------------------------------------
# 1. Network Architecture & Tensor Shapes
# ---------------------------------------------------------------------------
def test_dense_autoencoder_network_forward():
    """Verify PyTorch DenseAutoencoderNetwork maintains proper input and bottleneck dimensions."""
    input_dim = 10
    latent_dim = 4
    encoder_layers = [8, 6]
    decoder_layers = [6, 8]

    net = DenseAutoencoderNetwork(
        input_dim=input_dim,
        latent_dim=latent_dim,
        encoder_layers=encoder_layers,
        decoder_layers=decoder_layers,
        activation="relu",
        dropout=0.1,
    )

    batch_size = 16
    dummy_input = torch.randn(batch_size, input_dim)

    # Test full reconstruction
    output = net(dummy_input)
    assert output.shape == (batch_size, input_dim)

    # Test latent encoding
    latent = net.encode(dummy_input)
    assert latent.shape == (batch_size, latent_dim)


# ---------------------------------------------------------------------------
# 2. Detector Initialization & Configuration
# ---------------------------------------------------------------------------
def test_autoencoder_initialization():
    """Verify default configurations and uninitialized state."""
    detector = AutoencoderDetector(
        input_dim=12,
        latent_dim=4,
        learning_rate=0.005,
        batch_size=32,
        epochs=15,
        anomaly_threshold=70.0,
    )
    assert detector.input_dim == 12
    assert detector.latent_dim == 4
    assert detector.learning_rate == 0.005
    assert detector.batch_size == 32
    assert detector.epochs == 15
    assert detector.anomaly_threshold == 70.0
    assert not detector.is_trained
    assert detector.network is None


# ---------------------------------------------------------------------------
# 3. Training on Normal Traffic & Loss Minimization
# ---------------------------------------------------------------------------
def test_autoencoder_training_on_normal_traffic(synthetic_data):
    """Verify Autoencoder trains on normal traffic and reduces reconstruction loss."""
    X_df, y_binary, _ = synthetic_data
    X_normal = X_df[y_binary == 0]

    detector = AutoencoderDetector(
        latent_dim=4,
        epochs=15,
        batch_size=16,
        learning_rate=0.01,
        random_seed=42,
        device="cpu",
    )
    detector.train(X_normal)

    assert detector.is_trained
    assert detector.network is not None
    assert detector.feature_count_ == X_df.shape[1]
    assert len(detector.training_history_["train_loss"]) > 0
    # Final loss should be finite and positive
    assert detector.training_history_["train_loss"][-1] > 0.0
    assert detector.mse_min_ < detector.mse_max_


# ---------------------------------------------------------------------------
# 4. Reconstruction Error & Anomaly Score Calibration (0 - 100)
# ---------------------------------------------------------------------------
def test_reconstruction_error_and_score_calibration(synthetic_data):
    """Verify reconstruction MSE and calibrated score within [0, 100]."""
    X_df, y_binary, _ = synthetic_data
    X_normal = X_df[y_binary == 0]

    detector = AutoencoderDetector(
        latent_dim=4,
        epochs=20,
        batch_size=16,
        learning_rate=0.01,
        random_seed=42,
        device="cpu",
    )
    detector.train(X_normal)

    # 1. Raw Reconstruction MSE
    mse = detector.compute_reconstruction_error(X_df)
    assert isinstance(mse, np.ndarray)
    assert len(mse) == len(X_df)
    assert (mse >= 0.0).all()

    # Normal samples should reconstruct with lower error than attack samples
    normal_mse = mse[y_binary == 0].mean()
    attack_mse = mse[y_binary == 1].mean()
    assert attack_mse > normal_mse

    # 2. Normalized Anomaly Scores
    scores = detector.compute_anomaly_scores(X_df)
    assert isinstance(scores, np.ndarray)
    assert (scores >= 0.0).all()
    assert (scores <= 100.0).all()

    normal_scores = scores[y_binary == 0].mean()
    attack_scores = scores[y_binary == 1].mean()
    assert attack_scores > normal_scores


# ---------------------------------------------------------------------------
# 5. Threshold Selection & Decision Behavior
# ---------------------------------------------------------------------------
def test_threshold_selection_and_decision(synthetic_data):
    """Verify threshold determination strategies and binary classification."""
    X_df, y_binary, _ = synthetic_data
    X_normal = X_df[y_binary == 0]

    detector = AutoencoderDetector(latent_dim=4, epochs=10, random_seed=42, device="cpu")
    detector.train(X_normal)

    # Percentile strategy
    detector.determine_threshold(X_normal, strategy="percentile", percentile=95.0)
    assert detector.optimal_threshold_ > 0.0
    assert 0.0 <= detector.optimal_score_threshold_ <= 100.0

    # Predictions
    preds = detector.predict_binary(X_df)
    assert len(preds) == len(X_df)
    assert set(np.unique(preds)).issubset({0, 1})


# ---------------------------------------------------------------------------
# 6. Model Artifact Serialization & Reloading
# ---------------------------------------------------------------------------
def test_model_artifact_save_and_load(synthetic_data, tmp_path: Path):
    """Verify PyTorch model weights and detector state save/load accurately."""
    X_df, y_binary, _ = synthetic_data
    X_normal = X_df[y_binary == 0]

    detector = AutoencoderDetector(latent_dim=4, epochs=10, random_seed=42, device="cpu")
    detector.train(X_normal)

    model_file = tmp_path / "test_autoencoder.pt"
    detector.save(model_file)
    assert model_file.exists()

    reloaded = AutoencoderDetector.load(model_file, device="cpu")
    assert reloaded.is_trained
    assert reloaded.feature_count_ == detector.feature_count_
    assert reloaded.latent_dim == detector.latent_dim
    assert reloaded.optimal_threshold_ == detector.optimal_threshold_

    # Verify score consistency
    scores_orig = detector.compute_anomaly_scores(X_df)
    scores_reload = reloaded.compute_anomaly_scores(X_df)
    np.testing.assert_allclose(scores_orig, scores_reload, atol=1e-5)


# ---------------------------------------------------------------------------
# 7. Trainer & Early Stopping Validation
# ---------------------------------------------------------------------------
def test_autoencoder_trainer_workflow(synthetic_data, tmp_path: Path):
    """Verify AutoencoderTrainer handles splits, validation monitoring, and artifacts."""
    X_df, y_binary, _ = synthetic_data
    X_train = X_df.iloc[:40]
    y_train = y_binary.iloc[:40]
    X_val = X_df.iloc[40:]
    y_val = y_binary.iloc[40:]

    trainer = AutoencoderTrainer(
        dataset_name="synthetic_test",
        version="1.0.0",
        latent_dim=4,
        epochs=10,
        batch_size=16,
        early_stopping_patience=3,
        random_seed=42,
        device="cpu",
    )

    trainer.train(
        X_train_proc=X_train,
        y_train_binary=y_train,
        X_val_proc=X_val,
        y_val_binary=y_val,
    )

    assert trainer.detector.is_trained
    model_path, meta_path = trainer.save_artifacts(output_dir=tmp_path / "models")
    assert model_path.exists()
    assert meta_path.exists()


# ---------------------------------------------------------------------------
# 8. Single-Record & Batch Predictor
# ---------------------------------------------------------------------------
def test_autoencoder_predictor_inference(synthetic_data, tmp_path: Path):
    """Verify AutoencoderPredictor handles raw flow dicts and batch DataFrames."""
    X_df, y_binary, _ = synthetic_data

    # 1. Fit & save preprocessing pipeline
    pipeline = NetworkDataPipeline(dataset_name="pred_test", scaling_strategy="standard", selection_strategy="none")
    pipeline.fit(X_df)
    pipe_dir = pipeline.save(tmp_path / "preprocessing" / "pred_test")

    # 2. Train & save detector
    detector = AutoencoderDetector(latent_dim=4, epochs=10, random_seed=42, device="cpu")
    detector.train(pipeline.transform(X_df[y_binary == 0]))
    model_file = tmp_path / "models" / "autoencoder_pred_test_v1.0.0.pt"
    detector.save(model_file)

    # 3. Predictor
    predictor = AutoencoderPredictor(
        dataset_name="pred_test",
        model_path=model_file,
        preprocessing_dir=pipe_dir,
        device="cpu",
    )
    predictor.load()

    # Single-record inference
    single_record = X_df.iloc[0].to_dict()
    pred_single = predictor.predict_single(single_record)
    assert isinstance(pred_single, AutoencoderPrediction)
    assert pred_single.model_name == "autoencoder"
    assert pred_single.prediction in ("normal", "anomaly")
    assert 0.0 <= pred_single.anomaly_score <= 100.0
    assert pred_single.raw_mse >= 0.0
    assert pred_single.processing_time_ms >= 0.0

    # Batch inference
    batch_preds = predictor.predict_batch(X_df.head(10))
    assert len(batch_preds) == 10
    assert all(isinstance(p, AutoencoderPrediction) for p in batch_preds)


# ---------------------------------------------------------------------------
# 9. Invalid Inputs & Exception Handling
# ---------------------------------------------------------------------------
def test_invalid_input_and_error_handling(synthetic_data):
    """Verify appropriate error throwing on invalid shapes, NaNs, and uninitialized models."""
    detector = AutoencoderDetector(device="cpu")

    # Unfitted error
    with pytest.raises(RuntimeError):
        detector.compute_reconstruction_error(np.array([[1.0, 2.0]]))

    # Train and test dirty inputs
    X_df, y_bin, _ = synthetic_data
    detector.train(X_df[y_bin == 0])

    dirty_nan = np.array([[1.0, np.nan, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0]])
    with pytest.raises(ValueError):
        detector.compute_anomaly_scores(dirty_nan)

    missing_pred = AutoencoderPredictor(dataset_name="nonexistent", model_path="missing.pt")
    with pytest.raises(FileNotFoundError):
        missing_pred.load()


# ---------------------------------------------------------------------------
# 10. Model Registry Enrollment & Retrieval
# ---------------------------------------------------------------------------
def test_autoencoder_model_registry_operations(tmp_path: Path):
    """Verify registry stores and discovers autoencoder metadata."""
    reg_file = tmp_path / "test_registry.json"
    registry = ModelRegistry(registry_file=reg_file)

    registry.register_model(
        model_name="autoencoder",
        dataset="cicids2017",
        version="1.0.0",
        artifact_path="/path/to/autoencoder_cicids2017_v1.0.0.pt",
        feature_count=35,
        set_active=True,
    )

    meta = registry.get_model("autoencoder", dataset="cicids2017")
    assert meta is not None
    assert meta["model_name"] == "autoencoder"
    assert meta["dataset"] == "cicids2017"
    assert meta["version"] == "1.0.0"
    assert meta["is_active"] is True

    models = registry.list_models(model_name="autoencoder")
    assert len(models) == 1


# ---------------------------------------------------------------------------
# 11. Unseen Zero-Day Evaluation Metrics
# ---------------------------------------------------------------------------
def test_evaluator_unseen_zero_day_metrics(synthetic_data, tmp_path: Path):
    """Verify calculation of zero-day detection rate, reconstruction stats, and metrics."""
    X_df, y_binary, y_category = synthetic_data
    detector = AutoencoderDetector(latent_dim=4, epochs=15, random_seed=42, device="cpu")
    detector.train(X_df[y_binary == 0])

    report = AutoencoderEvaluator.evaluate(
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
    assert "reconstruction_error_distribution" in report
    assert "zero_day_evaluation" in report

    zd = report["zero_day_evaluation"]
    assert "zero_day_unseen" in zd["category_breakdown"]
    assert zd["category_breakdown"]["zero_day_unseen"]["is_unseen_zero_day"] is True


# ---------------------------------------------------------------------------
# 12. Service Layer Integration
# ---------------------------------------------------------------------------
def test_autoencoder_service_interface(synthetic_data, tmp_path: Path):
    """Verify AutoencoderService integration."""
    X_df, y_bin, _ = synthetic_data

    pipeline = NetworkDataPipeline(dataset_name="srv_test", scaling_strategy="standard", selection_strategy="none")
    pipeline.fit(X_df)
    pipe_dir = pipeline.save(tmp_path / "preprocessing" / "srv_test")

    detector = AutoencoderDetector(latent_dim=4, epochs=10, random_seed=42, device="cpu")
    detector.train(pipeline.transform(X_df[y_bin == 0]))
    model_file = tmp_path / "models" / "autoencoder_srv_test_v1.0.0.pt"
    detector.save(model_file)

    service = AutoencoderService(default_dataset="srv_test")
    predictor = AutoencoderPredictor(
        dataset_name="srv_test",
        model_path=model_file,
        preprocessing_dir=pipe_dir,
        device="cpu",
    )
    service.predictors["srv_test"] = predictor

    pred = service.predict_flow(X_df.iloc[0].to_dict(), dataset="srv_test")
    assert isinstance(pred, AutoencoderPrediction)
    assert pred.dataset == "srv_test"
    assert pred.model_name == "autoencoder"
