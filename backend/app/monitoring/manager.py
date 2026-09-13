import asyncio
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from backend.app.core.config import settings
from backend.app.monitoring.capture.live_capture import LiveCaptureSource
from backend.app.monitoring.capture.pcap_reader import PCAPCaptureSource, resolve_and_validate_pcap_path
from backend.app.monitoring.features.extractor import FeatureExtractor
from backend.app.monitoring.features.feature_mapper import FeatureMapper
from backend.app.monitoring.parsing.flow_parser import FlowAggregator
from backend.app.monitoring.parsing.packet_parser import PacketParser
from backend.app.monitoring.pipeline import MonitoringPipeline
from backend.app.monitoring.schemas import (
    InterfaceInfo,
    InterfaceListResponse,
    MonitoringStartRequest,
    MonitoringStatusResponse,
    MonitoringStopResponse,
    PCAPTestRequest,
    PCAPTestResponse,
)
from backend.app.monitoring.state import MonitoringState
from backend.app.services.detection_service import DetectionService

logger = logging.getLogger(__name__)

try:
    import scapy.layers.l2  # noqa: F401
    import scapy.layers.inet  # noqa: F401
    from scapy.utils import PcapReader
    SCAPY_AVAILABLE = True
except ImportError:  # pragma: no cover
    SCAPY_AVAILABLE = False
    PcapReader = None


class MonitoringManager:
    """
    Singleton lifecycle controller for the network monitoring and traffic ingestion subsystem.
    Manages active capture sessions, pipeline execution, real-time status reporting,
    and synchronous PCAP inspection test runs.
    """

    def __init__(self):
        self.state = MonitoringState()
        self.pipeline: Optional[MonitoringPipeline] = None
        self.detection_service = DetectionService()
        self._lock = asyncio.Lock()

    async def start(self, req: MonitoringStartRequest) -> MonitoringStatusResponse:
        """Start a new monitoring session (live interface or PCAP replay)."""
        async with self._lock:
            if self.pipeline and self.pipeline.is_running:
                raise ValueError("A monitoring session is already active. Stop the current session before starting a new one.")

            if req.source == "live":
                chosen_iface = req.interface.strip() if (req.interface and req.interface.strip()) else LiveCaptureSource.get_default_interface()
                target_desc = chosen_iface or "default"
                capture_source = LiveCaptureSource(
                    interface=chosen_iface,
                    filter_bpf=req.filter,
                    max_packets=req.max_packets,
                )
            else:
                if not req.file:
                    raise ValueError("A valid 'file' path must be provided when source='pcap'.")
                target_desc = req.file
                capture_source = PCAPCaptureSource(
                    file_path=req.file,
                    max_packets=req.max_packets,
                    replay_speed=req.replay_speed or 0.0,
                )

            # Record session start in state (transitions to STARTING)
            self.state.record_start(
                source=req.source,
                target=str(target_desc),
                dataset_name=req.dataset_name or "synthetic",
            )

            try:
                # Instantiate and start pipeline
                self.pipeline = MonitoringPipeline(
                    capture_source=capture_source,
                    detection_service=self.detection_service,
                    state=self.state,
                    dataset_name=req.dataset_name or "synthetic",
                    batch_size=req.batch_size or settings.MONITOR_BATCH_SIZE,
                    generate_xai=req.generate_xai if req.generate_xai is not None else True,
                    buffer_size=settings.MONITOR_BUFFER_SIZE,
                    flow_timeout_seconds=settings.MONITOR_FLOW_TIMEOUT_SECONDS,
                    flow_max_packets=settings.MONITOR_FLOW_MAX_PACKETS,
                )

                await self.pipeline.start()
                self.state.record_running()
                logger.info(f"Monitoring session started successfully on source='{req.source}', target='{target_desc}'")
                return self.get_status()

            except Exception as e:
                logger.error(f"Failed to start monitoring session: {e}", exc_info=True)
                self.state.record_error(str(e))
                if self.pipeline:
                    try:
                        await self.pipeline.stop()
                    except Exception:
                        pass
                    self.pipeline = None
                raise

    async def stop(self) -> MonitoringStopResponse:
        """Stop current monitoring session."""
        async with self._lock:
            if not self.pipeline or not self.pipeline.is_running:
                return MonitoringStopResponse(
                    status="stopped",
                    message="No active monitoring session was running.",
                    stopped_at=datetime.now(timezone.utc),
                    summary=self.state.get_summary(),
                )

            self.state.record_stopping()
            try:
                await self.pipeline.stop()
            finally:
                self.state.record_stop()
                self.pipeline = None

            summary = self.state.get_summary()
            logger.info(f"Monitoring session stopped. Total processed: {self.state.events_processed}")
            return MonitoringStopResponse(
                status="stopped",
                message="Monitoring session stopped successfully.",
                stopped_at=datetime.now(timezone.utc),
                summary=summary,
            )

    def get_interfaces(self) -> InterfaceListResponse:
        """Enumerate host network capture interfaces and driver readiness."""
        ifaces = LiveCaptureSource.get_available_interfaces()
        avail, msg = LiveCaptureSource.check_capture_availability()
        return InterfaceListResponse(
            interfaces=[InterfaceInfo(**item) for item in ifaces],
            driver_available=avail,
            driver_message=msg,
            count=len(ifaces),
        )

    def get_status(self) -> MonitoringStatusResponse:
        """Retrieve real-time metrics and health status."""
        current_buf = self.pipeline.buffer.size() if (self.pipeline and self.pipeline.buffer) else 0
        ifaces = LiveCaptureSource.get_available_interfaces()
        return self.state.get_status(
            current_buffer_size=current_buf,
            max_buffer_size=settings.MONITOR_BUFFER_SIZE,
            interfaces_list=ifaces,
        )

    async def test_pcap(self, req: PCAPTestRequest) -> PCAPTestResponse:
        """
        Execute an isolated synchronous replay and detection analysis on a PCAP file.
        Does not affect any active monitoring session.
        """
        if not SCAPY_AVAILABLE:
            raise RuntimeError("Scapy is not installed. PCAP testing unavailable.")

        p = resolve_and_validate_pcap_path(req.file)

        t0 = time.perf_counter()
        aggregator = FlowAggregator(timeout_seconds=settings.MONITOR_FLOW_TIMEOUT_SECONDS)
        extractor = FeatureExtractor()
        ds_name = req.dataset_name or "synthetic"

        pkts_read = 0
        pkts_parsed = 0
        completed_flows = []

        with PcapReader(str(p)) as reader:
            for raw_pkt in reader:
                pkts_read += 1
                parsed = PacketParser.parse_packet(raw_pkt)
                if parsed:
                    pkts_parsed += 1
                    flows = aggregator.process_packet(parsed)
                    completed_flows.extend(flows)

                if req.max_packets and pkts_read >= req.max_packets:
                    break

        # Flush remaining flows
        completed_flows.extend(aggregator.flush_all())

        # Perform ML detections on extracted flows
        detections_completed = 0
        anomalies_flagged = 0
        alerts_triggered = 0
        sample_flows = []

        for flow in completed_flows:
            feats = extractor.extract_features(flow)
            mapped = FeatureMapper.map_flow(feats, dataset_name=ds_name)

            ctx = {
                "flow_id": flow.flow_id,
                "src_ip": flow.src_ip,
                "dst_ip": flow.dst_ip,
                "src_port": flow.src_port,
                "dst_port": flow.dst_port,
                "protocol": flow.protocol,
                "service": flow.service,
                "duration": flow.duration,
                "total_bytes": flow.total_bytes,
                "total_packets": flow.total_packets,
            }

            det_res = await self.detection_service.detect_single(
                features=mapped,
                dataset_name=ds_name,
                generate_xai=req.generate_xai or False,
                flow_context=ctx,
            )

            detections_completed += 1
            if det_res.is_anomaly:
                anomalies_flagged += 1
            if det_res.alert and det_res.alert.created:
                alerts_triggered += 1

            if len(sample_flows) < 10:
                sample_flows.append({
                    "flow_id": flow.flow_id,
                    "src_ip": flow.src_ip,
                    "dst_ip": flow.dst_ip,
                    "protocol": flow.protocol,
                    "service": flow.service,
                    "is_anomaly": det_res.is_anomaly,
                    "risk_score": det_res.risk_score,
                    "severity": det_res.severity,
                })

        duration_sec = max(0.001, time.perf_counter() - t0)
        compat = FeatureMapper.get_all_compatibility(ds_name)

        return PCAPTestResponse(
            status="completed",
            file=str(p),
            packets_read=pkts_read,
            packets_parsed=pkts_parsed,
            flows_extracted=len(completed_flows),
            detections_completed=detections_completed,
            anomalies_flagged=anomalies_flagged,
            alerts_triggered=alerts_triggered,
            execution_time_ms=round(duration_sec * 1000.0, 2),
            throughput_pkts_per_sec=round(pkts_read / duration_sec, 2),
            throughput_flows_per_sec=round(len(completed_flows) / duration_sec, 2),
            model_compatibility=compat,
            sample_flows=sample_flows,
        )


monitoring_manager = MonitoringManager()
