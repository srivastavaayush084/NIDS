from datetime import datetime, timezone
from typing import Dict, Any, Optional, Literal
from pydantic import BaseModel, Field, ConfigDict

AuditStatus = Literal["SUCCESS", "FAILURE", "DENIED"]


class AuditLogDocument(BaseModel):
    """MongoDB document model for security compliance, administrative actions, and audit trails."""
    id: Optional[str] = Field(None, alias="_id")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    user_id: Optional[str] = Field(None, description="Identifier of acting user or 'system'")
    action: str = Field(..., description="Action performed, e.g., USER_LOGIN, ALERT_ACKNOWLEDGE")
    resource: str = Field(..., description="Target resource type, e.g., alerts, models, users")
    resource_id: Optional[str] = None
    ip_address: Optional[str] = None
    status: AuditStatus = "SUCCESS"
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(populate_by_name=True)
