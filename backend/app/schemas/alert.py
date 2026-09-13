from typing import Dict, Any, List, Optional, Literal
from datetime import datetime, timezone
from pydantic import BaseModel, Field

AlertStatus = Literal["new", "acknowledged", "resolved", "dismissed"]
AlertSeverity = Literal["INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"]


class AlertBase(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    description: str = Field(..., max_length=1000)
    alert_type: str = Field(default="ZERO_DAY_ANOMALY")
    severity: AlertSeverity = Field(default="MEDIUM", description="INFO, LOW, MEDIUM, HIGH, CRITICAL")
    anomaly_score: float = Field(default=0.0, ge=0.0, le=1.0)
    source_ip: Optional[str] = None
    destination_ip: Optional[str] = None
    status: AlertStatus = Field(default="new", description="new, acknowledged, resolved, dismissed")
    explanation: Optional[str] = None
    detection_result_id: Optional[str] = None


class AlertCreate(AlertBase):
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AlertUpdate(BaseModel):
    status: Optional[AlertStatus] = None
    explanation: Optional[str] = None
    severity: Optional[AlertSeverity] = None


class AlertResponse(AlertBase):
    id: str
    timestamp: datetime
    created_at: datetime
    updated_at: Optional[datetime] = None


class AlertListResponse(BaseModel):
    total: int
    page: int
    limit: int
    alerts: List[AlertResponse]
