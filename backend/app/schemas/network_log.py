from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class NetworkLogBase(BaseModel):
    source_ip: Optional[str] = Field(None, description="Source IPv4/IPv6 address")
    destination_ip: Optional[str] = Field(None, description="Destination IPv4/IPv6 address")
    source_port: Optional[int] = Field(None, ge=0, le=65535, description="Source port")
    destination_port: Optional[int] = Field(None, ge=0, le=65535, description="Destination port")
    protocol: Optional[str] = Field(default="TCP", description="Transport layer protocol")
    packet_count: int = Field(default=1, ge=0)
    byte_count: int = Field(default=0, ge=0)
    flow_duration: float = Field(default=0.0, ge=0.0)
    features: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class NetworkLogCreate(NetworkLogBase):
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class NetworkLogResponse(NetworkLogBase):
    id: str
    timestamp: datetime


class NetworkLogBatchCreate(BaseModel):
    logs: List[NetworkLogCreate]
    source: str = Field(default="ingestion_pipeline")


class NetworkLogFilter(BaseModel):
    source_ip: Optional[str] = None
    destination_ip: Optional[str] = None
    protocol: Optional[str] = None
    limit: int = Field(default=50, ge=1, le=1000)
    skip: int = Field(default=0, ge=0)
