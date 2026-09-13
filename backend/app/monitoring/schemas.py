import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field, field_validator


class PacketInfo(BaseModel):
    """Normalized structured packet header metadata."""
    timestamp: float = Field(..., description="Epoch timestamp of packet arrival")
    src_ip: str = Field(..., description="Source IPv4/IPv6 address")
    dst_ip: str = Field(..., description="Destination IPv4/IPv6 address")
    src_port: Optional[int] = Field(None, ge=0, le=65535, description="Source port number")
    dst_port: Optional[int] = Field(None, ge=0, le=65535, description="Destination port number")
    protocol: str = Field(..., description="Transport layer protocol: TCP, UDP, ICMP, OTHER")
    length: int = Field(..., ge=0, description="Packet total length in bytes")
    flags: Dict[str, bool] = Field(default_factory=dict, description="TCP control flags (SYN, ACK, FIN, RST, PSH, URG)")
    ttl: Optional[int] = Field(None, ge=0, le=255, description="Time to Live / Hop limit")
    payload_size: int = Field(default=0, ge=0, description="Transport layer payload length in bytes")


class FlowRecord(BaseModel):
    """Bidirectional aggregated network flow descriptor."""
    flow_id: str = Field(default_factory=lambda: f"flow-{uuid.uuid4().hex[:12]}")
    src_ip: str
    dst_ip: str
    src_port: Optional[int] = None
    dst_port: Optional[int] = None
    protocol: str = "TCP"
    start_time: float
    last_time: float
    duration: float = 0.0
    fwd_packets: int = 0
    bwd_packets: int = 0
    total_packets: int = 0
    fwd_bytes: int = 0
    bwd_bytes: int = 0
    total_bytes: int = 0
    fwd_flag_counts: Dict[str, int] = Field(default_factory=dict)
    bwd_flag_counts: Dict[str, int] = Field(default_factory=dict)
    tcp_state: str = "ESTABLISHED"
    service: str = "other"
    is_closed: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ModelCompatibilityReport(BaseModel):
    """Model feature compatibility evaluation report."""
    model_name: str
    compatible: bool
    available_features: int
    total_required_features: int
    missing_features: List[str] = Field(default_factory=list)
    explanation: str


class MonitoringStartRequest(BaseModel):
    """Request payload to initiate live or PCAP network monitoring."""
    source: Literal["live", "pcap"] = Field(..., description="Capture source: 'live' network interface or 'pcap' file replay")
    interface: Optional[str] = Field(None, max_length=200, description="Network interface name for live capture (e.g., eth0, Wi-Fi)")
    file: Optional[str] = Field(None, max_length=500, description="Path to PCAP/PCAPNG file for replay")
    filter: Optional[str] = Field(default="tcp or udp", max_length=200, description="BPF packet capture filter expression")
    max_packets: Optional[int] = Field(default=100000, ge=1, le=1000000, description="Maximum packets to process before stopping")
    batch_size: Optional[int] = Field(default=50, ge=1, le=500, description="Batch size for pipeline ML detection")
    replay_speed: Optional[float] = Field(default=0.0, ge=0.0, le=100.0, description="Replay pacing: 0.0 = max speed, 1.0 = real-time, 2.0 = 2x speed")
    dataset_name: Optional[str] = Field(default="synthetic", max_length=50, description="Target feature pipeline and dataset mapping")
    generate_xai: Optional[bool] = Field(default=True, description="Whether to compute XAI attributions on high-risk detections")

    @field_validator("file")
    @classmethod
    def validate_file_path(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            clean = v.strip()
            if "\x00" in clean:
                raise ValueError("Invalid file path: Null bytes are not permitted.")
            ext = "." + clean.rsplit(".", 1)[-1].lower() if "." in clean else ""
            if ext not in [".pcap", ".pcapng", ".cap"]:
                raise ValueError(f"Invalid file extension '{ext}'. Only .pcap, .pcapng, and .cap files are permitted.")
            return clean
        return v


class MonitoringStopResponse(BaseModel):
    """Response returned upon stopping monitoring session."""
    status: str = "stopped"
    message: str
    stopped_at: datetime
    summary: Dict[str, Any] = Field(default_factory=dict)


class InterfaceInfo(BaseModel):
    """Network adapter metadata descriptor."""
    name: str = Field(..., description="Interface identifier or name (e.g., Wi-Fi, Ethernet)")
    description: str = Field(default="", description="Human-readable device description")
    ip: Optional[str] = Field(default="", description="Configured IPv4 address")
    guid: Optional[str] = Field(default=None, description="System device GUID")
    is_loopback: bool = Field(default=False, description="Whether interface is a loopback adapter")
    is_default: bool = Field(default=False, description="Whether interface is the recommended default")


class InterfaceListResponse(BaseModel):
    """List of detected host network capture interfaces."""
    interfaces: List[InterfaceInfo] = Field(default_factory=list)
    driver_available: bool = True
    driver_message: str = "Live capture driver and interfaces are accessible."
    count: int = 0


class MonitoringStatusResponse(BaseModel):
    """Real-time monitoring telemetry, throughput metrics, and pipeline health."""
    running: bool
    active: bool = False
    status: str = "STOPPED"  # Explicit lifecycle: STARTING, RUNNING, STOPPING, STOPPED, ERROR
    source: Optional[str] = None
    target: Optional[str] = None  # Interface name or file path
    interface: Optional[str] = None
    dataset_name: str = "synthetic"
    status_message: str = "No capture session active"
    message: Optional[str] = None
    started_at: Optional[datetime] = None
    stopped_at: Optional[datetime] = None
    last_packet_at: Optional[datetime] = None
    uptime_seconds: float = 0.0
    packets_captured: int = 0
    packets_parsed: int = 0
    packets_processed: int = 0
    flows_created: int = 0
    events_processed: int = 0
    anomalies_detected: int = 0
    detections_generated: int = 0
    alerts_generated: int = 0
    dropped_events: int = 0
    error_count: int = 0
    error: Optional[str] = None
    throughput_pkts_sec: float = 0.0
    packets_per_second: float = 0.0
    throughput_flows_sec: float = 0.0
    flows_per_second: float = 0.0
    avg_detection_latency_ms: float = 0.0
    buffer_utilization_pct: float = 0.0
    models_compatible: Dict[str, bool] = Field(default_factory=dict)
    available_interfaces: List[InterfaceInfo] = Field(default_factory=list)



class PCAPTestRequest(BaseModel):
    """Request payload for synchronous/test PCAP replay inspection."""
    file: str = Field(..., max_length=500, description="Path to PCAP file inside allowed data directory")
    dataset_name: Optional[str] = Field(default="synthetic", max_length=50, description="Dataset mapping schema")
    max_packets: Optional[int] = Field(default=500, ge=1, le=10000)
    generate_xai: Optional[bool] = Field(default=False)

    @field_validator("file")
    @classmethod
    def validate_file_path(cls, v: str) -> str:
        clean = (v or "").strip()
        if not clean:
            raise ValueError("File path cannot be empty.")
        if "\x00" in clean:
            raise ValueError("Invalid file path: Null bytes are not permitted.")
        ext = "." + clean.rsplit(".", 1)[-1].lower() if "." in clean else ""
        if ext not in [".pcap", ".pcapng", ".cap"]:
            raise ValueError(f"Invalid file extension '{ext}'. Only .pcap, .pcapng, and .cap files are permitted.")
        return clean


class PCAPTestResponse(BaseModel):
    """Comprehensive analysis report from a PCAP replay benchmark."""
    status: str = "completed"
    file: str
    packets_read: int
    packets_parsed: int
    flows_extracted: int
    detections_completed: int
    anomalies_flagged: int
    alerts_triggered: int
    execution_time_ms: float
    throughput_pkts_per_sec: float
    throughput_flows_per_sec: float
    model_compatibility: Dict[str, ModelCompatibilityReport] = Field(default_factory=dict)
    sample_flows: List[Dict[str, Any]] = Field(default_factory=list)
