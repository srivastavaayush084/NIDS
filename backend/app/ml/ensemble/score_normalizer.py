from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.ml.data.utils.data_utils import ensure_dir, save_metadata, load_metadata


class ScoreNormalizer:
    """
    Transforms disparate native model outputs into a unified 0–100 risk scale.

    Explicitly accounts for heterogeneous score directions and distributions:
    - Isolation Forest: Lower decision function / Higher anomaly score -> Higher Risk
    - Dense Autoencoder: Higher reconstruction MSE -> Higher Risk
    - LSTM Autoencoder: Higher sequence reconstruction MSE -> Higher Risk
    - Random Forest: Higher attack probability -> Higher Risk

    Provides multiple normalization strategies fitted strictly on validation data:
    - 'threshold_relative': Piecewise continuous scaling anchoring the model's decision threshold at 50.0.
    - 'validation_min_max': Linear bounded scaling against empirical validation reference bounds.
    - 'direct_percentage': Direct probability/score scaling where applicable.
    """

    DEFAULT_CALIBRATION: Dict[str, Dict[str, Any]] = {
        "isolation_forest": {
            "method": "threshold_relative",
            "threshold": 50.0,
            "min_val": 0.0,
            "max_val": 100.0,
            "is_raw_decision": False,
        },
        "autoencoder": {
            "method": "threshold_relative",
            "threshold": 0.05,
            "min_val": 0.0,
            "max_val": 0.50,
            "is_raw_decision": False,
        },
        "lstm_autoencoder": {
            "method": "threshold_relative",
            "threshold": 0.05,
            "min_val": 0.0,
            "max_val": 0.50,
            "is_raw_decision": False,
        },
        "random_forest": {
            "method": "threshold_relative",
            "threshold": 0.50,
            "min_val": 0.0,
            "max_val": 1.0,
            "is_raw_decision": False,
        },
    }

    def __init__(
        self,
        calibration_data: Optional[Dict[str, Dict[str, Any]]] = None,
        default_method: Optional[str] = None,
    ):
        self.calibration = calibration_data or dict(self.DEFAULT_CALIBRATION)
        self.default_method = default_method or settings.ENSEMBLE_NORMALIZATION_METHOD

    def normalize(
        self,
        model_name: str,
        raw_score: float,
        threshold: Optional[float] = None,
        method: Optional[str] = None,
    ) -> float:
        """
        Normalize a single raw score into the 0.0 - 100.0 risk scale.

        Args:
            model_name: Canonical model name ('isolation_forest', 'autoencoder', 'lstm_autoencoder', 'random_forest')
            raw_score: The raw/native score produced by the model.
            threshold: Optional threshold override.
            method: 'threshold_relative', 'validation_min_max', or 'direct_percentage'.

        Returns:
            Normalized risk score strictly clipped to [0.0, 100.0].
        """
        m_name = self._canonical_name(model_name)
        model_calib = self.calibration.get(m_name, {})
        norm_method = method or model_calib.get("method", self.default_method)
        th = threshold if threshold is not None else model_calib.get("threshold", 50.0)

        if m_name == "isolation_forest":
            return self._normalize_isolation_forest(raw_score, th, norm_method, model_calib)
        elif m_name in ("autoencoder", "lstm_autoencoder"):
            return self._normalize_reconstruction(raw_score, th, norm_method, model_calib)
        elif m_name == "random_forest":
            return self._normalize_random_forest(raw_score, th, norm_method, model_calib)
        else:
            # Generic fallback
            return float(np.clip(raw_score, 0.0, 100.0))

    def normalize_batch(
        self,
        model_name: str,
        raw_scores: Union[np.ndarray, List[float]],
        threshold: Optional[float] = None,
        method: Optional[str] = None,
    ) -> np.ndarray:
        """Normalize an array of raw scores into the [0.0, 100.0] risk scale."""
        scores = np.asarray(raw_scores, dtype=float)
        return np.array([self.normalize(model_name, s, threshold, method) for s in scores])

    def _normalize_isolation_forest(
        self,
        score: float,
        threshold: float,
        method: str,
        calib: Dict[str, Any],
    ) -> float:
        """
        Normalize Isolation Forest scores.
        Handles both raw decision function scores ([-0.5, 0.5], lower=anomalous)
        and precomputed anomaly scores ([0, 100], higher=anomalous).
        """
        # Detect if raw decision score is provided (typically in [-1.0, 1.0])
        if score <= 1.0 and score >= -1.0 and not calib.get("is_precomputed_0_100", False):
            # Raw decision function: negative is anomaly, positive is normal
            # Map [-0.5, 0.5] -> [100, 0]
            normalized = (0.5 - score) * 100.0
            return float(np.clip(normalized, 0.0, 100.0))

        if method == "threshold_relative" and threshold > 0:
            if score <= threshold:
                res = 50.0 * (score / threshold)
            else:
                remaining = max(1.0, 100.0 - threshold)
                res = 50.0 + 50.0 * ((score - threshold) / remaining)
            return float(np.clip(res, 0.0, 100.0))

        return float(np.clip(score, 0.0, 100.0))

    def _normalize_reconstruction(
        self,
        error: float,
        threshold: float,
        method: str,
        calib: Dict[str, Any],
    ) -> float:
        """
        Normalize Autoencoder and LSTM Autoencoder reconstruction MSE errors.
        Higher error corresponds to higher anomaly risk.
        """
        err = max(0.0, float(error))
        th = max(1e-6, float(threshold))

        if method == "threshold_relative":
            # Continuous piecewise mapping:
            # Sub-threshold [0, th] maps smoothly to [0.0, 50.0]
            # Supra-threshold [th, 3*th] maps to [50.0, 100.0]
            if err <= th:
                score = 50.0 * (err / th)
            else:
                upper_span = max(1e-6, 2.0 * th)
                excess_ratio = min(1.0, (err - th) / upper_span)
                score = 50.0 + 50.0 * excess_ratio
            return float(np.clip(score, 0.0, 100.0))

        elif method == "validation_min_max":
            min_v = calib.get("min_val", 0.0)
            max_v = calib.get("max_val", th * 2.0)
            span = max(1e-6, max_v - min_v)
            score = 100.0 * ((err - min_v) / span)
            return float(np.clip(score, 0.0, 100.0))

        # Direct scaling
        return float(np.clip(err * 100.0, 0.0, 100.0))

    def _normalize_random_forest(
        self,
        prob: float,
        threshold: float,
        method: str,
        calib: Dict[str, Any],
    ) -> float:
        """
        Normalize Random Forest attack probabilities [0.0, 1.0].
        Higher probability corresponds to higher anomaly risk.
        """
        p = float(np.clip(prob, 0.0, 1.0))
        th = float(np.clip(threshold, 0.01, 0.99))

        if method == "threshold_relative":
            if p <= th:
                score = 50.0 * (p / th)
            else:
                score = 50.0 + 50.0 * ((p - th) / (1.0 - th))
            return float(np.clip(score, 0.0, 100.0))

        # Direct percentage: 0.0 -> 0.0, 1.0 -> 100.0
        return float(np.clip(p * 100.0, 0.0, 100.0))

    def calibrate_from_validation(
        self,
        validation_scores: Dict[str, Union[np.ndarray, List[float]]],
        thresholds: Optional[Dict[str, float]] = None,
    ) -> None:
        """
        Calibrate reference statistics (min, max, percentiles, thresholds)
        using strictly validation data to prevent test-set data leakage.
        """
        th_dict = thresholds or {}
        for m_raw, scores in validation_scores.items():
            m_name = self._canonical_name(m_raw)
            arr = np.asarray(scores, dtype=float)
            if len(arr) == 0:
                continue

            th = th_dict.get(m_name, float(np.percentile(arr, 95.0)))
            self.calibration[m_name] = {
                "method": self.default_method,
                "threshold": float(th),
                "min_val": float(np.min(arr)),
                "max_val": float(np.max(arr)),
                "p50": float(np.percentile(arr, 50.0)),
                "p95": float(np.percentile(arr, 95.0)),
                "p99": float(np.percentile(arr, 99.0)),
                "calibrated_at": datetime.now(timezone.utc).isoformat(),
            }
        logger.info(f"Ensemble ScoreNormalizer calibrated on {len(validation_scores)} model validation splits.")

    def save_calibration(self, file_path: Union[str, Path]) -> None:
        """Serialize calibration parameters to disk."""
        p = Path(file_path)
        ensure_dir(p.parent)
        save_metadata(
            {
                "version": "1.0.0",
                "default_method": self.default_method,
                "calibration": self.calibration,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
            p,
        )
        logger.info(f"Saved ensemble calibration metadata to: {p}")

    @classmethod
    def load_calibration(cls, file_path: Union[str, Path]) -> "ScoreNormalizer":
        """Load calibration parameters from disk."""
        p = Path(file_path)
        if not p.exists():
            logger.warning(f"Calibration file not found at {p}. Using default parameters.")
            return cls()
        data = load_metadata(p)
        return cls(
            calibration_data=data.get("calibration", {}),
            default_method=data.get("default_method", "threshold_relative"),
        )

    def _canonical_name(self, name: str) -> str:
        n = name.lower().strip()
        if n in ("if", "isolation_forest", "iforest"):
            return "isolation_forest"
        if n in ("ae", "autoencoder", "dense_autoencoder"):
            return "autoencoder"
        if n in ("lstm", "lstm_autoencoder", "lstm_detector"):
            return "lstm_autoencoder"
        if n in ("rf", "random_forest", "random_forest_baseline"):
            return "random_forest"
        return n
