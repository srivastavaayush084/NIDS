import logging
import time
import uuid
from typing import Dict, List, Optional, Tuple

from backend.app.monitoring.schemas import FlowRecord, PacketInfo

logger = logging.getLogger(__name__)

PORT_SERVICE_MAP = {
    80: "http",
    8080: "http",
    8000: "http",
    443: "ssl_tls",
    8443: "ssl_tls",
    21: "ftp",
    20: "ftp",
    22: "ssh",
    23: "telnet",
    25: "smtp",
    465: "smtp",
    587: "smtp",
    53: "dns",
    110: "pop3",
    143: "imap",
    3306: "mysql",
    5432: "postgresql",
    27017: "mongodb",
    6379: "redis",
}


def infer_service(src_port: Optional[int], dst_port: Optional[int], protocol: str) -> str:
    """Infer network service based on destination or source port and protocol."""
    if protocol == "ICMP":
        return "eco_i"

    for port in (dst_port, src_port):
        if port is not None and port in PORT_SERVICE_MAP:
            return PORT_SERVICE_MAP[port]

    if src_port is not None and dst_port is not None:
        # Private / high dynamic ports
        if dst_port >= 49152 or src_port >= 49152:
            return "private"

    return "other"


class FlowAggregator:
    """
    Stateful bidirectional network flow aggregator that groups stream of PacketInfo
    objects into 5-tuple flows, tracks TCP connection states, and emits completed/expired FlowRecords.
    """

    def __init__(
        self,
        timeout_seconds: float = 30.0,
        max_packets: int = 1000,
    ):
        self.timeout_seconds = timeout_seconds
        self.max_packets = max_packets
        # Map 5-tuple canonical key -> internal flow state dict
        self._active_flows: Dict[Tuple[str, str, Optional[int], Optional[int], str], Dict] = {}

    def _get_flow_key(
        self, pkt: PacketInfo
    ) -> Tuple[Tuple[str, str, Optional[int], Optional[int], str], bool]:
        """
        Identify or establish canonical 5-tuple key for packet.
        Returns ((src_ip, dst_ip, src_port, dst_port, proto), is_forward)
        """
        fwd_key = (pkt.src_ip, pkt.dst_ip, pkt.src_port, pkt.dst_port, pkt.protocol)
        bwd_key = (pkt.dst_ip, pkt.src_ip, pkt.dst_port, pkt.src_port, pkt.protocol)

        if fwd_key in self._active_flows:
            return fwd_key, True
        elif bwd_key in self._active_flows:
            return bwd_key, False
        else:
            return fwd_key, True

    def process_packet(self, pkt: PacketInfo) -> List[FlowRecord]:
        """
        Ingest a single PacketInfo.
        Returns a list of completed FlowRecords if this packet completed/closed any flows.
        """
        completed: List[FlowRecord] = []
        flow_key, is_fwd = self._get_flow_key(pkt)

        if flow_key not in self._active_flows:
            # Create new flow
            service = infer_service(pkt.src_port, pkt.dst_port, pkt.protocol)
            self._active_flows[flow_key] = {
                "flow_id": f"flow-{uuid.uuid4().hex[:12]}",
                "src_ip": pkt.src_ip,
                "dst_ip": pkt.dst_ip,
                "src_port": pkt.src_port,
                "dst_port": pkt.dst_port,
                "protocol": pkt.protocol,
                "start_time": pkt.timestamp,
                "last_time": pkt.timestamp,
                "fwd_packets": 0,
                "bwd_packets": 0,
                "fwd_bytes": 0,
                "bwd_bytes": 0,
                "fwd_flag_counts": {},
                "bwd_flag_counts": {},
                "tcp_state": "ESTABLISHED" if pkt.protocol == "TCP" else "OTH",
                "service": service,
                "is_closed": False,
                "packet_timestamps": [],
                "packet_sizes": [],
            }

        flow = self._active_flows[flow_key]
        flow["last_time"] = pkt.timestamp
        flow["packet_timestamps"].append(pkt.timestamp)
        flow["packet_sizes"].append(pkt.length)

        # Directional packet & byte counts
        if is_fwd:
            flow["fwd_packets"] += 1
            flow["fwd_bytes"] += pkt.length
            for flag, active in pkt.flags.items():
                if active:
                    flow["fwd_flag_counts"][flag] = flow["fwd_flag_counts"].get(flag, 0) + 1
        else:
            flow["bwd_packets"] += 1
            flow["bwd_bytes"] += pkt.length
            for flag, active in pkt.flags.items():
                if active:
                    flow["bwd_flag_counts"][flag] = flow["bwd_flag_counts"].get(flag, 0) + 1

        # Check TCP flags for state tracking
        if pkt.protocol == "TCP":
            # SYN without ACK
            if pkt.flags.get("SYN") and not pkt.flags.get("ACK"):
                if flow["fwd_packets"] == 1 and flow["bwd_packets"] == 0:
                    flow["tcp_state"] = "S0"
            # RST flag
            if pkt.flags.get("RST"):
                flow["tcp_state"] = "REJ"
                flow["is_closed"] = True
            # FIN flag
            if pkt.flags.get("FIN"):
                flow["tcp_state"] = "SF"
                # If FIN seen in both directions or closed, mark ready to flush
                if (flow["fwd_flag_counts"].get("FIN", 0) > 0 and
                        flow["bwd_flag_counts"].get("FIN", 0) > 0):
                    flow["is_closed"] = True
            # Normal completed handshake
            if pkt.flags.get("ACK") and flow["tcp_state"] == "S0":
                flow["tcp_state"] = "SF"

        total_pkts = flow["fwd_packets"] + flow["bwd_packets"]

        # If flow is explicitly closed or exceeded max_packets, emit it
        if flow["is_closed"] or total_pkts >= self.max_packets:
            record = self._convert_to_record(flow)
            completed.append(record)
            del self._active_flows[flow_key]

        return completed

    def flush_expired(self, current_time: Optional[float] = None) -> List[FlowRecord]:
        """
        Check all active flows and flush those that have exceeded timeout_seconds of inactivity.
        """
        if current_time is None:
            current_time = time.time()

        expired_keys: List[Tuple] = []
        expired_records: List[FlowRecord] = []

        for key, flow in self._active_flows.items():
            if (current_time - flow["last_time"]) >= self.timeout_seconds:
                expired_keys.append(key)
                expired_records.append(self._convert_to_record(flow))

        for key in expired_keys:
            del self._active_flows[key]

        return expired_records

    def flush_all(self) -> List[FlowRecord]:
        """Flush and return all currently active flows regardless of timeout."""
        records = [self._convert_to_record(flow) for flow in self._active_flows.values()]
        self._active_flows.clear()
        return records

    def _convert_to_record(self, flow: Dict) -> FlowRecord:
        """Convert internal flow dict to FlowRecord Pydantic model."""
        fwd_pkts = flow["fwd_packets"]
        bwd_pkts = flow["bwd_packets"]
        fwd_bytes = flow["fwd_bytes"]
        bwd_bytes = flow["bwd_bytes"]
        duration = max(0.0, flow["last_time"] - flow["start_time"])

        return FlowRecord(
            flow_id=flow["flow_id"],
            src_ip=flow["src_ip"],
            dst_ip=flow["dst_ip"],
            src_port=flow["src_port"],
            dst_port=flow["dst_port"],
            protocol=flow["protocol"],
            start_time=flow["start_time"],
            last_time=flow["last_time"],
            duration=round(duration, 6),
            fwd_packets=fwd_pkts,
            bwd_packets=bwd_pkts,
            total_packets=fwd_pkts + bwd_pkts,
            fwd_bytes=fwd_bytes,
            bwd_bytes=bwd_bytes,
            total_bytes=fwd_bytes + bwd_bytes,
            fwd_flag_counts=dict(flow["fwd_flag_counts"]),
            bwd_flag_counts=dict(flow["bwd_flag_counts"]),
            tcp_state=flow["tcp_state"],
            service=flow["service"],
            is_closed=flow["is_closed"],
            metadata={
                "packet_sizes": flow.get("packet_sizes", []),
                "packet_timestamps": flow.get("packet_timestamps", []),
            },
        )
