from typing import Dict, Any, List, Optional, Literal
from datetime import datetime, timezone
from pydantic import BaseModel, Field

EventLevel = Literal["INFO", "WARNING", "ERROR", "CRITICAL"]


class SystemEventBase(BaseModel):
    event_type: str = Field(..., description="APP_STARTUP, APP_SHUTDOWN, MODEL_LOADED, DB_CONNECTED, etc.")
    level: EventLevel = Field(default="INFO")
    component: str = Field(default="backend.system")
    message: str = Field(..., max_length=1000)
    details: Dict[str, Any] = Field(default_factory=dict)


class SystemEventCreate(SystemEventBase):
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SystemEventResponse(SystemEventBase):
    id: str
    timestamp: datetime


class SystemEventListResponse(BaseModel):
    total: int
    page: int
    limit: int
    events: List[SystemEventResponse]
