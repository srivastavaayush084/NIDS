from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import precision_recall_fscore_support

from backend.app.core.logging import logger
from backend.app.ml.data.utils.data_utils import ensure_dir


class RandomForestClassifierModel:
    """
    Supervised Random Forest Classifier serving as a benchmark baseline model.
    Trains on labeled network traffic (both normal and known attack classes)
    to classify events and extracts feature importances for comparative evaluation.
    """

    def __init__(
        self,
        n_estimators: int = 100,
        max_depth: Optional[int] = None,
        min_samples_split: int = 2,
        min_samples_leaf: int = 1,
        max_features: Union[str, float, int] = "sqrt",
        bootstrap: bool = True,
        class_weight: Optional[Union[str, Dict[Any, Any]]] = "balanced",
        criterion: str = "gini",
        random_state: int = 42,
        n_jobs: int = -1,
        decision_threshold: float = 0.5,
    ):
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.min_samples_split = min_samples_split
        self.min_samples_leaf = min_samples_leaf
        self.max_features = max_features
        self.bootstrap = bootstrap
        self.class_weight = class_weight
        self.criterion = criterion
        self.random_state = random_state
        self.n_jobs = n_jobs
        self.decision_threshold = decision_threshold

        self.model: Optional[RandomForestClassifier] = None
        self.is_trained: bool = False
        self.feature_names_: List[str] = []
        self.classes_: List[int] = [0, 1]
        self.feature_importances_dict_: Dict[str, float] = {}
        self.optimal_threshold_: float = decision_threshold
        self.threshold_strategy: str = "default_0.5"

    @property
    def feature_count_(self) -> int:
        """Return total number of input features."""
        return len(self.feature_names_)

    def _ensure_numpy(self, X: Union[np.ndarray, pd.DataFrame]) -> np.ndarray:
        """Convert input data to 2D float32 numpy array and validate."""
        if isinstance(X, pd.DataFrame):
            if not self.feature_names_ and not self.is_trained:
                self.feature_names_ = list(X.columns)
            arr = X.to_numpy(dtype=np.float32).copy()
        elif isinstance(X, np.ndarray):
            arr = X.astype(np.float32).copy()
        else:
            raise TypeError(f"Expected pd.DataFrame or np.ndarray, got {type(X)}")

        if arr.ndim == 1:
            arr = arr.reshape(1, -1)

        if np.isnan(arr).any() or np.isinf(arr).any():
            raise ValueError("Input array contains NaN or infinite values.")

        return np.ascontiguousarray(arr)

    def train(
        self,
        X_train: Union[np.ndarray, pd.DataFrame],
        y_train: Union[np.ndarray, pd.Series],
        feature_names: Optional[List[str]] = None,
    ) -> "RandomForestClassifierModel":
        """
        Train Random Forest model on labeled feature matrix X and binary labels y.
        """
        X_arr = self._ensure_numpy(X_train)
        y_arr = np.asarray(y_train, dtype=int).ravel()

        if len(X_arr) != len(y_arr):
            raise ValueError(f"X rows ({len(X_arr)}) and y labels ({len(y_arr)}) must match.")

        if feature_names:
            self.feature_names_ = list(feature_names)
        elif isinstance(X_train, pd.DataFrame):
            self.feature_names_ = list(X_train.columns)
        else:
            self.feature_names_ = [f"feature_{i}" for i in range(X_arr.shape[1])]

        logger.info(
            f"Training RandomForestClassifierModel: samples={len(X_arr)}, features={len(self.feature_names_)}, "
            f"n_estimators={self.n_estimators}, max_depth={self.max_depth}, class_weight={self.class_weight}"
        )

        self.model = RandomForestClassifier(
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
        )

        self.model.fit(X_arr, y_arr)
        self.is_trained = True
        self.classes_ = list(self.model.classes_)

        # Extract Gini feature importances
        if hasattr(self.model, "feature_importances_"):
            raw_imp = self.model.feature_importances_
            self.feature_importances_dict_ = {
                name: float(raw_imp[i]) for i, name in enumerate(self.feature_names_)
            }

        logger.info(f"RandomForestClassifierModel training complete. Classes learned: {self.classes_}")
        return self

    def predict_proba(self, X: Union[np.ndarray, pd.DataFrame]) -> np.ndarray:
        """
        Predict class probabilities. Returns array of shape (N, 2) with columns [P(0), P(1)].
        """
        if not self.is_trained or self.model is None:
            raise RuntimeError("Model is not trained.")

        X_arr = self._ensure_numpy(X)
        probs = self.model.predict_proba(X_arr)

        # Handle case where only 1 class was observed during training
        if probs.shape[1] == 1:
            only_class = self.classes_[0]
            full_probs = np.zeros((len(X_arr), 2), dtype=np.float32)
            full_probs[:, only_class] = probs[:, 0]
            full_probs[:, 1 - only_class] = 1.0 - probs[:, 0]
            return full_probs

        return probs.astype(np.float32)

    def predict_attack_probability(self, X: Union[np.ndarray, pd.DataFrame]) -> np.ndarray:
        """Return 1D array of predicted attack probabilities P(y=1)."""
        probs = self.predict_proba(X)
        return probs[:, 1]

    def predict_binary(
        self,
        X: Union[np.ndarray, pd.DataFrame],
        threshold: Optional[float] = None,
    ) -> np.ndarray:
        """Predict binary indicator: 0 = Normal, 1 = Attack based on decision threshold."""
        thresh = threshold if threshold is not None else self.decision_threshold
        attack_probs = self.predict_attack_probability(X)
        return (attack_probs >= thresh).astype(int)

    def compute_anomaly_scores(self, X: Union[np.ndarray, pd.DataFrame]) -> np.ndarray:
        """
        Transform predicted attack probability into normalized score (0.0 to 100.0).
        Score = 100.0 * P(attack).
        """
        attack_probs = self.predict_attack_probability(X)
        return np.round(np.clip(attack_probs * 100.0, 0.0, 100.0), 2)

    def get_feature_importances(self, top_n: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Return sorted list of features ranked by Gini importance.
        """
        if not self.feature_importances_dict_:
            return []

        sorted_items = sorted(
            self.feature_importances_dict_.items(),
            key=lambda item: item[1],
            reverse=True,
        )

        ranked = [
            {
                "feature": name,
                "importance": round(float(score), 6),
                "rank": rank + 1,
            }
            for rank, (name, score) in enumerate(sorted_items)
        ]

        if top_n is not None and top_n > 0:
            return ranked[:top_n]
        return ranked

    def determine_threshold(
        self,
        X_val: Union[np.ndarray, pd.DataFrame],
        y_val: Union[np.ndarray, pd.Series],
        strategy: str = "f1_optimal",
    ) -> float:
        """
        Tune decision threshold strictly on validation data to maximize F1 score.
        """
        y_val_arr = np.asarray(y_val, dtype=int).ravel()
        if len(np.unique(y_val_arr)) < 2:
            self.optimal_threshold_ = 0.5
            self.threshold_strategy = "default_0.5"
            return 0.5

        attack_probs = self.predict_attack_probability(X_val)
        best_thresh = 0.5
        best_f1 = -1.0

        if strategy == "f1_optimal":
            threshold_candidates = np.linspace(0.1, 0.9, 41)
            for t in threshold_candidates:
                preds = (attack_probs >= t).astype(int)
                _, _, f1, _ = precision_recall_fscore_support(
                    y_val_arr, preds, average="binary", zero_division=0
                )
                if f1 > best_f1:
                    best_f1 = f1
                    best_thresh = float(t)
            self.threshold_strategy = f"f1_optimal_val_{best_thresh:.2f}"
        else:
            best_thresh = 0.5
            self.threshold_strategy = "default_0.5"

        self.decision_threshold = best_thresh
        self.optimal_threshold_ = best_thresh
        logger.info(
            f"Random Forest Decision Threshold Calibrated: {self.decision_threshold:.4f} (Strategy: {self.threshold_strategy})"
        )
        return self.decision_threshold

    def get_params(self) -> Dict[str, Any]:
        """Return model hyperparameter dictionary."""
        return {
            "n_estimators": self.n_estimators,
            "max_depth": self.max_depth,
            "min_samples_split": self.min_samples_split,
            "min_samples_leaf": self.min_samples_leaf,
            "max_features": self.max_features,
            "bootstrap": self.bootstrap,
            "class_weight": self.class_weight,
            "criterion": self.criterion,
            "random_state": self.random_state,
            "n_jobs": self.n_jobs,
            "decision_threshold": self.decision_threshold,
            "threshold_strategy": self.threshold_strategy,
            "feature_count": len(self.feature_names_),
        }

    def save(self, file_path: Union[str, Path]) -> Path:
        """Serialize Random Forest model to disk using joblib."""
        if not self.is_trained or self.model is None:
            raise RuntimeError("Cannot save an unfitted RandomForestClassifierModel.")

        path = Path(file_path)
        ensure_dir(path.parent)

        payload = {
            "model_type": "random_forest",
            "model": self.model,
            "params": self.get_params(),
            "feature_names": self.feature_names_,
            "classes": self.classes_,
            "feature_importances": self.feature_importances_dict_,
            "decision_threshold": self.decision_threshold,
            "threshold_strategy": self.threshold_strategy,
        }

        joblib.dump(payload, path)
        logger.info(f"Saved Random Forest model artifact to: {path}")
        return path

    @classmethod
    def load(cls, file_path: Union[str, Path]) -> "RandomForestClassifierModel":
        """Load trained Random Forest checkpoint and restore inference state."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Random Forest artifact not found at {path}")

        payload = joblib.load(path)
        params = payload["params"]

        wrapper = cls(
            n_estimators=params["n_estimators"],
            max_depth=params["max_depth"],
            min_samples_split=params["min_samples_split"],
            min_samples_leaf=params["min_samples_leaf"],
            max_features=params["max_features"],
            bootstrap=params["bootstrap"],
            class_weight=params["class_weight"],
            criterion=params.get("criterion", "gini"),
            random_state=params["random_state"],
            n_jobs=params.get("n_jobs", -1),
            decision_threshold=payload.get("decision_threshold", 0.5),
        )

        wrapper.model = payload["model"]
        wrapper.is_trained = True
        wrapper.feature_names_ = payload.get("feature_names", [])
        wrapper.classes_ = payload.get("classes", [0, 1])
        wrapper.feature_importances_dict_ = payload.get("feature_importances", {})
        wrapper.decision_threshold = payload.get("decision_threshold", 0.5)
        wrapper.optimal_threshold_ = wrapper.decision_threshold
        wrapper.threshold_strategy = payload.get("threshold_strategy", "default_0.5")

        logger.info(
            f"Loaded RandomForestClassifierModel from {path} (features={len(wrapper.feature_names_)}, "
            f"trees={wrapper.n_estimators}, threshold={wrapper.decision_threshold:.4f})"
        )
        return wrapper
