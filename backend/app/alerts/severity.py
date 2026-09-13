from typing import Dict, Any
from backend.app.ml.ensemble.severity import SeverityClassifier, classify_severity
from backend.app.alerts.schemas import AlertSeverity, AlertPriority

# Mapping of threat severity to incident response priority
SEVERITY_TO_PRIORITY_MAP: Dict[AlertSeverity, AlertPriority] = {
    "LOW": "LOW",
    "MEDIUM": "MEDIUM",
    "HIGH": "HIGH",
    "CRITICAL": "URGENT",
}


def map_severity_to_priority(severity: AlertSeverity) -> AlertPriority:
    """
    Map operational threat severity tier to security triage incident priority.
    """
    return SEVERITY_TO_PRIORITY_MAP.get(severity, "MEDIUM")


def evaluate_alert_severity(risk_score: float) -> AlertSeverity:
    """
    Classify normalized risk score (0.0 to 100.0) into standardized alert severity tier.
    Reuses centralized Phase 9 ensemble severity thresholds.
    """
    return classify_severity(risk_score)  # type: ignore
