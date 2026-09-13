from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class NetworkPacketFeature(BaseModel):
    """Network flow/packet feature representation."""
    src_ip: Optional[str] = Field(None, description="Source IP address")
    dst_ip: Optional[str] = Field(None, description="Destination IP address")
    src_port: Optional[int] = Field(None, ge=0, le=65535, description="Source Port (0-65535)")
    dst_port: Optional[int] = Field(None, ge=0, le=65535, description="Destination Port (0-65535)")
    protocol: Optional[str] = Field(None, description="Transport Protocol (TCP/UDP/ICMP)")
    duration: Optional[float] = Field(0.0, ge=0.0, description="Flow duration in seconds")
    src_bytes: Optional[int] = Field(0, ge=0, description="Bytes sent from source to destination")
    dst_bytes: Optional[int] = Field(0, ge=0, description="Bytes sent from destination to source")
    packet_count: Optional[int] = Field(0, ge=0, description="Total packet count")
    raw_features: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Raw dataset feature map")


class BatchTrafficIngestRequest(BaseModel):
    records: List[NetworkPacketFeature] = Field(..., min_length=1, max_length=500, description="Batch records (max 500)")
    source: str = Field(default="live_stream", description="Source identifier (e.g., csv_upload, pcap, sim_stream)")


class TrafficIngestResponse(BaseModel):
    status: str
    message: str
    processed_count: int
    ingested_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
