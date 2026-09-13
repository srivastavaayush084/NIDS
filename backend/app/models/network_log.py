from datetime import datetime, timezone
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict


class NetworkLogDocument(BaseModel):
    """MongoDB document model for ingested network flow logs."""
    id: Optional[str] = Field(None, alias="_id")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source_ip: Optional[str] = None
    destination_ip: Optional[str] = None
    source_port: Optional[int] = Field(None, ge=0, le=65535)
    destination_port: Optional[int] = Field(None, ge=0, le=65535)
    protocol: Optional[str] = Field(default="TCP", description="TCP, UDP, ICMP, etc.")
    packet_count: int = Field(default=1, ge=0)
    byte_count: int = Field(default=0, ge=0)
    flow_duration: float = Field(default=0.0, ge=0.0)
    features: Dict[str, Any] = Field(default_factory=dict, description="Extracted numerical & categorical ML features")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Raw packet flags, interface, source dataset")

    model_config = ConfigDict(populate_by_name=True)
