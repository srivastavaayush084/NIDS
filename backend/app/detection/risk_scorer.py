from typing import Dict, Any
from backend.app.core.config import settings


class RiskScorer:
    """Calculates unified risk score and classifies severity based on multi-model signals."""

    @staticmethod
    def calculate_risk_score(model_scores: Dict[str, float], weights: Dict[str, float] = None) -> float:
        """Combine raw model scores into a normalized risk score between 0.0 and 1.0."""
        if not model_scores:
            return 0.0

        if weights is None:
            # Default ensemble weighting
            weights = {
                "isolation_forest": 0.30,
                "autoencoder": 0.35,
                "lstm": 0.25,
                "random_forest": 0.10
            }

        total_weight = 0.0
        weighted_sum = 0.0

        for model, score in model_scores.items():
            w = weights.get(model, 0.1)
            weighted_sum += max(0.0, min(1.0, score)) * w
            total_weight += w

        if total_weight == 0:
            return 0.0

        return round(weighted_sum / total_weight, 4)

    @staticmethod
    def determine_severity(risk_score: float) -> str:
        """Determine severity level from calculated risk score."""
        if risk_score >= settings.CRITICAL_RISK_THRESHOLD:
            return "CRITICAL"
        elif risk_score >= settings.HIGH_RISK_THRESHOLD:
            return "HIGH"
        elif risk_score >= settings.DEFAULT_ANOMALY_THRESHOLD:
            return "MEDIUM"
        elif risk_score >= 0.30:
            return "LOW"
        return "INFO"
