from datetime import datetime, timezone
from typing import Optional, Literal
from pydantic import BaseModel, Field, ConfigDict

AlertStatus = Literal["new", "acknowledged", "resolved", "dismissed"]
AlertSeverity = Literal["INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"]


class AlertDocument(BaseModel):
    """MongoDB document model for security incident alerts."""
    id: Optional[str] = Field(None, alias="_id")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    detection_result_id: Optional[str] = None
    alert_type: str = Field(default="ZERO_DAY_ANOMALY", description="Classification of threat/incident")
    severity: AlertSeverity = "MEDIUM"
    title: str = Field(..., min_length=3, max_length=200)
    description: str = Field(..., max_length=1000)
    source_ip: Optional[str] = None
    destination_ip: Optional[str] = None
    anomaly_score: float = Field(default=0.0, ge=0.0, le=1.0)
    status: AlertStatus = "new"
    explanation: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(populate_by_name=True)


# Backward compatibility alias
SecurityAlert = AlertDocument
