import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.ml.ensemble.schemas import EnsemblePrediction
from backend.app.ml.explainability.schemas import EnsembleExplanation, ModelExplanation
from backend.app.alerts.schemas import (
    AlertDocument,
    AlertSeverity,
    AlertPriority,
    NetworkEndpoint,
    ModelEvidenceItem,
    EnsembleEvidence,
    XAIEvidence,
    DeduplicationInfo,
)
from backend.app.alerts.rules import AlertRuleEngine
from backend.app.alerts.severity import map_severity_to_priority
from backend.app.alerts.deduplication import AlertDeduplicator
from backend.app.alerts.formatter import AlertFormatter


class AlertEngine:
    """
    Production-grade Security Alert Engine.
    Orchestrates the conversion of Ensemble Detection Engine outputs into
    auditable, deduplicated, and explainable security incident alert documents.
    """

    def __init__(
        self,
        rule_engine: Optional[AlertRuleEngine] = None,
        deduplicator: Optional[AlertDeduplicator] = None,
        formatter: Optional[AlertFormatter] = None,
    ):
        self.rule_engine = rule_engine or AlertRuleEngine()
        self.deduplicator = deduplicator or AlertDeduplicator()
        self.formatter = formatter or AlertFormatter()

    def evaluate_and_build_alert(
        self,
        prediction: EnsemblePrediction,
        flow_context: Optional[Dict[str, Any]] = None,
        explanation: Optional[Union[EnsembleExplanation, ModelExplanation]] = None,
        detection_result_id: Optional[str] = None,
    ) -> Tuple[bool, Optional[AlertDocument], str, AlertSeverity, str]:
        """
        Evaluate ensemble detection result and construct a fully-populated AlertDocument if criteria are met.
        
        Returns:
            Tuple of (should_alert: bool, alert_doc: Optional[AlertDocument], reason: str, severity: AlertSeverity, fingerprint: str)
        """
        ctx = flow_context or {}
        should_alert, reason, severity = self.rule_engine.should_generate_alert(prediction)

        # Extract flow network endpoints
        src_ip = ctx.get("source_ip") or ctx.get("src_ip")
        src_port = ctx.get("source_port") or ctx.get("src_port")
        dst_ip = ctx.get("destination_ip") or ctx.get("dst_ip")
        dst_port = ctx.get("destination_port") or ctx.get("dst_port")
        protocol = ctx.get("protocol", "TCP")
        alert_type = ctx.get("alert_type", "network_anomaly")

        fingerprint = self.deduplicator.generate_fingerprint(
            source_ip=src_ip,
            destination_ip=dst_ip,
            source_port=src_port,
            destination_port=dst_port,
            protocol=protocol,
            alert_type=alert_type,
        )

        if not should_alert:
            logger.debug(f"Alert generation suppressed for score={prediction.risk_score:.2f}: {reason}")
            return False, None, reason, severity, fingerprint

        priority = map_severity_to_priority(severity)
        now = datetime.now(timezone.utc)

        # 1. Build Model Evidence
        model_evidence: List[ModelEvidenceItem] = []
        for m_name, c in prediction.contributions.items():
            model_evidence.append(
                ModelEvidenceItem(
                    model_name=m_name,
                    prediction=c.prediction,
                    is_anomaly=c.is_anomaly,
                    native_score=round(c.native_score, 4),
                    normalized_score=round(c.normalized_score, 2),
                    configured_weight=round(c.configured_weight, 4),
                    effective_weight=round(c.effective_weight, 4),
                    weighted_contribution=round(c.effective_weight * c.normalized_score, 2),
                    decision_threshold=round(c.decision_threshold, 4),
                    latency_ms=round(c.latency_ms, 3),
                    is_available=c.is_available,
                    error=c.error,
                )
            )

        # 2. Build Ensemble Evidence
        ensemble_evidence = EnsembleEvidence(
            risk_score=round(prediction.risk_score, 2),
            decision_threshold=prediction.decision_threshold,
            agreement_ratio=round(prediction.agreement.agreement_ratio, 4),
            consensus_prediction=prediction.agreement.consensus_prediction,
            models_total=prediction.agreement.models_total,
            models_available=prediction.agreement.models_available,
            models_anomalous=prediction.agreement.models_anomalous,
            models_normal=prediction.agreement.models_normal,
            participating_models=prediction.participating_models,
            missing_models=prediction.missing_models,
            reliability_score=round(prediction.reliability_score, 3),
        )

        # 3. Format XAI Evidence if available
        xai_evidence: Optional[XAIEvidence] = None
        if explanation is not None:
            try:
                top_feats = []
                if isinstance(explanation, EnsembleExplanation):
                    for fc in explanation.fused_feature_contributions[:5]:
                        top_feats.append(fc.model_dump())
                elif isinstance(explanation, ModelExplanation):
                    for fc in explanation.feature_contributions[:5]:
                        top_feats.append(fc.model_dump())

                peak_t = None
                if isinstance(explanation, ModelExplanation) and explanation.timestep_contributions:
                    peak_t = explanation.timestep_contributions[0].timestep_label

                xai_evidence = XAIEvidence(
                    explanation_id=explanation.explanation_id,
                    method=explanation.model_dump().get("explanation_method", "ensemble_risk_attribution"),
                    summary=explanation.summary,
                    top_features=top_feats,
                    peak_timestep=peak_t,
                    is_available=True,
                )
            except Exception as e:
                logger.warning(f"Error extracting XAI evidence for alert: {e}")
                xai_evidence = XAIEvidence(
                    method="unavailable",
                    summary="Explanation extraction encountered an issue.",
                    is_available=False,
                    error=str(e),
                )

        # 4. Format Title & Description
        title = self.formatter.format_title(severity, prediction, alert_type)
        description = self.formatter.format_description(
            severity=severity,
            prediction=prediction,
            source_ip=src_ip,
            dest_ip=dst_ip,
            protocol=protocol,
            xai_evidence=xai_evidence,
        )

        # 5. Assemble Alert Document
        alert_doc = AlertDocument(
            alert_id=f"alt-{uuid.uuid4().hex[:12]}",
            timestamp=now,
            detection_result_id=detection_result_id or ctx.get("detection_result_id"),
            alert_type=alert_type,
            severity=severity,
            priority=priority,
            title=title,
            description=description,
            status="OPEN",
            risk_score=round(prediction.risk_score, 2),
            threshold=prediction.decision_threshold,
            source=NetworkEndpoint(ip=src_ip, port=int(src_port) if src_port is not None and str(src_port).isdigit() else None),
            destination=NetworkEndpoint(ip=dst_ip, port=int(dst_port) if dst_port is not None and str(dst_port).isdigit() else None),
            protocol=str(protocol).upper() if protocol else "TCP",
            model_evidence=model_evidence,
            ensemble=ensemble_evidence,
            explanation=xai_evidence,
            deduplication=DeduplicationInfo(
                fingerprint=fingerprint,
                occurrence_count=1,
                first_seen=now,
                last_seen=now,
            ),
            metadata=ctx.get("metadata", {}),
            created_at=now,
            updated_at=now,
        )

        logger.info(f"Constructed Security Alert [{severity}|{priority}] '{title}' (Fingerprint: {fingerprint[:8]}...)")
        return True, alert_doc, "alert_created", severity, fingerprint
