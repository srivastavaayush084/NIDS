import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd
from sklearn.metrics import precision_recall_fscore_support
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.ml.models.autoencoder import AutoencoderDetector
from backend.app.ml.registry.model_registry import model_registry
from backend.app.ml.data.utils.data_utils import ensure_dir, save_metadata


class AutoencoderTrainer:
    """
    Orchestrates the end-to-end training lifecycle of the Deep Learning Autoencoder Anomaly Detector.
    Enforces a strict Normal-Only Baseline Training Strategy to model benign network flow topology
    and calibrates reconstruction-error thresholds on validation data.
    """

    def __init__(
        self,
        dataset_name: str = "synthetic",
        version: str = "1.0.0",
        hidden_dims: Optional[List[int]] = None,
        latent_dim: Optional[int] = None,
        encoder_layers: Optional[List[int]] = None,
        decoder_layers: Optional[List[int]] = None,
        activation: str = "relu",
        dropout_rate: float = 0.0,
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
        self.hidden_dims = hidden_dims if hidden_dims is not None else [64, 32]
        self.encoder_layers = encoder_layers
        self.decoder_layers = decoder_layers
        self.latent_dim = latent_dim or settings.AUTOENCODER_LATENT_DIM
        self.activation = activation
        self.dropout_rate = dropout if dropout is not None else dropout_rate
        self.learning_rate = learning_rate or settings.AUTOENCODER_LEARNING_RATE
        self.batch_size = batch_size or settings.AUTOENCODER_BATCH_SIZE
        self.epochs = epochs or settings.AUTOENCODER_EPOCHS
        self.early_stopping_patience = early_stopping_patience or settings.AUTOENCODER_EARLY_STOPPING_PATIENCE
        self.random_seed = random_seed or settings.AUTOENCODER_RANDOM_SEED
        self.threshold_percentile = threshold_percentile or settings.AUTOENCODER_THRESHOLD_PERCENTILE
        self.threshold_strategy = threshold_strategy or "percentile"
        self.device = device
        self.normal_only_training = normal_only_training

        self.detector: Optional[AutoencoderDetector] = None
        self.training_duration_sec: float = 0.0
        self.training_metadata: Dict[str, Any] = {}

    def train(
        self,
        X_train_proc: pd.DataFrame,
        y_train_binary: pd.Series,
        X_val_proc: Optional[pd.DataFrame] = None,
        y_val_binary: Optional[pd.Series] = None,
        pipeline_dir: Optional[Union[str, Path]] = None,
    ) -> AutoencoderDetector:
        """
        Execute training on normal baseline features and calibrate decision threshold on validation data.
        """
        logger.info("=" * 60)
        logger.info(f"TRAINING AUTOENCODER: dataset='{self.dataset_name}', version='{self.version}'")
        logger.info("=" * 60)

        start_time = time.perf_counter()

        # 1. Normal-Only Training Strategy
        if self.normal_only_training:
            normal_mask = (y_train_binary == 0).to_numpy()
            X_fit = X_train_proc.iloc[normal_mask].reset_index(drop=True)
            logger.info(
                f"Normal-Only Training Strategy: Filtered {len(X_fit)} normal baseline samples "
                f"from {len(X_train_proc)} total training samples."
            )
        else:
            X_fit = X_train_proc
            logger.warning("Training on mixed normal + attack samples (normal_only_training=False).")

        # 2. Filter Normal Validation Samples for early stopping & calibration
        X_val_fit = None
        X_val_att = None
        if X_val_proc is not None and y_val_binary is not None and len(X_val_proc) > 0:
            val_norm_mask = (y_val_binary == 0).to_numpy()
            val_att_mask = (y_val_binary == 1).to_numpy()
            if np.any(val_norm_mask):
                X_val_fit = X_val_proc.iloc[val_norm_mask].reset_index(drop=True)
            if np.any(val_att_mask):
                X_val_att = X_val_proc.iloc[val_att_mask].reset_index(drop=True)

        # 3. Instantiate and Train Detector
        self.detector = AutoencoderDetector(
            input_dim=len(X_train_proc.columns),
            hidden_dims=self.hidden_dims,
            latent_dim=self.latent_dim,
            encoder_layers=self.encoder_layers,
            decoder_layers=self.decoder_layers,
            activation=self.activation,
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
            X_train=X_fit,
            X_val=X_val_fit,
            feature_names=list(X_train_proc.columns),
        )

        # 4. Calibrate Threshold on Validation Data
        if X_val_fit is not None and len(X_val_fit) > 0:
            self.detector.calibrate_threshold_and_bounds(
                X_val_normal=X_val_fit,
                X_val_attack=X_val_att,
                strategy="percentile",
                percentile=self.threshold_percentile,
            )

        self.training_duration_sec = time.perf_counter() - start_time
        logger.info(f"Autoencoder training completed in {self.training_duration_sec:.2f} seconds.")
        return self.detector

    def save_artifacts(
        self,
        output_dir: Optional[Union[str, Path]] = None,
        preprocessing_dir: Optional[Union[str, Path]] = None,
    ) -> Tuple[Path, Path]:
        """
        Save trained Autoencoder model checkpoint, metadata JSON, and enroll in ModelRegistry.
        """
        if self.detector is None or not self.detector.is_trained:
            raise RuntimeError("Cannot save unfitted Autoencoder.")

        models_dir = Path(output_dir) if output_dir else settings.MODELS_DIR
        ensure_dir(models_dir)

        model_filename = f"autoencoder_{self.dataset_name}_v{self.version}.pt"
        metadata_filename = f"autoencoder_{self.dataset_name}_v{self.version}_metadata.json"

        model_path = models_dir / model_filename
        metadata_path = models_dir / metadata_filename

        # Save model PyTorch checkpoint
        self.detector.save(model_path)

        # Build comprehensive metadata
        metadata = {
            "model_name": "autoencoder",
            "model_type": "deep_learning_autoencoder",
            "dataset": self.dataset_name,
            "version": self.version,
            "trained_at": datetime.now(timezone.utc).isoformat(),
            "training_duration_sec": round(self.training_duration_sec, 3),
            "hyperparameters": self.detector.get_params(),
            "feature_count": len(self.detector.feature_names_),
            "feature_names": self.detector.feature_names_,
            "reconstruction_threshold": self.detector.reconstruction_threshold,
            "threshold_strategy": self.detector.threshold_strategy,
            "score_bounds": {
                "mse_min": self.detector.mse_min_,
                "mse_max": self.detector.mse_max_,
            },
            "training_strategy": {
                "normal_only_training": self.normal_only_training,
                "random_seed": self.random_seed,
            },
            "preprocessing_dir": str(preprocessing_dir) if preprocessing_dir else str(settings.PREPROCESSING_DIR / self.dataset_name),
            "artifact_path": str(model_path),
        }

        save_metadata(metadata, metadata_path)
        self.training_metadata = metadata

        # Register in Model Registry
        model_registry.register_model(
            model_name="autoencoder",
            dataset=self.dataset_name,
            version=self.version,
            artifact_path=model_path,
            model_type="deep_learning_autoencoder",
            feature_count=len(self.detector.feature_names_),
            feature_names=self.detector.feature_names_,
            preprocessing_dir=preprocessing_dir or (settings.PREPROCESSING_DIR / self.dataset_name),
            hyperparameters=self.detector.get_params(),
            set_active=True,
        )

        logger.info(f"Autoencoder model artifact saved to: {model_path}")
        logger.info(f"Autoencoder metadata saved to: {metadata_path}")
        return model_path, metadata_path
