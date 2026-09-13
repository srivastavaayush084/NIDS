import asyncio
import logging
import time
from typing import Any, Callable, Dict, List, Optional

from backend.app.core.config import settings
from backend.app.monitoring.buffer import MonitoringBuffer
from backend.app.monitoring.capture.base import BaseCaptureSource
from backend.app.monitoring.capture.live_capture import LiveCaptureSource
from backend.app.monitoring.features.extractor import FeatureExtractor
from backend.app.monitoring.features.feature_mapper import FeatureMapper
from backend.app.monitoring.parsing.flow_parser import FlowAggregator
from backend.app.monitoring.parsing.packet_parser import PacketParser
from backend.app.monitoring.schemas import FlowRecord, PacketInfo
from backend.app.monitoring.state import MonitoringState
from backend.app.services.detection_service import DetectionService

logger = logging.getLogger(__name__)


class MonitoringPipeline:
    """
    Asynchronous traffic ingestion and ML detection pipeline.
    Links Packet Ingestion -> Flow Aggregation -> Feature Extraction -> ML Detection -> Alert Service.
    """

    def __init__(
        self,
        capture_source: BaseCaptureSource,
        detection_service: Optional[DetectionService] = None,
        state: Optional[MonitoringState] = None,
        dataset_name: str = "synthetic",
        batch_size: int = 50,
        generate_xai: bool = True,
        buffer_size: int = 10000,
        flow_timeout_seconds: float = 30.0,
        flow_max_packets: int = 1000,
    ):
        self.capture_source = capture_source
        self.detection_service = detection_service or DetectionService()
        self.state = state or MonitoringState()
        self.dataset_name = dataset_name
        self.batch_size = batch_size
        self.generate_xai = generate_xai

        self.buffer = MonitoringBuffer(
            max_size=buffer_size,
            overflow_policy="drop_oldest",
        )
        self.flow_aggregator = FlowAggregator(
            timeout_seconds=flow_timeout_seconds,
            max_packets=flow_max_packets,
        )
        self.feature_extractor = FeatureExtractor()

        self._running = False
        self._consumer_task: Optional[asyncio.Task] = None
        self._flush_task: Optional[asyncio.Task] = None

    @property
    def is_running(self) -> bool:
        return self._running

    def on_packet_received(self, pkt: PacketInfo) -> None:
        """Callback invoked synchronously from capture source worker threads."""
        if not self._running:
            return

        self.state.increment_packets_captured(1)
        self.state.increment_packets_parsed(1)

        try:
            completed_flows = self.flow_aggregator.process_packet(pkt)
            for flow in completed_flows:
                self.state.increment_flows_created(1)
                pushed = self.buffer.push(flow)
                if not pushed:
                    self.state.increment_dropped_events(1)
        except Exception as e:
            logger.error(f"Error aggregating packet into flow: {e}")
            self.state.increment_errors(1)

    async def start(self) -> None:
        """Start the pipeline background worker and begin packet capture."""
        if self._running:
            logger.warning("MonitoringPipeline is already running.")
            return

        self._running = True

        # Check model compatibility
        compat_reports = FeatureMapper.get_all_compatibility(self.dataset_name)
        self.state.set_models_compatible({m: r.compatible for m, r in compat_reports.items()})

        # Start detection consumer and flow expiration loop
        loop = asyncio.get_running_loop()
        self._consumer_task = asyncio.create_task(self._detection_consumer_loop())
        self._flush_task = asyncio.create_task(self._periodic_flow_flusher_loop())

        # Start packet capture source
        try:
            self.capture_source.start(self.on_packet_received)
        except Exception as e:
            self._running = False
            if self._flush_task and not self._flush_task.done():
                self._flush_task.cancel()
            if self._consumer_task and not self._consumer_task.done():
                self._consumer_task.cancel()
            logger.error(f"Failed to start capture source: {e}")
            raise

    async def stop(self) -> None:
        """Gracefully stop packet capture, flush remaining flows, and drain buffer."""
        if not self._running:
            return

        logger.info("Stopping MonitoringPipeline...")
        self._running = False

        # 1. Stop capture source
        try:
            self.capture_source.stop()
        except Exception as e:
            logger.warning(f"Error stopping capture source: {e}")

        # 2. Cancel background worker loops
        if self._flush_task and not self._flush_task.done():
            self._flush_task.cancel()
        if self._consumer_task and not self._consumer_task.done():
            self._consumer_task.cancel()

        # 3. Flush all remaining active flows from aggregator into buffer
        remaining_flows = self.flow_aggregator.flush_all()
        for flow in remaining_flows:
            self.state.increment_flows_created(1)
            self.buffer.push(flow)

        # 4. Drain remaining buffer items with bounded timeout
        try:
            await asyncio.wait_for(self._drain_buffer(), timeout=2.0)
        except asyncio.TimeoutError:
            logger.warning("Buffer drain timed out during pipeline stop.")
        except Exception as e:
            logger.warning(f"Error draining buffer during stop: {e}")

        logger.info("MonitoringPipeline stopped successfully.")

    async def _periodic_flow_flusher_loop(self) -> None:
        """Periodically flushes expired inactive flows into the detection buffer."""
        while self._running:
            try:
                await asyncio.sleep(settings.MONITOR_FLUSH_INTERVAL_SECONDS)
                expired = self.flow_aggregator.flush_expired()
                for flow in expired:
                    self.state.increment_flows_created(1)
                    pushed = self.buffer.push(flow)
                    if not pushed:
                        self.state.increment_dropped_events(1)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in periodic flow flusher: {e}")
                self.state.increment_errors(1)

    async def _detection_consumer_loop(self) -> None:
        """Main detection worker loop processing batches of flows from the buffer."""
        while self._running:
            try:
                # Retrieve batch from buffer
                batch = await self.buffer.async_pop_batch(
                    batch_size=self.batch_size,
                    timeout=0.2,
                )
                if not batch:
                    # Also check if capture source finished (e.g. PCAP replay done)
                    if not self.capture_source.is_running:
                        # If capture source was live and terminated unexpectedly
                        if isinstance(self.capture_source, LiveCaptureSource):
                            max_pkts = getattr(self.capture_source, "max_packets", None)
                            pkt_count = getattr(self.capture_source, "_packet_count", 0)
                            if not max_pkts or pkt_count < max_pkts:
                                iface = getattr(self.capture_source, "interface", "default")
                                err_msg = f"Live packet capture worker terminated unexpectedly on interface '{iface}'."
                                logger.error(err_msg)
                                self.state.record_error(err_msg)
                                self._running = False
                                break

                        # Flush any remaining expired
                        expired = self.flow_aggregator.flush_all()
                        for f in expired:
                            self.state.increment_flows_created(1)
                            self.buffer.push(f)
                    await asyncio.sleep(0.05)
                    continue

                await self._process_flow_batch(batch)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in detection consumer loop: {e}", exc_info=True)
                self.state.increment_errors(1)

    async def _drain_buffer(self) -> None:
        """Drain all remaining items in the buffer before shutdown."""
        while not self.buffer.is_empty():
            batch = self.buffer.pop_batch(batch_size=self.batch_size)
            if batch:
                await self._process_flow_batch(batch)
            else:
                break

    async def _process_flow_batch(self, flows: List[FlowRecord]) -> None:
        """Extract features, map to model schema, and invoke ML DetectionService."""
        for flow in flows:
            t0 = time.perf_counter()
            try:
                # 1. Feature Extraction
                flow_feats = self.feature_extractor.extract_features(flow)

                # 2. Feature Mapping
                mapped_feats = FeatureMapper.map_flow(flow_feats, dataset_name=self.dataset_name)

                # 3. Detection & Alert Inference
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

                det_response = await self.detection_service.detect_single(
                    features=mapped_feats,
                    dataset_name=self.dataset_name,
                    generate_xai=self.generate_xai,
                    flow_context=ctx,
                )

                latency_ms = (time.perf_counter() - t0) * 1000.0
                is_anom = det_response.is_anomaly
                alert_created = (
                    det_response.alert.created
                    if det_response.alert
                    else False
                )

                self.state.increment_events_processed(
                    count=1,
                    latency_ms=latency_ms,
                    is_anomaly=is_anom,
                    alert_created=alert_created,
                )

            except Exception as e:
                logger.error(f"Detection failed for flow '{flow.flow_id}': {e}")
                self.state.increment_errors(1)
