import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union
import numpy as np
import pandas as pd

from backend.app.core.logging import logger
from backend.app.ml.explainability.schemas import ModelExplanation


class BaseExplainer(ABC):
    """
    Abstract Base Class for all Model Explainers.
    Standardizes inference invocation, explanation computation, latency tracking,
    and schema-compliant output generation.
    """

    def __init__(
        self,
        model_name: str,
        explanation_method: str,
        dataset_name: str = "generic",
        feature_names: Optional[List[str]] = None,
        top_k: int = 10,
    ):
        self.model_name = model_name
        self.explanation_method = explanation_method
        self.dataset_name = dataset_name
        self.feature_names: List[str] = list(feature_names) if feature_names else []
        self.top_k = top_k
        self.is_initialized: bool = False

    def _ensure_2d_numpy(self, X: Union[np.ndarray, pd.DataFrame, pd.Series, Dict[str, Any], List[Any]]) -> np.ndarray:
        """Convert input data sample to 2D numpy array."""
        if isinstance(X, dict):
            if not self.feature_names:
                self.feature_names = list(X.keys())
            vals = [X.get(k, 0.0) for k in self.feature_names]
            arr = np.array(vals, dtype=np.float32).reshape(1, -1)
        elif isinstance(X, pd.Series):
            if not self.feature_names:
                self.feature_names = list(X.index)
            arr = X.to_numpy(dtype=np.float32).reshape(1, -1)
        elif isinstance(X, pd.DataFrame):
            if not self.feature_names:
                self.feature_names = list(X.columns)
            arr = X.to_numpy(dtype=np.float32)
        elif isinstance(X, np.ndarray):
            arr = X.astype(np.float32)
            if arr.ndim == 1:
                arr = arr.reshape(1, -1)
        elif isinstance(X, (list, tuple)):
            arr = np.array(X, dtype=np.float32)
            if arr.ndim == 1:
                arr = arr.reshape(1, -1)
        else:
            raise TypeError(f"Unsupported input type for explanation: {type(X)}")

        if np.isnan(arr).any() or np.isinf(arr).any():
            arr = np.nan_to_num(arr, nan=0.0, posinf=1e5, neginf=-1e5)

        return arr

    @abstractmethod
    def explain_instance(
        self,
        X_sample: Union[np.ndarray, pd.DataFrame, pd.Series, Dict[str, Any]],
        top_k: Optional[int] = None,
        **kwargs: Any,
    ) -> ModelExplanation:
        """
        Generate a detailed explanation for a single network flow record.
        """
        pass

    def explain_batch(
        self,
        X_batch: Union[np.ndarray, pd.DataFrame],
        top_k: Optional[int] = None,
        max_samples: Optional[int] = None,
        **kwargs: Any,
    ) -> List[ModelExplanation]:
        """
        Generate explanations across a batch of network flow samples.
        """
        X_arr = self._ensure_2d_numpy(X_batch)
        if max_samples is not None and max_samples > 0:
            X_arr = X_arr[:max_samples]

        explanations: List[ModelExplanation] = []
        for i in range(len(X_arr)):
            sample = X_arr[i : i + 1]
            exp = self.explain_instance(sample, top_k=top_k, **kwargs)
            explanations.append(exp)

        return explanations
