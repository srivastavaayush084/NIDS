import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class EventIngestRequest(BaseModel):
    """
    Validated network event ingestion payload model.
    Accepts standardized network flow headers alongside optional raw/engineered feature attributes.
    """
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source_ip: Optional[str] = Field(None, description="Source IP address")
    destination_ip: Optional[str] = Field(None, description="Destination IP address")
    source_port: Optional[int] = Field(None, ge=0, le=65535, description="Source port number")
    destination_port: Optional[int] = Field(None, ge=0, le=65535, description="Destination port number")
    protocol: Optional[str] = Field(default="TCP", description="Transport protocol (e.g., TCP, UDP, ICMP)")
    packet_count: Optional[int] = Field(default=1, ge=0, description="Total packets in flow")
    byte_count: Optional[int] = Field(default=0, ge=0, description="Total bytes in flow")
    duration: Optional[float] = Field(default=0.0, ge=0.0, description="Flow duration in seconds")
    dataset_name: Optional[str] = Field(default="synthetic", description="Associated dataset or telemetry schema")
    features: Dict[str, Any] = Field(default_factory=dict, description="Domain/engineered feature dictionary (e.g., src_bytes, dst_bytes, count, etc.)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Sensor/ingestion source metadata")


class EventIngestResponse(BaseModel):
    """Event ingestion confirmation response."""
    event_id: str
    timestamp: datetime
    status: str = "stored"
    dataset_name: str = "synthetic"
    source_ip: Optional[str] = None
    destination_ip: Optional[str] = None


class BatchEventIngestRequest(BaseModel):
    """Batch network event ingestion payload."""
    events: List[EventIngestRequest] = Field(..., min_length=1, max_length=500)
    source: Optional[str] = Field(default="api_ingestion", description="Batch source origin identifier")


class BatchEventIngestResponse(BaseModel):
    """Batch ingestion result summary."""
    total: int
    stored: int
    failed: int
    event_ids: List[str] = Field(default_factory=list)
    errors: List[Dict[str, Any]] = Field(default_factory=list)
