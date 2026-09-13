from typing import Any, Dict, List, Optional
from backend.app.core.config import settings
from backend.app.ml.ensemble.schemas import EnsemblePrediction
from backend.app.alerts.schemas import AlertSeverity, AlertPriority, XAIEvidence


class AlertFormatter:
    """
    Constructs factual, contextual human-readable alert titles and incident descriptions
    derived directly from Ensemble Detection Engine outputs and XAI explanations.
    """

    @staticmethod
    def format_title(
        severity: AlertSeverity,
        prediction: EnsemblePrediction,
        alert_type: str = "network_anomaly",
    ) -> str:
        """
        Generate a concise, standardized operational alert title.
        Avoids unsupported attack classification labels.
        """
        if severity == "CRITICAL":
            if prediction.agreement.agreement_ratio >= 0.75:
                return "Critical Multi-Model Anomaly Consensus Detected"
            return "Critical Zero-Day Network Anomaly Detected"
        elif severity == "HIGH":
            if prediction.agreement.models_anomalous >= 2:
                return "High-Risk Multi-Engine Network Anomaly Detected"
            return "High-Risk Network Anomaly Detected"
        elif severity == "MEDIUM":
            return "Elevated Suspicious Network Behavior Detected"
        else:
            return "Low-Risk Network Flow Divergence Noted"

    @staticmethod
    def format_description(
        severity: AlertSeverity,
        prediction: EnsemblePrediction,
        source_ip: Optional[str] = None,
        dest_ip: Optional[str] = None,
        protocol: Optional[str] = None,
        xai_evidence: Optional[XAIEvidence] = None,
        max_length: Optional[int] = None,
    ) -> str:
        """
        Generate a detailed operational description containing risk score, consensus ratio,
        participating model breakdown, flow metadata, and XAI feature attributions.
        """
        limit = max_length or settings.ALERT_MAX_DESCRIPTION_LENGTH
        parts = []

        # 1. Lead overview
        src_str = f" from {source_ip}" if source_ip else ""
        dst_str = f" targeting {dest_ip}" if dest_ip else ""
        proto_str = f" over {protocol.upper()}" if protocol else ""
        
        parts.append(
            f"Anomalous network activity was detected{src_str}{dst_str}{proto_str} "
            f"with an ensemble risk score of {prediction.risk_score:.1f}/100.0 (Severity: {severity})."
        )

        # 2. Consensus & Participating models
        models_str = ", ".join(prediction.participating_models)
        parts.append(
            f"Model consensus: {prediction.agreement.models_anomalous} of {prediction.agreement.models_available} "
            f"participating detection engines ({models_str}) flagged anomalous patterns "
            f"(consensus agreement ratio: {prediction.agreement.agreement_ratio * 100.0:.1f}%)."
        )

        # 3. Leading model scores
        top_models = []
        for m_name, c in prediction.contributions.items():
            if c.is_available:
                top_models.append(f"{m_name}: risk={c.normalized_score:.1f} (weight={c.effective_weight:.2f})")
        if top_models:
            parts.append(f"Model breakdown: {'; '.join(top_models)}.")

        # 4. Attached XAI Summary & top features if present
        if xai_evidence and xai_evidence.is_available:
            parts.append(f"Explainability Analysis: \"{xai_evidence.summary}\"")
            if xai_evidence.top_features:
                feat_strs = []
                for f in xai_evidence.top_features[:3]:
                    fname = f.get("feature_name", "feature")
                    c_val = f.get("contribution", 0.0)
                    feat_strs.append(f"{fname} ({c_val:+.4f})")
                parts.append(f"Leading anomalous feature metrics: {', '.join(feat_strs)}.")

        full_desc = " ".join(parts)
        if len(full_desc) > limit:
            full_desc = full_desc[: limit - 3] + "..."

        return full_desc
