import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.ml.models.random_forest import RandomForestClassifierModel
from backend.app.ml.registry.model_registry import model_registry
from backend.app.ml.data.utils.data_utils import ensure_dir, save_metadata


class RandomForestTrainer:
    """
    Orchestrates the training lifecycle of the Supervised Random Forest Baseline Classifier.
    Trains on labeled training features (normal + known attacks), calibrates decision thresholds,
    extracts Gini feature importances, and registers model artifacts.
    """

    def __init__(
        self,
        dataset_name: str = "synthetic",
        version: str = "1.0.0",
        n_estimators: Optional[int] = None,
        max_depth: Optional[int] = None,
        min_samples_split: Optional[int] = None,
        min_samples_leaf: Optional[int] = None,
        max_features: Optional[Union[str, float, int]] = None,
        bootstrap: bool = True,
        class_weight: Optional[Union[str, Dict[Any, Any]]] = "balanced",
        criterion: str = "gini",
        random_state: Optional[int] = None,
        n_jobs: Optional[int] = None,
        decision_threshold: Optional[float] = None,
        tune_threshold: bool = True,
    ):
        self.dataset_name = dataset_name.lower().strip()
        self.version = version
        self.n_estimators = n_estimators or settings.RF_N_ESTIMATORS
        self.max_depth = max_depth or settings.RF_MAX_DEPTH
        self.min_samples_split = min_samples_split or settings.RF_MIN_SAMPLES_SPLIT
        self.min_samples_leaf = min_samples_leaf or settings.RF_MIN_SAMPLES_LEAF
        self.max_features = max_features or settings.RF_MAX_FEATURES
        self.bootstrap = bootstrap
        self.class_weight = class_weight if class_weight is not None else settings.RF_CLASS_WEIGHT
        self.criterion = criterion
        self.random_state = random_state or settings.RF_RANDOM_SEED
        self.n_jobs = n_jobs if n_jobs is not None else settings.RF_N_JOBS
        self.decision_threshold = decision_threshold if decision_threshold is not None else settings.RF_THRESHOLD
        self.tune_threshold = tune_threshold

        self.model: Optional[RandomForestClassifierModel] = None
        self.training_duration_sec: float = 0.0
        self.training_metadata: Dict[str, Any] = {}

    def train(
        self,
        X_train_proc: pd.DataFrame,
        y_train_binary: pd.Series,
        X_val_proc: Optional[pd.DataFrame] = None,
        y_val_binary: Optional[pd.Series] = None,
        pipeline_dir: Optional[Union[str, Path]] = None,
    ) -> RandomForestClassifierModel:
        """
        Execute supervised training on labeled features and calibrate threshold on validation data.
        """
        logger.info("=" * 60)
        logger.info(f"TRAINING RANDOM FOREST BASELINE: dataset='{self.dataset_name}', version='{self.version}'")
        logger.info("=" * 60)

        start_time = time.perf_counter()

        # Check class distribution
        y_arr = np.asarray(y_train_binary, dtype=int).ravel()
        normal_count = int(np.sum(y_arr == 0))
        attack_count = int(np.sum(y_arr == 1))
        logger.info(
            f"Supervised Training Distribution: {len(X_train_proc)} total samples "
            f"(Normal: {normal_count}, Attack: {attack_count})"
        )

        # 1. Instantiate and Train Classifier
        self.model = RandomForestClassifierModel(
            n_estimators=self.n_estimators,
            max_depth=self.max_depth,
            min_samples_split=self.min_samples_split,
            min_samples_leaf=self.min_samples_leaf,
            max_features=self.max_features,
            bootstrap=self.bootstrap,
            class_weight=self.class_weight,
            criterion=self.criterion,
            random_state=self.random_state,
            n_jobs=self.n_jobs,
            decision_threshold=self.decision_threshold,
        )

        self.model.train(
            X_train=X_train_proc,
            y_train=y_train_binary,
            feature_names=list(X_train_proc.columns),
        )

        # 2. Tune Decision Threshold on Validation Data if available
        if self.tune_threshold and X_val_proc is not None and y_val_binary is not None and len(X_val_proc) > 0:
            self.model.determine_threshold(X_val_proc, y_val_binary, strategy="f1_optimal")
        else:
            self.model.optimal_threshold_ = self.decision_threshold

        self.training_duration_sec = round(time.perf_counter() - start_time, 2)
        logger.info(f"Random Forest training completed in {self.training_duration_sec} seconds.")

        # 3. Populate Comprehensive Training Metadata
        top_importances = self.model.get_feature_importances(top_n=15)
        self.training_metadata = {
            "model_name": "random_forest",
            "version": self.version,
            "dataset": self.dataset_name,
            "training_timestamp": datetime.now(timezone.utc).isoformat(),
            "training_duration_seconds": self.training_duration_sec,
            "model_type": "supervised_classifier_baseline",
            "hyperparameters": self.model.get_params(),
            "training_samples_total": len(X_train_proc),
            "class_distribution": {
                "normal": normal_count,
                "attack": attack_count,
            },
            "validation_samples_total": len(X_val_proc) if X_val_proc is not None else 0,
            "decision_threshold": round(self.model.decision_threshold, 4),
            "threshold_strategy": self.model.threshold_strategy,
            "feature_names": list(X_train_proc.columns),
            "feature_count": len(X_train_proc.columns),
            "top_feature_importances": top_importances,
        }
        return self.model

    def save_artifacts(
        self,
        output_dir: Optional[Union[str, Path]] = None,
        preprocessing_dir: Optional[Union[str, Path]] = None,
    ) -> Tuple[Path, Path]:
        """Save .joblib model checkpoint, metadata.json, and register in model registry."""
        if not self.model or not self.model.is_trained:
            raise RuntimeError("Cannot save artifacts: Model is not trained.")

        out_dir = Path(output_dir) if output_dir else settings.MODELS_DIR
        ensure_dir(out_dir)

        model_filename = f"random_forest_{self.dataset_name}_v{self.version}.joblib"
        metadata_filename = f"random_forest_{self.dataset_name}_v{self.version}_metadata.json"

        model_path = out_dir / model_filename
        metadata_path = out_dir / metadata_filename

        # Save Joblib model state
        self.model.save(model_path)

        # Update metadata paths
        self.training_metadata["artifact_path"] = str(model_path)
        self.training_metadata["metadata_path"] = str(metadata_path)
        if preprocessing_dir:
            self.training_metadata["preprocessing_artifact_path"] = str(preprocessing_dir)

        save_metadata(self.training_metadata, metadata_path)

        # Register in central ModelRegistry
        model_registry.register_model(
            model_name="random_forest",
            dataset=self.dataset_name,
            version=self.version,
            artifact_path=str(model_path),
            model_type="supervised_classifier_baseline",
            feature_count=self.training_metadata["feature_count"],
            feature_names=self.training_metadata.get("feature_names"),
            preprocessing_dir=str(preprocessing_dir) if preprocessing_dir else None,
            hyperparameters=self.training_metadata.get("hyperparameters"),
            metrics={"decision_threshold": self.model.decision_threshold},
            training_samples=self.training_metadata.get("training_samples_total", 0),
            set_active=True,
        )

        logger.info(f"Random Forest model artifact saved to: {model_path}")
        logger.info(f"Random Forest metadata saved to: {metadata_path}")
        return model_path, metadata_path
