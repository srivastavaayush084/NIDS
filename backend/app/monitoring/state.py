import time
import threading
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from backend.app.monitoring.schemas import InterfaceInfo, MonitoringStatusResponse


class MonitoringState:
    """
    Thread-safe runtime telemetry state tracker for real-time traffic monitoring,
    capture performance, throughput rates, and ML detection statistics.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self.status: str = "STOPPED"
        self.running: bool = False
        self.source: Optional[str] = None
        self.target: Optional[str] = None
        self.dataset_name: str = "synthetic"
        self.started_at: Optional[datetime] = None
        self.stopped_at: Optional[datetime] = None
        self.last_packet_at: Optional[datetime] = None
        self._start_perf_time: Optional[float] = None
        self._stop_perf_time: Optional[float] = None

        self.packets_captured: int = 0
        self.packets_parsed: int = 0
        self.flows_created: int = 0
        self.events_processed: int = 0
        self.anomalies_detected: int = 0
        self.alerts_generated: int = 0
        self.dropped_events: int = 0
        self.error_count: int = 0
        self.last_error_message: Optional[str] = None
        self.total_detection_latency_ms: float = 0.0
        self.models_compatible: Dict[str, bool] = {}

    def reset(self) -> None:
        """Reset state metrics to zero."""
        with self._lock:
            self.status = "STOPPED"
            self.running = False
            self.source = None
            self.target = None
            self.started_at = None
            self.stopped_at = None
            self.last_packet_at = None
            self._start_perf_time = None
            self._stop_perf_time = None
            self.packets_captured = 0
            self.packets_parsed = 0
            self.flows_created = 0
            self.events_processed = 0
            self.anomalies_detected = 0
            self.alerts_generated = 0
            self.dropped_events = 0
            self.error_count = 0
            self.last_error_message = None
            self.total_detection_latency_ms = 0.0
            self.models_compatible = {}

    def record_start(self, source: str, target: str, dataset_name: str = "synthetic") -> None:
        """Record start of a monitoring session (transitions to STARTING)."""
        with self._lock:
            self.status = "STARTING"
            self.running = True
            self.source = source
            self.target = target
            self.dataset_name = dataset_name
            self.started_at = datetime.now(timezone.utc)
            self.stopped_at = None
            self.last_packet_at = None
            self._start_perf_time = time.perf_counter()
            self._stop_perf_time = None
            self.packets_captured = 0
            self.packets_parsed = 0
            self.flows_created = 0
            self.events_processed = 0
            self.anomalies_detected = 0
            self.alerts_generated = 0
            self.dropped_events = 0
            self.error_count = 0
            self.last_error_message = None
            self.total_detection_latency_ms = 0.0

    def record_running(self) -> None:
        """Record transition to RUNNING after pipeline worker and sniffer start."""
        with self._lock:
            self.status = "RUNNING"
            self.running = True

    def record_stopping(self) -> None:
        """Record transition to STOPPING during graceful session shutdown."""
        with self._lock:
            self.status = "STOPPING"

    def record_stop(self) -> None:
        """Record termination of monitoring session (transitions to STOPPED)."""
        with self._lock:
            self.status = "STOPPED"
            self.running = False
            self.stopped_at = datetime.now(timezone.utc)
            self._stop_perf_time = time.perf_counter()

    def record_error(self, error_msg: str) -> None:
        """Record transition to ERROR state with descriptive diagnostic message."""
        with self._lock:
            self.status = "ERROR"
            self.running = False
            self.error_count += 1
            self.last_error_message = error_msg
            self.stopped_at = datetime.now(timezone.utc)
            self._stop_perf_time = time.perf_counter()

    def increment_packets_captured(self, count: int = 1) -> None:
        with self._lock:
            self.packets_captured += count
            self.last_packet_at = datetime.now(timezone.utc)

    def increment_packets_parsed(self, count: int = 1) -> None:
        with self._lock:
            self.packets_parsed += count

    def increment_flows_created(self, count: int = 1) -> None:
        with self._lock:
            self.flows_created += count

    def increment_events_processed(
        self,
        count: int = 1,
        latency_ms: float = 0.0,
        is_anomaly: bool = False,
        alert_created: bool = False,
    ) -> None:
        with self._lock:
            self.events_processed += count
            self.total_detection_latency_ms += latency_ms
            if is_anomaly:
                self.anomalies_detected += count
            if alert_created:
                self.alerts_generated += count

    def increment_dropped_events(self, count: int = 1) -> None:
        with self._lock:
            self.dropped_events += count

    def increment_errors(self, count: int = 1, error_msg: Optional[str] = None) -> None:
        with self._lock:
            self.error_count += count
            if error_msg:
                self.last_error_message = error_msg

    def set_models_compatible(self, models_dict: Dict[str, bool]) -> None:
        with self._lock:
            self.models_compatible = dict(models_dict)

    def get_status(
        self,
        current_buffer_size: int = 0,
        max_buffer_size: int = 10000,
        interfaces_list: Optional[list] = None,
    ) -> MonitoringStatusResponse:
        """Compute and return real-time status and throughput telemetry."""
        with self._lock:
            uptime = 0.0
            if self._start_perf_time is not None:
                end_t = self._stop_perf_time or time.perf_counter()
                uptime = max(0.0, end_t - self._start_perf_time)

            throughput_pkts = (self.packets_captured / uptime) if uptime > 0 else 0.0
            throughput_flows = (self.flows_created / uptime) if uptime > 0 else 0.0
            avg_latency = (
                (self.total_detection_latency_ms / self.events_processed)
                if self.events_processed > 0
                else 0.0
            )
            buffer_util = (
                round((current_buffer_size / max_buffer_size) * 100.0, 2)
                if max_buffer_size > 0
                else 0.0
            )

            # Construct human-friendly status message
            if self.status == "ERROR":
                msg = f"Capture failed: {self.last_error_message or 'Unknown error'}"
            elif self.status == "STARTING":
                msg = f"Initializing capture session on '{self.target or 'default'}'..."
            elif self.status == "STOPPING":
                msg = "Stopping capture session and flushing pipeline buffers..."
            elif self.status == "RUNNING" or self.running:
                if self.source == "live":
                    if self.packets_captured == 0:
                        msg = f"Capture active on interface '{self.target or 'default'}' — no packets observed yet"
                    else:
                        msg = f"Live network capture active on interface '{self.target or 'default'}' ({self.packets_captured} packets captured)"
                else:
                    msg = f"Streaming PCAP replay active from '{self.target or 'file'}'"
            else:
                if self.stopped_at:
                    msg = f"Monitoring session stopped. Total processed: {self.events_processed} flows"
                else:
                    msg = "No capture session active. Select an interface or sample PCAP to start monitoring."

            iface_val = self.target if self.source == "live" else None

            # Map raw interfaces list into InterfaceInfo schemas if provided
            iface_objects = []
            if interfaces_list:
                for iface_item in interfaces_list:
                    if isinstance(iface_item, dict):
                        iface_objects.append(InterfaceInfo(**iface_item))
                    elif isinstance(iface_item, InterfaceInfo):
                        iface_objects.append(iface_item)

            return MonitoringStatusResponse(
                running=self.running,
                active=self.running,
                status=self.status,
                source=self.source,
                target=self.target,
                interface=iface_val,
                dataset_name=self.dataset_name,
                status_message=msg,
                message=msg,
                started_at=self.started_at,
                stopped_at=self.stopped_at,
                last_packet_at=self.last_packet_at,
                uptime_seconds=round(uptime, 2),
                packets_captured=self.packets_captured,
                packets_parsed=self.packets_parsed,
                packets_processed=self.events_processed,
                flows_created=self.flows_created,
                events_processed=self.events_processed,
                anomalies_detected=self.anomalies_detected,
                detections_generated=self.events_processed,
                alerts_generated=self.alerts_generated,
                dropped_events=self.dropped_events,
                error_count=self.error_count,
                error=self.last_error_message,
                throughput_pkts_sec=round(throughput_pkts, 2),
                packets_per_second=round(throughput_pkts, 2),
                throughput_flows_sec=round(throughput_flows, 2),
                flows_per_second=round(throughput_flows, 2),
                avg_detection_latency_ms=round(avg_latency, 2),
                buffer_utilization_pct=buffer_util,
                models_compatible=self.models_compatible,
                available_interfaces=iface_objects,
            )


    def get_summary(self) -> Dict[str, Any]:
        """Return raw metrics dictionary for shutdown logging and persistence."""
        status = self.get_status()
        return status.model_dump()
