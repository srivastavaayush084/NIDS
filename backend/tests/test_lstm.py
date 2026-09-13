from pathlib import Path
from typing import Tuple
import numpy as np
import pandas as pd
import pytest
import torch

from backend.app.ml.sequence.sequence_builder import SequenceBuilder, SequenceWindow
from backend.app.ml.sequence.sequence_validator import validate_sequence_data
from backend.app.ml.models.lstm_autoencoder import LSTMAutoencoderDetector, LSTMAutoencoderNetwork
from backend.app.ml.training.lstm_trainer import LSTMTrainer
from backend.app.ml.inference.lstm_predictor import LSTMPredictor, LSTMPrediction
from backend.app.ml.evaluation.lstm_evaluator import LSTMEvaluator
from backend.app.ml.registry.model_registry import ModelRegistry
from backend.app.ml.data.preprocessing.pipeline import NetworkDataPipeline
from backend.app.services.lstm_service import LSTMService


@pytest.fixture
def synthetic_tabular_data() -> Tuple[pd.DataFrame, pd.Series, pd.Series]:
    """Generate sequential synthetic network features with ordered benign and attack events."""
    np.random.seed(42)
    n_normal = 50
    n_known_attack = 20
    n_unseen_attack = 15
    n_features = 6

    # Normal events centered around 0.0 with small variance
    X_normal = np.random.normal(loc=0.0, scale=0.4, size=(n_normal, n_features))
    # Known attack events shifted to +3.0
    X_known = np.random.normal(loc=3.0, scale=0.6, size=(n_known_attack, n_features))
    # Unseen zero-day attack events shifted to -4.0
    X_unseen = np.random.normal(loc=-4.0, scale=0.8, size=(n_unseen_attack, n_features))

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
# 1. Sequence Builder & Windowing Logic
# ---------------------------------------------------------------------------
def test_sequence_builder_windowing(synthetic_tabular_data):
    """Verify SequenceBuilder constructs proper 3D tensor shapes, strides, and metadata."""
    X_df, y_binary, y_category = synthetic_tabular_data
    seq_len = 8
    stride = 2

    builder = SequenceBuilder(sequence_length=seq_len, stride=stride, label_aggregation="any")
    X_seq, y_seq_bin, y_seq_cat, windows = builder.build_sequences(
        X=X_df,
        y_binary=y_binary,
        y_category=y_category,
    )

    expected_count = (len(X_df) - seq_len) // stride + 1
    assert X_seq.shape == (expected_count, seq_len, X_df.shape[1])
    assert len(y_seq_bin) == expected_count
    assert len(y_seq_cat) == expected_count
    assert len(windows) == expected_count
    assert isinstance(windows[0], SequenceWindow)
    assert windows[0].start_row_idx == 0
    assert windows[0].end_row_idx == seq_len


def test_sequence_builder_label_aggregations():
    """Verify label aggregation rules ('any', 'last', 'majority')."""
    X_mock = np.zeros((10, 4), dtype=np.float32)
    # 3 normal, 2 attack, 5 normal
    y_mock = pd.Series([0, 0, 0, 1, 1, 0, 0, 0, 0, 0])

    # 1. 'any' aggregation
    builder_any = SequenceBuilder(sequence_length=5, stride=1, label_aggregation="any")
    _, y_any, _, _ = builder_any.build_sequences(X_mock, y_mock)
    # First window has rows 0..4 (contains row 3, 4 which are 1) -> 1
    assert y_any[0] == 1

    # 2. 'last' aggregation
    builder_last = SequenceBuilder(sequence_length=5, stride=1, label_aggregation="last")
    _, y_last, _, _ = builder_last.build_sequences(X_mock, y_mock)
    # First window rows 0..4 ends at row 4 (value is 1) -> 1
    assert y_last[0] == 1
    # Second window rows 1..5 ends at row 5 (value is 0) -> 0
    assert y_last[1] == 0

    # 3. 'majority' aggregation
    builder_maj = SequenceBuilder(sequence_length=5, stride=1, label_aggregation="majority")
    _, y_maj, _, _ = builder_maj.build_sequences(X_mock, y_mock)
    # First window has 2/5 = 40% attacks -> 0 (<50%)
    assert y_maj[0] == 0


# ---------------------------------------------------------------------------
# 2. Sequence Validation & Dimensional Integrity
# ---------------------------------------------------------------------------
def test_sequence_validator_checks():
    """Verify validate_sequence_data enforces tensor shape and finite values."""
    # Valid 3D tensor
    valid_tensor = np.random.randn(5, 10, 4).astype(np.float32)
    out = validate_sequence_data(valid_tensor, expected_seq_len=10, expected_feat_dim=4)
    assert out.shape == (5, 10, 4)

    # 2D sequence allowed if single_sequence=True
    valid_2d = np.random.randn(10, 4).astype(np.float32)
    out_2d = validate_sequence_data(valid_2d, expected_seq_len=10, expected_feat_dim=4, allow_single_sequence=True)
    assert out_2d.shape == (1, 10, 4)

    # Length mismatch
    with pytest.raises(ValueError):
        validate_sequence_data(valid_tensor, expected_seq_len=12, expected_feat_dim=4)

    # Feature dim mismatch
    with pytest.raises(ValueError):
        validate_sequence_data(valid_tensor, expected_seq_len=10, expected_feat_dim=6)

    # NaN input error
    nan_tensor = valid_tensor.copy()
    nan_tensor[0, 0, 0] = np.nan
    with pytest.raises(ValueError):
        validate_sequence_data(nan_tensor, expected_seq_len=10, expected_feat_dim=4)


# ---------------------------------------------------------------------------
# 3. LSTM Network Forward Pass & Tensor Shapes
# ---------------------------------------------------------------------------
def test_lstm_autoencoder_network_forward():
    """Verify PyTorch LSTMAutoencoderNetwork maintains sequential dimensions."""
    batch_size = 8
    seq_len = 10
    input_dim = 6
    encoder_units = 32
    latent_dim = 8
    decoder_units = 32

    net = LSTMAutoencoderNetwork(
        input_dim=input_dim,
        seq_len=seq_len,
        encoder_units=encoder_units,
        latent_dim=latent_dim,
        decoder_units=decoder_units,
        num_layers=1,
        dropout_rate=0.1,
    )

    dummy_input = torch.randn(batch_size, seq_len, input_dim)

    # Test full reconstruction
    output = net(dummy_input)
    assert output.shape == (batch_size, seq_len, input_dim)

    # Test latent encoding bottleneck
    latent = net.encode(dummy_input)
    assert latent.shape == (batch_size, latent_dim)


# ---------------------------------------------------------------------------
# 4. Detector Training on Normal Sequences
# ---------------------------------------------------------------------------
def test_lstm_detector_training(synthetic_tabular_data):
    """Verify LSTMAutoencoderDetector trains on normal baseline sequences."""
    X_df, y_binary, _ = synthetic_tabular_data
    builder = SequenceBuilder(sequence_length=6, stride=1)
    
    # Generate normal training sequences
    X_normal_seq, _, _, _ = builder.build_sequences(X_df[y_binary == 0])

    detector = LSTMAutoencoderDetector(
        input_dim=X_df.shape[1],
        seq_len=6,
        encoder_units=24,
        latent_dim=8,
        decoder_units=24,
        epochs=15,
        batch_size=16,
        learning_rate=0.01,
        random_seed=42,
        device="cpu",
    )
    detector.train(X_normal_seq)

    assert detector.is_trained
    assert detector.network is not None
    assert len(detector.training_history_["train_loss"]) > 0
    assert detector.training_history_["train_loss"][-1] > 0.0
    assert detector.mse_min_ < detector.mse_max_


# ---------------------------------------------------------------------------
# 5. Sequence Reconstruction MSE & Anomaly Score Calibration (0 - 100)
# ---------------------------------------------------------------------------
def test_lstm_reconstruction_error_and_scores(synthetic_tabular_data):
    """Verify sequence reconstruction MSE and score calibration in [0, 100]."""
    X_df, y_binary, _ = synthetic_tabular_data
    builder = SequenceBuilder(sequence_length=6, stride=1, label_aggregation="any")
    
    X_normal_seq, _, _, _ = builder.build_sequences(X_df[y_binary == 0])
    X_all_seq, y_seq_bin, _, _ = builder.build_sequences(X_df, y_binary=y_binary)

    detector = LSTMAutoencoderDetector(
        input_dim=X_df.shape[1],
        seq_len=6,
        encoder_units=24,
        latent_dim=8,
        decoder_units=24,
        epochs=15,
        batch_size=16,
        learning_rate=0.01,
        random_seed=42,
        device="cpu",
    )
    detector.train(X_normal_seq)

    # 1. Raw Sequence MSE
    mse = detector.compute_reconstruction_error(X_all_seq)
    assert isinstance(mse, np.ndarray)
    assert len(mse) == len(X_all_seq)
    assert (mse >= 0.0).all()

    # Normal sequences should on average have lower MSE than attack sequences
    normal_mse = mse[y_seq_bin == 0].mean()
    attack_mse = mse[y_seq_bin == 1].mean()
    assert attack_mse > normal_mse

    # 2. Timestep errors breakdown
    ts_errors = detector.compute_timestep_errors(X_all_seq)
    assert ts_errors.shape == (len(X_all_seq), 6)

    # 3. Anomaly Scores (0 - 100)
    scores = detector.compute_anomaly_scores(X_all_seq)
    assert (scores >= 0.0).all()
    assert (scores <= 100.0).all()


# ---------------------------------------------------------------------------
# 6. Threshold Selection & Decision Behavior
# ---------------------------------------------------------------------------
def test_lstm_threshold_selection(synthetic_tabular_data):
    """Verify validation threshold selection and binary prediction."""
    X_df, y_binary, _ = synthetic_tabular_data
    builder = SequenceBuilder(sequence_length=6, stride=1)
    X_normal_seq, _, _, _ = builder.build_sequences(X_df[y_binary == 0])
    X_all_seq, _, _, _ = builder.build_sequences(X_df)

    detector = LSTMAutoencoderDetector(
        input_dim=X_df.shape[1],
        seq_len=6,
        encoder_units=16,
        latent_dim=6,
        epochs=10,
        random_seed=42,
        device="cpu",
    )
    detector.train(X_normal_seq)

    thresh = detector.determine_threshold(X_normal_seq, strategy="percentile", percentile=95.0)
    assert thresh > 0.0
    assert 0.0 <= detector.optimal_score_threshold_ <= 100.0

    preds = detector.predict_binary(X_all_seq)
    assert len(preds) == len(X_all_seq)
    assert set(np.unique(preds)).issubset({0, 1})


# ---------------------------------------------------------------------------
# 7. Model Checkpoint Save & Load (.pt)
# ---------------------------------------------------------------------------
def test_lstm_model_artifact_save_load(synthetic_tabular_data, tmp_path: Path):
    """Verify serialization to .pt and exact reconstruction score reload."""
    X_df, y_binary, _ = synthetic_tabular_data
    builder = SequenceBuilder(sequence_length=6, stride=1)
    X_normal_seq, _, _, _ = builder.build_sequences(X_df[y_binary == 0])
    X_all_seq, _, _, _ = builder.build_sequences(X_df)

    detector = LSTMAutoencoderDetector(
        input_dim=X_df.shape[1],
        seq_len=6,
        encoder_units=16,
        latent_dim=6,
        epochs=10,
        random_seed=42,
        device="cpu",
    )
    detector.train(X_normal_seq)

    model_file = tmp_path / "test_lstm.pt"
    detector.save(model_file)
    assert model_file.exists()

    reloaded = LSTMAutoencoderDetector.load(model_file, device="cpu")
    assert reloaded.is_trained
    assert reloaded.seq_len == detector.seq_len
    assert reloaded.latent_dim == detector.latent_dim
    assert reloaded.optimal_threshold_ == detector.optimal_threshold_

    scores_orig = detector.compute_anomaly_scores(X_all_seq)
    scores_reload = reloaded.compute_anomaly_scores(X_all_seq)
    np.testing.assert_allclose(scores_orig, scores_reload, atol=1e-5)


# ---------------------------------------------------------------------------
# 8. Trainer Lifecycle Workflow
# ---------------------------------------------------------------------------
def test_lstm_trainer_workflow(synthetic_tabular_data, tmp_path: Path):
    """Verify LSTMTrainer handles tabular splits, windowing, early stopping, and registry."""
    X_df, y_binary, _ = synthetic_tabular_data
    X_train = X_df.iloc[:50]
    y_train = y_binary.iloc[:50]
    X_val = X_df.iloc[50:]
    y_val = y_binary.iloc[50:]

    trainer = LSTMTrainer(
        dataset_name="synthetic_test",
        version="1.0.0",
        sequence_length=5,
        sequence_stride=1,
        encoder_units=16,
        latent_dim=6,
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
# 9. Predictor Single, Batch & Stream Inference
# ---------------------------------------------------------------------------
def test_lstm_predictor_inference(synthetic_tabular_data, tmp_path: Path):
    """Verify LSTMPredictor handles single sequence, batch sequences, and stream DataFrames."""
    X_df, y_binary, _ = synthetic_tabular_data
    seq_len = 5

    # 1. Fit & save preprocessing pipeline
    pipeline = NetworkDataPipeline(dataset_name="lstm_pred_test", scaling_strategy="standard", selection_strategy="none")
    pipeline.fit(X_df)
    pipe_dir = pipeline.save(tmp_path / "preprocessing" / "lstm_pred_test")

    # 2. Build sequences, train & save detector
    builder = SequenceBuilder(sequence_length=seq_len, stride=1)
    X_proc = pipeline.transform(X_df[y_binary == 0])
    X_seq_norm, _, _, _ = builder.build_sequences(X_proc)

    detector = LSTMAutoencoderDetector(input_dim=X_df.shape[1], seq_len=seq_len, latent_dim=6, epochs=10, random_seed=42, device="cpu")
    detector.train(X_seq_norm)
    model_file = tmp_path / "models" / "lstm_pred_test_v1.0.0.pt"
    detector.save(model_file)

    # 3. Predictor
    predictor = LSTMPredictor(
        dataset_name="lstm_pred_test",
        model_path=model_file,
        preprocessing_dir=pipe_dir,
        device="cpu",
    )
    predictor.load()

    # Single-sequence inference
    single_seq = X_seq_norm[0]
    pred_single = predictor.predict_single(single_seq)
    assert isinstance(pred_single, LSTMPrediction)
    assert pred_single.model_name == "lstm_autoencoder"
    assert pred_single.prediction in ("normal", "anomaly")
    assert 0.0 <= pred_single.anomaly_score <= 100.0
    assert pred_single.raw_mse >= 0.0
    assert pred_single.processing_time_ms >= 0.0
    assert "timestep_errors" in pred_single.metadata

    # Batch sequences inference
    batch_preds = predictor.predict_batch(X_seq_norm[:5])
    assert len(batch_preds) == 5
    assert all(isinstance(p, LSTMPrediction) for p in batch_preds)

    # Stream tabular records inference
    stream_preds = predictor.predict_stream(X_df.head(20), stride=2)
    assert len(stream_preds) > 0
    assert all(isinstance(p, LSTMPrediction) for p in stream_preds)


# ---------------------------------------------------------------------------
# 10. Model Registry Integration
# ---------------------------------------------------------------------------
def test_lstm_model_registry_operations(tmp_path: Path):
    """Verify registry stores and discovers lstm_autoencoder model metadata."""
    reg_file = tmp_path / "test_registry.json"
    registry = ModelRegistry(registry_file=reg_file)

    registry.register_model(
        model_name="lstm_autoencoder",
        dataset="nsl_kdd",
        version="1.0.0",
        artifact_path="/path/to/lstm_nsl_kdd_v1.0.0.pt",
        feature_count=41,
        set_active=True,
    )

    meta = registry.get_model("lstm_autoencoder", dataset="nsl_kdd")
    assert meta is not None
    assert meta["model_name"] == "lstm_autoencoder"
    assert meta["dataset"] == "nsl_kdd"
    assert meta["version"] == "1.0.0"
    assert meta["is_active"] is True

    models = registry.list_models(model_name="lstm_autoencoder")
    assert len(models) == 1


# ---------------------------------------------------------------------------
# 11. Unseen Zero-Day Evaluation Metrics
# ---------------------------------------------------------------------------
def test_lstm_evaluator_unseen_zero_day_metrics(synthetic_tabular_data, tmp_path: Path):
    """Verify calculation of sequence-level security metrics and unseen zero-day breakdown."""
    X_df, y_binary, y_category = synthetic_tabular_data
    builder = SequenceBuilder(sequence_length=5, stride=1, label_aggregation="any")
    
    X_normal_seq, _, _, _ = builder.build_sequences(X_df[y_binary == 0])
    X_all_seq, y_seq_bin, y_seq_cat, _ = builder.build_sequences(
        X_df, y_binary=y_binary, y_category=y_category
    )

    detector = LSTMAutoencoderDetector(input_dim=X_df.shape[1], seq_len=5, latent_dim=6, epochs=10, random_seed=42, device="cpu")
    detector.train(X_normal_seq)

    report = LSTMEvaluator.evaluate(
        detector=detector,
        X_test_seq=X_all_seq,
        y_test_binary=y_seq_bin,
        y_test_category=y_seq_cat,
        unseen_categories=["zero_day_unseen"],
        dataset_name="synthetic_test",
        output_dir=tmp_path / "exp",
        generate_plots=False,
    )

    assert "metrics" in report
    assert "accuracy" in report["metrics"]
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
def test_lstm_service_interface(synthetic_tabular_data, tmp_path: Path):
    """Verify LSTMService provides decoupled sync and async sequence prediction."""
    X_df, y_bin, _ = synthetic_tabular_data
    seq_len = 5

    pipeline = NetworkDataPipeline(dataset_name="srv_lstm_test", scaling_strategy="standard", selection_strategy="none")
    pipeline.fit(X_df)
    pipe_dir = pipeline.save(tmp_path / "preprocessing" / "srv_lstm_test")

    builder = SequenceBuilder(sequence_length=seq_len, stride=1)
    X_seq_norm, _, _, _ = builder.build_sequences(pipeline.transform(X_df[y_bin == 0]))

    detector = LSTMAutoencoderDetector(input_dim=X_df.shape[1], seq_len=seq_len, latent_dim=6, epochs=10, random_seed=42, device="cpu")
    detector.train(X_seq_norm)
    model_file = tmp_path / "models" / "lstm_srv_test_v1.0.0.pt"
    detector.save(model_file)

    service = LSTMService(default_dataset="srv_lstm_test")
    predictor = LSTMPredictor(
        dataset_name="srv_lstm_test",
        model_path=model_file,
        preprocessing_dir=pipe_dir,
        device="cpu",
    )
    service.predictors["srv_lstm_test"] = predictor

    pred = service.predict_sequence(X_seq_norm[0], dataset="srv_lstm_test")
    assert isinstance(pred, LSTMPrediction)
    assert pred.dataset == "srv_lstm_test"
    assert pred.model_name == "lstm_autoencoder"
