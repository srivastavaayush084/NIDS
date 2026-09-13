from typing import Any, Dict, List, Optional, Union
import numpy as np
from backend.app.core.config import settings


class SeverityClassifier:
    """
    Classifies continuous normalized risk scores (0.0 - 100.0) into discrete
    operational severity tiers: LOW, MEDIUM, HIGH, CRITICAL.

    Guarantees:
    - Complete, contiguous coverage of the [0.0, 100.0] range.
    - Zero overlapping intervals and zero coverage gaps.
    - Externalized, configurable thresholds via application settings.
    """

    SEVERITY_COLORS = {
        "LOW": "#10B981",       # Emerald Green
        "MEDIUM": "#F59E0B",    # Amber
        "HIGH": "#F97316",      # Orange
        "CRITICAL": "#EF4444",  # Crimson Red
    }

    SEVERITY_DESCRIPTIONS = {
        "LOW": "Routine / Nominal network activity. Minimal anomaly indicators present.",
        "MEDIUM": "Elevated pattern divergence detected. Potential policy violation or unusual benign flow.",
        "HIGH": "Strong anomalous signatures identified across multiple detection models. Investigation recommended.",
        "CRITICAL": "Severe multi-model anomaly consensus or confirmed attack pattern. Immediate threat mitigation required.",
    }

    def __init__(
        self,
        low_max: Optional[float] = None,
        medium_max: Optional[float] = None,
        high_max: Optional[float] = None,
        critical_min: Optional[float] = None,
    ):
        self.low_max = low_max if low_max is not None else settings.ENSEMBLE_SEVERITY_LOW_MAX
        self.medium_max = medium_max if medium_max is not None else settings.ENSEMBLE_SEVERITY_MEDIUM_MAX
        self.high_max = high_max if high_max is not None else settings.ENSEMBLE_SEVERITY_HIGH_MAX
        self.critical_min = critical_min if critical_min is not None else settings.ENSEMBLE_SEVERITY_CRITICAL_MIN

        # Validate range continuity
        if not (0.0 <= self.low_max < self.medium_max < self.high_max <= 100.0):
            raise ValueError(
                f"Invalid severity thresholds: low_max={self.low_max}, medium_max={self.medium_max}, "
                f"high_max={self.high_max}. Must satisfy 0 <= low < med < high <= 100."
            )

    def classify(self, risk_score: float) -> str:
        """
        Classify a continuous risk score (0.0 - 100.0) into a severity level.

        Args:
            risk_score: Normalized risk score.

        Returns:
            'LOW', 'MEDIUM', 'HIGH', or 'CRITICAL'.
        """
        s = float(np.clip(risk_score, 0.0, 100.0))
        if s <= self.low_max:
            return "LOW"
        elif s <= self.medium_max:
            return "MEDIUM"
        elif s < self.critical_min:
            return "HIGH"
        else:
            return "CRITICAL"

    def classify_batch(self, risk_scores: Union[np.ndarray, List[float]]) -> List[str]:
        """Classify a list/array of risk scores into severity tiers."""
        return [self.classify(s) for s in risk_scores]

    def get_metadata(self, severity: str) -> Dict[str, Any]:
        """Retrieve color codes and security descriptions for a severity tier."""
        sev = severity.upper().strip()
        return {
            "tier": sev,
            "color": self.SEVERITY_COLORS.get(sev, "#6B7280"),
            "description": self.SEVERITY_DESCRIPTIONS.get(sev, "Unknown severity level."),
            "threshold_range": self._get_tier_range(sev),
        }

    def _get_tier_range(self, severity: str) -> Dict[str, float]:
        if severity == "LOW":
            return {"min": 0.0, "max": self.low_max}
        elif severity == "MEDIUM":
            return {"min": self.low_max, "max": self.medium_max}
        elif severity == "HIGH":
            return {"min": self.medium_max, "max": self.critical_min}
        else:
            return {"min": self.critical_min, "max": 100.0}


_default_severity_classifier = SeverityClassifier()


def classify_severity(risk_score: float) -> str:
    """Convenience function to classify continuous risk score into severity tier."""
    return _default_severity_classifier.classify(risk_score)

