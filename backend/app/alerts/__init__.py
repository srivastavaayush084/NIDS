"""
Security Alert Engine Package.
Orchestrates conversion of Ensemble Detection results into deduplicated, explainable,
prioritized, and auditable security alerts.
"""

from backend.app.alerts.schemas import (
    AlertStatus,
    AlertSeverity,
    AlertPriority,
    NetworkEndpoint,
    ModelEvidenceItem,
    EnsembleEvidence,
    XAIEvidence,
    DeduplicationInfo,
    AlertDocument,
    AlertEventResult,
    AlertFilterParams,
)
from backend.app.alerts.severity import map_severity_to_priority, evaluate_alert_severity
from backend.app.alerts.rules import AlertRuleEngine
from backend.app.alerts.deduplication import AlertDeduplicator
from backend.app.alerts.formatter import AlertFormatter
from backend.app.alerts.engine import AlertEngine

__all__ = [
    "AlertStatus",
    "AlertSeverity",
    "AlertPriority",
    "NetworkEndpoint",
    "ModelEvidenceItem",
    "EnsembleEvidence",
    "XAIEvidence",
    "DeduplicationInfo",
    "AlertDocument",
    "AlertEventResult",
    "AlertFilterParams",
    "map_severity_to_priority",
    "evaluate_alert_severity",
    "AlertRuleEngine",
    "AlertDeduplicator",
    "AlertFormatter",
    "AlertEngine",
]
