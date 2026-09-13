from typing import Dict, Any, List


class DetectionExplainer:
    """Generates human-understandable explanations for zero-day and anomaly detections."""

    @staticmethod
    def explain_anomaly(
        risk_score: float,
        model_predictions: Dict[str, Any],
        top_features: List[Dict[str, Any]] = None
    ) -> str:
        """Formulate a contextual narrative explanation describing why traffic was flagged."""
        if risk_score < 0.30:
            return "Traffic behavior is consistent with normal baseline patterns."

        consensus_count = sum(1 for m in model_predictions.values() if m.get("is_anomaly", False))
        total_models = len(model_predictions) if model_predictions else 1

        parts = [
            f"Traffic flagged with risk score {risk_score:.2f} ({consensus_count}/{total_models} models detected anomalous deviation)."
        ]

        if top_features:
            feature_names = [f.get("feature_name", "") for f in top_features[:3]]
            parts.append(f"Top deviations observed in metrics: {', '.join(feature_names)}.")

        if risk_score >= 0.85:
            parts.append("High likelihood of novel zero-day payload or uncharacterized lateral communication pattern.")

        return " ".join(parts)
