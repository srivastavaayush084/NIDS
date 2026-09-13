from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class FlowFeatures:
    """
    Extracted flow metrics and network statistical measurements.
    Contains both intrinsic flow statistics and sliding-window contextual aggregates.
    """
    # Core flow attributes
    flow_id: str
    src_ip: str
    dst_ip: str
    src_port: Optional[int]
    dst_port: Optional[int]
    protocol: str
    service: str
    tcp_state: str

    # Direct flow metrics
    duration: float
    src_bytes: int
    dst_bytes: int
    src_pkts: int
    dst_pkts: int
    total_bytes: int
    total_pkts: int

    # Derived rate and ratio metrics
    byte_ratio: float
    packet_ratio: float
    src_byte_rate: float
    dst_byte_rate: float
    packet_rate: float

    # Sliding-window traffic metrics (e.g. KDD/CICIDS statistical features)
    count: int = 1
    srv_count: int = 1
    serror_rate: float = 0.0
    same_srv_rate: float = 1.0
    diff_srv_rate: float = 0.0
    dst_host_count: int = 1
    dst_host_srv_count: int = 1

    # Raw metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
