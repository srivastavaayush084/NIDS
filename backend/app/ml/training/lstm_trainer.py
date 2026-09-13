import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.ml.models.lstm_autoencoder import LSTMAutoencoderDetector
from backend.app.ml.sequence.sequence_builder import SequenceBuilder
from backend.app.ml.registry.model_registry import model_registry
from backend.app.ml.data.utils.data_utils import ensure_dir, save_metadata


class LSTMTrainer:
    """
    Orchestrates the training lifecycle of the Sequential LSTM Autoencoder Anomaly Detector.
    Constructs sliding sequence windows from preprocessed tabular splits (preserving temporal boundaries)
    and executes a Normal-Only Baseline Training Strategy to model benign sequence transitions.
    """

    def __init__(
        self,
        dataset_name: str = "synthetic",
        version: str = "1.0.0",
        sequence_length: Optional[int] = None,
        sequence_stride: Optional[int] = None,
        encoder_units: Optional[int] = None,
        latent_dim: Optional[int] = None,
        decoder_units: Optional[int] = None,
        num_layers: Optional[int] = None,
        dropout_rate: float = 0.1,
        dropout: Optional[float] = None,
        learning_rate: Optional[float] = None,
        batch_size: Optional[int] = None,
        epochs: Optional[int] = None,
        early_stopping_patience: Optional[int] = None,
        random_seed: Optional[int] = None,
        threshold_percentile: Optional[float] = None,
        threshold_strategy: Optional[str] = None,
        device: Optional[str] = None,
        normal_only_training: bool = True,
    ):
        self.dataset_name = dataset_name.lower().strip()
        self.version = version
        self.sequence_length = sequence_length or settings.LSTM_SEQUENCE_LENGTH
        self.sequence_stride = sequence_stride or settings.LSTM_SEQUENCE_STRIDE
        self.encoder_units = encoder_units or settings.LSTM_ENCODER_UNITS
        self.latent_dim = latent_dim or settings.LSTM_LATENT_DIM
        self.decoder_units = decoder_units or settings.LSTM_DECODER_UNITS
        self.num_layers = num_layers or settings.LSTM_NUM_LAYERS
        self.dropout_rate = dropout if dropout is not None else dropout_rate
        self.learning_rate = learning_rate or settings.LSTM_LEARNING_RATE
        self.batch_size = batch_size or settings.LSTM_BATCH_SIZE
        self.epochs = epochs or settings.LSTM_EPOCHS
        self.early_stopping_patience = early_stopping_patience or settings.LSTM_EARLY_STOPPING_PATIENCE
        self.random_seed = random_seed or settings.LSTM_RANDOM_SEED
        self.threshold_percentile = threshold_percentile or settings.LSTM_THRESHOLD_PERCENTILE
        self.threshold_strategy = threshold_strategy or "percentile"
        self.device = device
        self.normal_only_training = normal_only_training

        self.sequence_builder = SequenceBuilder(
            sequence_length=self.sequence_length,
            stride=self.sequence_stride,
            label_aggregation="any",
        )
        self.detector: Optional[LSTMAutoencoderDetector] = None
        self.training_duration_sec: float = 0.0
        self.training_metadata: Dict[str, Any] = {}

    def train(
        self,
        X_train_proc: pd.DataFrame,
        y_train_binary: pd.Series,
        X_val_proc: Optional[pd.DataFrame] = None,
        y_val_binary: Optional[pd.Series] = None,
        pipeline_dir: Optional[Union[str, Path]] = None,
    ) -> LSTMAutoencoderDetector:
        """
        Build sliding sequence windows and train LSTM Autoencoder on normal baseline sequences.
        """
        logger.info("=" * 60)
        logger.info(f"TRAINING LSTM AUTOENCODER: dataset='{self.dataset_name}', version='{self.version}'")
        logger.info(f"Sequence Configuration: length={self.sequence_length}, stride={self.sequence_stride}")
        logger.info("=" * 60)

        start_time = time.perf_counter()

        # 1. Construct Training Sequences
        if self.normal_only_training:
            normal_mask = (y_train_binary == 0).to_numpy()
            X_train_normal = X_train_proc.iloc[normal_mask].reset_index(drop=True)
            logger.info(
                f"Normal-Only Training: Using {len(X_train_normal)} normal rows from {len(X_train_proc)} total."
            )
            X_seq_train, _, _, _ = self.sequence_builder.build_sequences(
                X=X_train_normal,
                raise_if_insufficient=False,
            )
        else:
            X_seq_train, _, _, _ = self.sequence_builder.build_sequences(
                X=X_train_proc,
                y_binary=y_train_binary,
                raise_if_insufficient=False,
            )

        if len(X_seq_train) == 0:
            raise ValueError(
                f"Cannot train LSTM: 0 sequences generated (rows={len(X_train_proc)}, seq_len={self.sequence_length})."
            )

        logger.info(f"Generated {len(X_seq_train)} training sequences with shape {X_seq_train.shape}")

        # 2. Construct Validation Sequences
        X_seq_val = None
        X_seq_val_norm = None
        X_seq_val_att = None
        if X_val_proc is not None and y_val_binary is not None and len(X_val_proc) >= self.sequence_length:
            X_val_seq_all, y_val_seq_bin, _, _ = self.sequence_builder.build_sequences(
                X=X_val_proc,
                y_binary=y_val_binary,
                raise_if_insufficient=False,
            )
            if len(X_val_seq_all) > 0 and y_val_seq_bin is not None:
                norm_val_mask = (y_val_seq_bin == 0)
                att_val_mask = (y_val_seq_bin == 1)
                if np.any(norm_val_mask):
                    X_seq_val_norm = X_val_seq_all[norm_val_mask]
                    X_seq_val = X_seq_val_norm
                if np.any(att_val_mask):
                    X_seq_val_att = X_val_seq_all[att_val_mask]

        # 3. Instantiate and Train Detector
        self.detector = LSTMAutoencoderDetector(
            input_dim=len(X_train_proc.columns),
            seq_len=self.sequence_length,
            encoder_units=self.encoder_units,
            latent_dim=self.latent_dim,
            decoder_units=self.decoder_units,
            num_layers=self.num_layers,
            dropout_rate=self.dropout_rate,
            learning_rate=self.learning_rate,
            batch_size=self.batch_size,
            epochs=self.epochs,
            early_stopping_patience=self.early_stopping_patience,
            random_seed=self.random_seed,
            threshold_percentile=self.threshold_percentile,
            device=self.device,
        )

        self.detector.train(
            X_seq_train=X_seq_train,
            X_seq_val=X_seq_val,
            feature_names=list(X_train_proc.columns),
        )

        # 4. Calibrate Threshold on Normal Validation Sequences
        if X_seq_val_norm is not None and len(X_seq_val_norm) > 0:
            self.detector.calibrate_threshold_and_bounds(
                X_val_normal_seq=X_seq_val_norm,
                X_val_attack_seq=X_seq_val_att,
                strategy=self.threshold_strategy,
                percentile=self.threshold_percentile,
            )
        else:
            logger.warning("No validation sequences available; using training sequence threshold calibration.")
            self.detector.calibrate_threshold_and_bounds(
                X_val_normal_seq=X_seq_train,
                strategy=self.threshold_strategy,
                percentile=self.threshold_percentile,
            )

        self.training_duration_sec = round(time.perf_counter() - start_time, 2)
        logger.info(f"LSTM Autoencoder training completed in {self.training_duration_sec} seconds.")

        # 5. Populate Training Metadata
        self.training_metadata = {
            "model_name": "lstm_autoencoder",
            "version": self.version,
            "dataset": self.dataset_name,
            "training_timestamp": datetime.now(timezone.utc).isoformat(),
            "training_duration_seconds": self.training_duration_sec,
            "normal_only_training": self.normal_only_training,
            "sequence_config": {
                "sequence_length": self.sequence_length,
                "stride": self.sequence_stride,
                "label_aggregation": self.sequence_builder.label_aggregation,
            },
            "architecture": {
                "input_dimension": len(X_train_proc.columns),
                "sequence_length": self.sequence_length,
                "encoder_units": self.encoder_units,
                "latent_dimension": self.latent_dim,
                "decoder_units": self.decoder_units,
                "num_layers": self.num_layers,
                "dropout_rate": self.dropout_rate,
            },
            "hyperparameters": {
                "learning_rate": self.learning_rate,
                "batch_size": self.batch_size,
                "max_epochs": self.epochs,
                "early_stopping_patience": self.early_stopping_patience,
                "random_seed": self.random_seed,
            },
            "training_samples_raw_rows": len(X_train_proc),
            "training_sequences_count": len(X_seq_train),
            "validation_sequences_count": len(X_seq_val) if X_seq_val is not None else 0,
            "reconstruction_threshold": round(self.detector.reconstruction_threshold, 6),
            "threshold_strategy": self.detector.threshold_strategy,
            "mse_min": round(self.detector.mse_min_, 6),
            "mse_max": round(self.detector.mse_max_, 6),
            "feature_names": list(X_train_proc.columns),
            "feature_count": len(X_train_proc.columns),
        }
        return self.detector

    def save_artifacts(
        self,
        output_dir: Optional[Union[str, Path]] = None,
        preprocessing_dir: Optional[Union[str, Path]] = None,
    ) -> Tuple[Path, Path]:
        """Save .pt model weights, metadata.json, and register in model registry."""
        if not self.detector or not self.detector.is_trained:
            raise RuntimeError("Cannot save artifacts: Model is not trained.")

        out_dir = Path(output_dir) if output_dir else settings.MODELS_DIR
        ensure_dir(out_dir)

        model_filename = f"lstm_autoencoder_{self.dataset_name}_v{self.version}.pt"
        metadata_filename = f"lstm_autoencoder_{self.dataset_name}_v{self.version}_metadata.json"

        model_path = out_dir / model_filename
        metadata_path = out_dir / metadata_filename

        # Save PyTorch model state
        self.detector.save(model_path)

        # Update metadata paths
        self.training_metadata["artifact_path"] = str(model_path)
        self.training_metadata["metadata_path"] = str(metadata_path)
        if preprocessing_dir:
            self.training_metadata["preprocessing_artifact_path"] = str(preprocessing_dir)

        save_metadata(self.training_metadata, metadata_path)

        # Register in central ModelRegistry
        model_registry.register_model(
            model_name="lstm_autoencoder",
            dataset=self.dataset_name,
            version=self.version,
            artifact_path=str(model_path),
            model_type="sequential_anomaly_detector",
            feature_count=self.training_metadata["feature_count"],
            feature_names=self.training_metadata.get("feature_names"),
            preprocessing_dir=str(preprocessing_dir) if preprocessing_dir else None,
            hyperparameters=self.training_metadata.get("hyperparameters"),
            metrics={"reconstruction_threshold": self.detector.reconstruction_threshold},
            training_samples=self.training_metadata.get("training_sequences_count", 0),
            set_active=True,
        )

        logger.info(f"LSTM Autoencoder model artifact saved to: {model_path}")
        logger.info(f"LSTM Autoencoder metadata saved to: {metadata_path}")
        return model_path, metadata_path
