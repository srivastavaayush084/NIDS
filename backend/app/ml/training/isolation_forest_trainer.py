from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd
from sklearn.metrics import precision_recall_fscore_support
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.ml.models.isolation_forest import IsolationForestDetector
from backend.app.ml.data.loaders.factory import get_dataset_loader
from backend.app.ml.data.preprocessing.pipeline import NetworkDataPipeline
from backend.app.ml.data.splitting.dataset_splitter import DatasetSplitter, SplitResult
from backend.app.ml.registry.model_registry import model_registry
from backend.app.ml.data.utils.data_utils import ensure_dir, save_metadata, load_dataframe


class IsolationForestTrainer:
    """
    Orchestrates the training lifecycle for the Isolation Forest Anomaly Detector.
    Enforces a strict Normal-Only Baseline Training Strategy to prevent target leakage
    and establishes empirical anomaly score calibration bounds.
    """

    def __init__(
        self,
        dataset_name: str = "synthetic",
        version: str = "1.0.0",
        n_estimators: int = 100,
        contamination: float = 0.05,
        max_samples: Union[str, int, float] = "auto",
        max_features: float = 1.0,
        bootstrap: bool = False,
        random_state: int = 42,
        n_jobs: int = -1,
        normal_only_training: bool = True,
    ):
        self.dataset_name = dataset_name.lower().strip()
        self.version = version
        self.n_estimators = n_estimators
        self.contamination = contamination
        self.max_samples = max_samples
        self.max_features = max_features
        self.bootstrap = bootstrap
        self.random_state = random_state
        self.n_jobs = n_jobs
        self.normal_only_training = normal_only_training

        self.detector: Optional[IsolationForestDetector] = None
        self.pipeline: Optional[NetworkDataPipeline] = None
        self.training_metadata: Dict[str, Any] = {}
        self.optimal_threshold_: float = 60.0

    def find_optimal_threshold(
        self,
        detector: IsolationForestDetector,
        X_val_proc: np.ndarray,
        y_val_binary: np.ndarray,
    ) -> float:
        """
        Evaluate candidate thresholds on validation data to identify the best balance of F1 and Recall.
        Does NOT touch test data.
        """
        if len(y_val_binary) == 0 or len(np.unique(y_val_binary)) < 2:
            return 60.0  # Default threshold if validation class diversity is limited

        val_scores = detector.compute_anomaly_scores(X_val_proc)
        candidate_thresholds = np.linspace(20.0, 85.0, 27)
        best_threshold = 60.0
        best_f1 = -1.0

        for thresh in candidate_thresholds:
            preds = (val_scores >= thresh).astype(int)
            prec, rec, f1, _ = precision_recall_fscore_support(
                y_val_binary, preds, average="binary", zero_division=0
            )
            if f1 > best_f1:
                best_f1 = f1
                best_threshold = float(thresh)

        logger.info(f"Validation threshold search: Best threshold={best_threshold:.1f} (Validation F1={best_f1:.4f})")
        return best_threshold

    def train(
        self,
        X_train_proc: pd.DataFrame,
        y_train_binary: pd.Series,
        X_val_proc: Optional[pd.DataFrame] = None,
        y_val_binary: Optional[pd.Series] = None,
        pipeline_dir: Optional[Union[str, Path]] = None,
    ) -> IsolationForestDetector:
        """
        Train Isolation Forest model on processed features.
        """
        logger.info("=" * 60)
        logger.info(f"TRAINING ISOLATION FOREST: dataset='{self.dataset_name}', version='{self.version}'")
        logger.info("=" * 60)

        # 1. Normal-Only Training Data Filtering
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

        # 2. Instantiate and Fit Model
        self.detector = IsolationForestDetector(
            n_estimators=self.n_estimators,
            contamination=self.contamination,
            max_samples=self.max_samples,
            max_features=self.max_features,
            bootstrap=self.bootstrap,
            random_state=self.random_state,
            n_jobs=self.n_jobs,
        )

        self.detector.train(X_fit, feature_names=list(X_train_proc.columns))

        # 3. Validation Calibration & Threshold Tuning
        if X_val_proc is not None and y_val_binary is not None and len(X_val_proc) > 0:
            val_norm_mask = (y_val_binary == 0).to_numpy()
            val_att_mask = (y_val_binary == 1).to_numpy()
            
            X_val_norm = X_val_proc.iloc[val_norm_mask] if np.any(val_norm_mask) else X_fit
            X_val_att = X_val_proc.iloc[val_att_mask] if np.any(val_att_mask) else None

            self.detector.calibrate_score_bounds(X_val_norm, X_val_att)
            self.optimal_threshold_ = self.find_optimal_threshold(
                self.detector,
                X_val_proc.to_numpy(dtype=np.float32),
                y_val_binary.to_numpy()
            )
            self.detector.anomaly_threshold = self.optimal_threshold_

        return self.detector

    def save_artifacts(
        self,
        output_dir: Optional[Union[str, Path]] = None,
        preprocessing_dir: Optional[Union[str, Path]] = None,
    ) -> Tuple[Path, Path]:
        """
        Save trained model artifact, metadata JSON, and register with ModelRegistry.
        """
        if self.detector is None or not self.detector.is_trained:
            raise RuntimeError("Cannot save unfitted model.")

        models_dir = Path(output_dir) if output_dir else settings.MODELS_DIR
        ensure_dir(models_dir)

        model_filename = f"isolation_forest_{self.dataset_name}_v{self.version}.joblib"
        metadata_filename = f"isolation_forest_{self.dataset_name}_v{self.version}_metadata.json"

        model_path = models_dir / model_filename
        metadata_path = models_dir / metadata_filename

        # Save model joblib
        self.detector.save(model_path)

        # Build comprehensive metadata
        metadata = {
            "model_name": "isolation_forest",
            "model_type": "unsupervised_anomaly_detector",
            "dataset": self.dataset_name,
            "version": self.version,
            "trained_at": datetime.now(timezone.utc).isoformat(),
            "hyperparameters": self.detector.get_params(),
            "optimal_threshold": self.optimal_threshold_,
            "feature_count": self.detector.feature_count_,
            "feature_names": self.detector.feature_names_,
            "score_bounds": {
                "score_min": self.detector.score_min_,
                "score_max": self.detector.score_max_,
            },
            "training_strategy": {
                "normal_only_training": self.normal_only_training,
                "random_state": self.random_state,
            },
            "preprocessing_dir": str(preprocessing_dir) if preprocessing_dir else str(settings.PREPROCESSING_DIR / self.dataset_name),
            "artifact_path": str(model_path),
        }

        save_metadata(metadata, metadata_path)
        self.training_metadata = metadata

        # Register in Model Registry
        model_registry.register_model(
            model_name="isolation_forest",
            dataset=self.dataset_name,
            version=self.version,
            artifact_path=model_path,
            model_type="unsupervised_anomaly_detector",
            feature_count=self.detector.feature_count_,
            feature_names=self.detector.feature_names_,
            preprocessing_dir=preprocessing_dir or (settings.PREPROCESSING_DIR / self.dataset_name),
            hyperparameters=self.detector.get_params(),
            set_active=True,
        )

        logger.info(f"Model artifact saved to: {model_path}")
        logger.info(f"Model metadata saved to: {metadata_path}")
        return model_path, metadata_path
