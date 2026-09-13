import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field, ConfigDict

AlertStatus = Literal["OPEN", "ACKNOWLEDGED", "RESOLVED", "DISMISSED"]
AlertSeverity = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
AlertPriority = Literal["LOW", "MEDIUM", "HIGH", "URGENT"]


class NetworkEndpoint(BaseModel):
    """Network connection endpoint (IP and Port)."""
    ip: Optional[str] = Field(None, description="IPv4 or IPv6 address")
    port: Optional[int] = Field(None, ge=0, le=65535, description="Port number")


class ModelEvidenceItem(BaseModel):
    """Detailed evidence from an individual constituent detection model."""
    model_name: str
    prediction: str = Field(..., description="'normal' or 'attack'")
    is_anomaly: bool
    native_score: float
    normalized_score: float
    configured_weight: float
    effective_weight: float
    weighted_contribution: float
    decision_threshold: float
    latency_ms: float = 0.0
    is_available: bool = True
    error: Optional[str] = None


class EnsembleEvidence(BaseModel):
    """Summary evidence and consensus metrics from the Ensemble Detection Engine."""
    risk_score: float = Field(..., ge=0.0, le=100.0)
    decision_threshold: float = 50.0
    agreement_ratio: float = Field(..., ge=0.0, le=1.0)
    consensus_prediction: str
    models_total: int
    models_available: int
    models_anomalous: int
    models_normal: int
    participating_models: List[str] = Field(default_factory=list)
    missing_models: List[str] = Field(default_factory=list)
    reliability_score: float = Field(..., ge=0.0, le=1.0)


class XAIEvidence(BaseModel):
    """Attached Explainable AI (XAI) feature and timestep attributions."""
    explanation_id: Optional[str] = None
    method: str = "ensemble_risk_attribution"
    summary: str
    top_features: List[Dict[str, Any]] = Field(default_factory=list)
    peak_timestep: Optional[str] = None
    is_available: bool = True
    error: Optional[str] = None


class DeduplicationInfo(BaseModel):
    """Alert deduplication and recurrence tracking metadata."""
    fingerprint: str = Field(..., description="Deterministic SHA-256 event fingerprint")
    occurrence_count: int = Field(default=1, ge=1, description="Number of recurring detection events")
    first_seen: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_seen: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AlertDocument(BaseModel):
    """
    Standardized MongoDB Security Alert Document.
    Represents an operational incident generated from high-risk ensemble detections.
    """
    id: Optional[str] = Field(None, alias="_id")
    alert_id: str = Field(default_factory=lambda: f"alt-{uuid.uuid4().hex[:12]}")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    detection_result_id: Optional[str] = None
    alert_type: str = Field(default="network_anomaly", description="Type of alert: network_anomaly, suspicious_activity, high_risk_detection")
    severity: AlertSeverity = "HIGH"
    priority: AlertPriority = "HIGH"
    title: str = Field(..., min_length=3, max_length=250)
    description: str = Field(..., max_length=1500)
    status: AlertStatus = "OPEN"
    risk_score: float = Field(..., ge=0.0, le=100.0)
    threshold: float = Field(default=50.0)
    source: NetworkEndpoint = Field(default_factory=NetworkEndpoint)
    destination: NetworkEndpoint = Field(default_factory=NetworkEndpoint)
    protocol: Optional[str] = "TCP"
    model_evidence: List[ModelEvidenceItem] = Field(default_factory=list)
    ensemble: Optional[EnsembleEvidence] = None
    explanation: Optional[XAIEvidence] = None
    deduplication: DeduplicationInfo
    assigned_to: Optional[str] = None
    resolution_note: Optional[str] = None
    dismissal_reason: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(populate_by_name=True)

    def to_summary_dict(self) -> Dict[str, Any]:
        """Compact summary dictionary for high-level logging and dashboard telemetry."""
        return {
            "alert_id": self.alert_id,
            "title": self.title,
            "severity": self.severity,
            "priority": self.priority,
            "status": self.status,
            "risk_score": round(self.risk_score, 2),
            "source_ip": self.source.ip,
            "destination_ip": self.destination.ip,
            "occurrence_count": self.deduplication.occurrence_count,
            "xai_attached": bool(self.explanation and self.explanation.is_available),
            "created_at": self.created_at.isoformat(),
        }


class AlertEventResult(BaseModel):
    """
    Standard response from the Alert Engine indicating alert generation outcome.
    """
    alert_created: bool
    alert_id: Optional[str] = None
    deduplicated: bool = False
    severity: Optional[AlertSeverity] = None
    priority: Optional[AlertPriority] = None
    risk_score: Optional[float] = None
    status: Optional[AlertStatus] = None
    fingerprint: Optional[str] = None
    occurrence_count: int = 0
    xai_available: bool = False
    reason: Optional[str] = None
    alert: Optional[AlertDocument] = None


class AlertFilterParams(BaseModel):
    """Parameters for searching and filtering security alerts."""
    severity: Optional[AlertSeverity] = None
    status: Optional[AlertStatus] = None
    alert_type: Optional[str] = None
    source_ip: Optional[str] = None
    destination_ip: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    min_risk_score: Optional[float] = None
    fingerprint: Optional[str] = None
    limit: int = Field(default=50, ge=1, le=500)
    skip: int = Field(default=0, ge=0)
    sort_by: str = "created_at"
    sort_desc: bool = True
