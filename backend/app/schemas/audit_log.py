from typing import Dict, Any, List, Optional, Literal
from datetime import datetime, timezone
from pydantic import BaseModel, Field

AuditStatus = Literal["SUCCESS", "FAILURE", "DENIED"]


class AuditLogBase(BaseModel):
    user_id: Optional[str] = None
    action: str = Field(..., description="Action executed")
    resource: str = Field(..., description="Target resource")
    resource_id: Optional[str] = None
    ip_address: Optional[str] = None
    status: AuditStatus = Field(default="SUCCESS")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AuditLogCreate(AuditLogBase):
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AuditLogResponse(AuditLogBase):
    id: str
    timestamp: datetime


class AuditLogListResponse(BaseModel):
    total: int
    page: int
    limit: int
    logs: List[AuditLogResponse]
