from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from backend.app.core.logging import logger
from backend.app.ml.data.utils.data_utils import save_artifact, load_artifact


class IsolationForestDetector:
    """
    Production-grade Isolation Forest unsupervised anomaly detector for network intrusion & zero-day detection.
    
    Trained primarily on baseline normal traffic to learn benign topology.
    Transforms raw tree partition depths into application-level normalized anomaly scores (0.0 to 100.0).
    """

    def __init__(
        self,
        n_estimators: int = 100,
        contamination: float = 0.05,
        max_samples: Union[str, int, float] = "auto",
        max_features: float = 1.0,
        bootstrap: bool = False,
        random_state: int = 42,
        n_jobs: int = -1,
        anomaly_threshold: float = 60.0,
    ):
        self.n_estimators = n_estimators
        self.contamination = contamination
        self.max_samples = max_samples
        self.max_features = max_features
        self.bootstrap = bootstrap
        self.random_state = random_state
        self.n_jobs = n_jobs
        self.anomaly_threshold = anomaly_threshold  # Normalized score threshold (0-100)

        self.model: Optional[IsolationForest] = None
        self.is_trained: bool = False
        self.feature_count_: int = 0
        self.feature_names_: List[str] = []

        # Empirical calibration bounds on normal baseline scores for 0-100 normalization
        self.score_min_: float = -1.0  # lowest score observed (most anomalous)
        self.score_max_: float = 0.0   # highest score observed (most normal)

    def _ensure_numpy(self, X: Union[np.ndarray, pd.DataFrame]) -> np.ndarray:
        """Convert input to contiguous 2D float32 numpy array and validate."""
        if isinstance(X, pd.DataFrame):
            if not self.feature_names_ and not self.is_trained:
                self.feature_names_ = list(X.columns)
            arr = X.to_numpy(dtype=np.float32)
        elif isinstance(X, np.ndarray):
            arr = X.astype(np.float32)
        else:
            raise TypeError(f"Expected pd.DataFrame or np.ndarray, got {type(X)}")

        if arr.ndim == 1:
            arr = arr.reshape(1, -1)

        if np.isnan(arr).any() or np.isinf(arr).any():
            raise ValueError("Input array contains NaN or infinite values.")

        return arr

    def train(self, X: Union[np.ndarray, pd.DataFrame], feature_names: Optional[List[str]] = None) -> "IsolationForestDetector":
        """
        Train Isolation Forest model on baseline network traffic (typically normal/benign).
        """
        X_arr = self._ensure_numpy(X)
        self.feature_count_ = X_arr.shape[1]
        if feature_names:
            self.feature_names_ = list(feature_names)
        elif isinstance(X, pd.DataFrame):
            self.feature_names_ = list(X.columns)

        logger.info(
            f"Training IsolationForest: samples={X_arr.shape[0]}, features={self.feature_count_}, "
            f"n_estimators={self.n_estimators}, contamination={self.contamination}, random_state={self.random_state}"
        )

        self.model = IsolationForest(
            n_estimators=self.n_estimators,
            contamination=self.contamination,
            max_samples=self.max_samples,
            max_features=self.max_features,
            bootstrap=self.bootstrap,
            random_state=self.random_state,
            n_jobs=self.n_jobs,
        )

        self.model.fit(X_arr)
        self.is_trained = True

        # Initial calibration based on training normal data
        raw_train_scores = self.model.score_samples(X_arr)
        self.score_max_ = float(np.percentile(raw_train_scores, 99))
        self.score_min_ = float(np.percentile(raw_train_scores, 1)) - 0.15

        logger.info(
            f"IsolationForest trained successfully. Baseline score range: [{self.score_min_:.4f}, {self.score_max_:.4f}]"
        )
        return self

    def calibrate_score_bounds(self, X_val_normal: Union[np.ndarray, pd.DataFrame], X_val_attack: Optional[Union[np.ndarray, pd.DataFrame]] = None) -> None:
        """
        Calibrate score transformation min/max bounds using validation sets to ensure robust 0-100 scaling.
        """
        if not self.is_trained or self.model is None:
            raise RuntimeError("Model must be trained before score calibration.")

        val_norm_arr = self._ensure_numpy(X_val_normal)
        norm_scores = self.model.score_samples(val_norm_arr)
        
        self.score_max_ = float(np.percentile(norm_scores, 95))
        
        if X_val_attack is not None:
            val_att_arr = self._ensure_numpy(X_val_attack)
            att_scores = self.model.score_samples(val_att_arr)
            self.score_min_ = float(np.min(att_scores)) - 0.05
        else:
            self.score_min_ = float(np.min(norm_scores)) - 0.25

        logger.info(f"Calibrated anomaly score bounds: min={self.score_min_:.4f}, max={self.score_max_:.4f}")

    def score_samples(self, X: Union[np.ndarray, pd.DataFrame]) -> np.ndarray:
        """
        Raw scikit-learn anomaly scores.
        Note: Lower/more negative values indicate higher anomaly likelihood.
        """
        if not self.is_trained or self.model is None:
            raise RuntimeError("Model is not trained.")
        X_arr = self._ensure_numpy(X)
        return self.model.score_samples(X_arr)

    def decision_function(self, X: Union[np.ndarray, pd.DataFrame]) -> np.ndarray:
        """
        Raw decision function scores. Positive = inliers, Negative = outliers.
        """
        if not self.is_trained or self.model is None:
            raise RuntimeError("Model is not trained.")
        X_arr = self._ensure_numpy(X)
        return self.model.decision_function(X_arr)

    def compute_anomaly_scores(self, X: Union[np.ndarray, pd.DataFrame]) -> np.ndarray:
        """
        Compute application-level normalized anomaly scores between 0.0 and 100.0.
        
        Higher score = greater anomaly/outlier likelihood.
        Transformation:
            normalized_score = 100.0 * (score_max - raw_score) / (score_max - score_min)
            clamped strictly to [0.0, 100.0]
        """
        raw_scores = self.score_samples(X)
        denom = max(1e-6, self.score_max_ - self.score_min_)
        
        # Invert: higher raw_score (normal) -> lower anomaly score (near 0)
        # lower raw_score (anomaly) -> higher anomaly score (near 100)
        normalized = 100.0 * (self.score_max_ - raw_scores) / denom
        normalized = np.clip(normalized, 0.0, 100.0)
        return np.round(normalized, 2)

    def predict_binary(self, X: Union[np.ndarray, pd.DataFrame], threshold: Optional[float] = None) -> np.ndarray:
        """
        Predict binary anomaly indicator: 0 = Normal, 1 = Anomaly based on anomaly_threshold.
        """
        thresh = threshold if threshold is not None else self.anomaly_threshold
        scores = self.compute_anomaly_scores(X)
        return (scores >= thresh).astype(int)

    def predict(self, X: Union[np.ndarray, pd.DataFrame]) -> np.ndarray:
        """Standard scikit-learn prediction: 1 = normal, -1 = anomaly."""
        if not self.is_trained or self.model is None:
            raise RuntimeError("Model is not trained.")
        X_arr = self._ensure_numpy(X)
        return self.model.predict(X_arr)

    def get_params(self) -> Dict[str, Any]:
        """Return model hyperparameter dictionary."""
        return {
            "n_estimators": self.n_estimators,
            "contamination": self.contamination,
            "max_samples": self.max_samples,
            "max_features": self.max_features,
            "bootstrap": self.bootstrap,
            "random_state": self.random_state,
            "n_jobs": self.n_jobs,
            "anomaly_threshold": self.anomaly_threshold,
            "score_min": self.score_min_,
            "score_max": self.score_max_,
            "feature_count": self.feature_count_,
        }

    def save(self, file_path: Union[str, Path]) -> Path:
        """Save detector instance to disk using joblib."""
        if not self.is_trained:
            raise RuntimeError("Cannot save an unfitted IsolationForestDetector.")
        return save_artifact(self, file_path)

    @classmethod
    def load(cls, file_path: Union[str, Path]) -> "IsolationForestDetector":
        """Load detector instance from disk."""
        obj = load_artifact(file_path)
        if not isinstance(obj, cls):
            raise TypeError(f"Loaded object is not an instance of {cls.__name__}, got {type(obj)}")
        return obj
