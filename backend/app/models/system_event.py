from datetime import datetime, timezone
from typing import Dict, Any, Optional, Literal
from pydantic import BaseModel, Field, ConfigDict

EventLevel = Literal["INFO", "WARNING", "ERROR", "CRITICAL"]


class SystemEventDocument(BaseModel):
    """MongoDB document model for application lifecycle and operational system events."""
    id: Optional[str] = Field(None, alias="_id")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    event_type: str = Field(..., description="APP_STARTUP, APP_SHUTDOWN, MODEL_LOADED, DB_CONNECTED, etc.")
    level: EventLevel = "INFO"
    component: str = Field(default="backend.system", description="Subsystem originating the event")
    message: str = Field(..., max_length=1000)
    details: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(populate_by_name=True)
