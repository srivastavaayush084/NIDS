from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class DatabaseTestResponse(BaseModel):
    """Secure database connectivity test response (no credentials or URI leaked)."""
    status: str = Field(..., description="connected, disconnected, error")
    database_name: str = Field(..., description="Target database name")
    connected: bool
    latency_ms: Optional[float] = None
    collections: List[str] = Field(default_factory=list)
    collection_counts: Dict[str, int] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    message: str
