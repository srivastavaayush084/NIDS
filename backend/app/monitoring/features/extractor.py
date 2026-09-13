import collections
import logging
import threading
from typing import Deque, Dict, Tuple

from backend.app.monitoring.features.flow_features import FlowFeatures
from backend.app.monitoring.schemas import FlowRecord

logger = logging.getLogger(__name__)


class FeatureExtractor:
    """
    Statistical and temporal network feature extractor.
    Extracts intrinsic flow metrics and computes sliding-window contextual
    connection frequencies and error rates across historical traffic.
    """

    def __init__(self, time_window_seconds: float = 2.0, host_history_size: int = 100):
        self.time_window_seconds = time_window_seconds
        self.host_history_size = host_history_size

        # Sliding window for 2-second time-based metrics: (timestamp, dst_ip, service, tcp_state)
        self._time_window: Deque[Tuple[float, str, str, str]] = collections.deque()
        # History for host-based metrics: (dst_ip, service)
        self._host_history: Deque[Tuple[str, str]] = collections.deque()
        self._lock = threading.Lock()

    def reset(self) -> None:
        """Clear all sliding window history."""
        with self._lock:
            self._time_window.clear()
            self._host_history.clear()

    def extract_features(self, flow: FlowRecord) -> FlowFeatures:
        """
        Extract flow statistics and sliding-window contextual aggregates from a FlowRecord.
        """
        duration = max(0.0, float(flow.duration))
        src_bytes = int(flow.fwd_bytes)
        dst_bytes = int(flow.bwd_bytes)
        src_pkts = int(flow.fwd_packets)
        dst_pkts = int(flow.bwd_packets)
        total_bytes = int(flow.total_bytes)
        total_pkts = int(flow.total_packets)

        # Derived ratios and rates
        byte_ratio = float(src_bytes) / float(total_bytes + 1e-6)
        packet_ratio = float(src_pkts) / float(total_pkts + 1e-6)
        time_denom = duration if duration > 0.001 else 0.001
        src_byte_rate = float(src_bytes) / time_denom
        dst_byte_rate = float(dst_bytes) / time_denom
        packet_rate = float(total_pkts) / time_denom

        proto_lower = flow.protocol.lower()
        service_lower = flow.service.lower()
        state = flow.tcp_state

        with self._lock:
            # 1. Update and prune 2-second time window
            cutoff_time = flow.last_time - self.time_window_seconds
            while self._time_window and self._time_window[0][0] < cutoff_time:
                self._time_window.popleft()

            # Record current flow into time window
            self._time_window.append((flow.last_time, flow.dst_ip, service_lower, state))

            # Compute 2-sec metrics for this destination IP
            same_dst_flows = [item for item in self._time_window if item[1] == flow.dst_ip]
            count = len(same_dst_flows)
            srv_count = sum(1 for item in same_dst_flows if item[2] == service_lower)
            serror_count = sum(1 for item in same_dst_flows if item[3] == "S0")

            serror_rate = (serror_count / count) if count > 0 else 0.0
            same_srv_rate = (srv_count / count) if count > 0 else 1.0
            diff_srv_rate = (1.0 - same_srv_rate) if count > 0 else 0.0

            # 2. Update host history (last 100 connections)
            self._host_history.append((flow.dst_ip, service_lower))
            while len(self._host_history) > self.host_history_size:
                self._host_history.popleft()

            # Compute host-based metrics
            dst_host_count = sum(1 for (dip, _) in self._host_history if dip == flow.dst_ip)
            dst_host_srv_count = sum(
                1 for (dip, srv) in self._host_history if dip == flow.dst_ip and srv == service_lower
            )

        return FlowFeatures(
            flow_id=flow.flow_id,
            src_ip=flow.src_ip,
            dst_ip=flow.dst_ip,
            src_port=flow.src_port,
            dst_port=flow.dst_port,
            protocol=proto_lower,
            service=service_lower,
            tcp_state=state,
            duration=round(duration, 6),
            src_bytes=src_bytes,
            dst_bytes=dst_bytes,
            src_pkts=src_pkts,
            dst_pkts=dst_pkts,
            total_bytes=total_bytes,
            total_pkts=total_pkts,
            byte_ratio=round(byte_ratio, 6),
            packet_ratio=round(packet_ratio, 6),
            src_byte_rate=round(src_byte_rate, 4),
            dst_byte_rate=round(dst_byte_rate, 4),
            packet_rate=round(packet_rate, 4),
            count=count,
            srv_count=srv_count,
            serror_rate=round(serror_rate, 4),
            same_srv_rate=round(same_srv_rate, 4),
            diff_srv_rate=round(diff_srv_rate, 4),
            dst_host_count=dst_host_count,
            dst_host_srv_count=dst_host_srv_count,
            metadata={
                "fwd_flag_counts": flow.fwd_flag_counts,
                "bwd_flag_counts": flow.bwd_flag_counts,
                **flow.metadata,
            },
        )
