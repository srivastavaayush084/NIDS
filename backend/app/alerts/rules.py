from typing import Dict, Optional, Tuple
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.ml.ensemble.schemas import EnsemblePrediction
from backend.app.alerts.schemas import AlertSeverity
from backend.app.alerts.severity import evaluate_alert_severity


class AlertRuleEngine:
    """
    Evaluates whether an incoming EnsemblePrediction warrants security alert generation
    based on externalized configuration, risk thresholds, severity filters, and consensus metrics.
    """

    def __init__(
        self,
        alerts_enabled: Optional[bool] = None,
        min_risk_score: Optional[float] = None,
        low_enabled: Optional[bool] = None,
        medium_enabled: Optional[bool] = None,
        high_enabled: Optional[bool] = None,
        critical_enabled: Optional[bool] = None,
        min_agreement_ratio: Optional[float] = None,
        require_anomaly_flag: bool = True,
    ):
        self.alerts_enabled = alerts_enabled if alerts_enabled is not None else settings.ALERTS_ENABLED
        self.min_risk_score = min_risk_score if min_risk_score is not None else settings.ALERT_MIN_RISK_SCORE
        self.enabled_severities: Dict[AlertSeverity, bool] = {
            "LOW": low_enabled if low_enabled is not None else settings.ALERT_LOW_ENABLED,
            "MEDIUM": medium_enabled if medium_enabled is not None else settings.ALERT_MEDIUM_ENABLED,
            "HIGH": high_enabled if high_enabled is not None else settings.ALERT_HIGH_ENABLED,
            "CRITICAL": critical_enabled if critical_enabled is not None else settings.ALERT_CRITICAL_ENABLED,
        }
        self.min_agreement_ratio = min_agreement_ratio
        self.require_anomaly_flag = require_anomaly_flag

    def should_generate_alert(
        self,
        prediction: EnsemblePrediction,
    ) -> Tuple[bool, str, AlertSeverity]:
        """
        Evaluate alert rules against an ensemble prediction.
        
        Returns:
            Tuple of (should_alert: bool, reason: str, severity: AlertSeverity)
        """
        severity = evaluate_alert_severity(prediction.risk_score)

        if not self.alerts_enabled:
            return False, "alerts_disabled_globally", severity

        # Check if severity tier is enabled in configuration
        if not self.enabled_severities.get(severity, False):
            return False, f"severity_{severity.lower()}_disabled", severity

        # Check minimum risk score threshold
        if prediction.risk_score < self.min_risk_score:
            return False, "risk_score_below_minimum_threshold", severity

        # Check anomaly flag requirement
        if self.require_anomaly_flag and not prediction.is_anomaly:
            return False, "ensemble_prediction_is_normal", severity

        # Check optional minimum model agreement ratio
        if self.min_agreement_ratio is not None:
            if prediction.agreement.agreement_ratio < self.min_agreement_ratio:
                return False, "model_agreement_below_required_threshold", severity

        return True, "alert_criteria_satisfied", severity
