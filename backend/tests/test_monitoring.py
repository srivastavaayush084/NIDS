import asyncio
import os
import tempfile
import time
from pathlib import Path
import pytest
from httpx import AsyncClient, ASGITransport

from scapy.layers.inet import ICMP, IP, TCP, UDP
from scapy.layers.inet6 import IPv6
from scapy.layers.l2 import Ether, ARP
from scapy.utils import wrpcap

from backend.app.core.config import settings
from backend.app.main import app
from backend.app.monitoring.buffer import MonitoringBuffer
from backend.app.monitoring.capture.live_capture import LiveCaptureSource
from backend.app.monitoring.capture.pcap_reader import PCAPCaptureSource
from backend.app.monitoring.features.extractor import FeatureExtractor
from backend.app.monitoring.features.feature_mapper import FeatureMapper
from backend.app.monitoring.features.flow_features import FlowFeatures
from backend.app.monitoring.manager import MonitoringManager, monitoring_manager
from backend.app.monitoring.parsing.flow_parser import FlowAggregator, infer_service
from backend.app.monitoring.parsing.packet_parser import PacketParser
from backend.app.monitoring.pipeline import MonitoringPipeline
from backend.app.monitoring.state import MonitoringState
from backend.app.monitoring.schemas import (
    FlowRecord,
    MonitoringStartRequest,
    PCAPTestRequest,
    PacketInfo,
)
from backend.app.auth.dependencies import get_current_user
from backend.app.models.user import UserDocument


@pytest.fixture(autouse=True)
def override_auth_for_monitoring_tests():
    """Ensure monitoring API test requests execute with admin/analyst credentials."""
    mock_user = UserDocument(
        id="usr-mon-admin",
        user_id="usr-mon-admin",
        username="mon_admin",
        email="monadmin@zeroday.ai",
        hashed_password="$2b$12$mockhashedpasswordsample123456789012345678901234567890",
        role="admin",
        is_active=True,
    )
    app.dependency_overrides[get_current_user] = lambda: mock_user
    yield
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def sample_pcap_file():
    """Create a temporary real PCAP file containing normal and anomalous traffic packets."""
    temp_dir = tempfile.mkdtemp()
    pcap_path = os.path.join(temp_dir, "test_traffic.pcap")

    packets = []
    base_time = 1700000000.0

    # 1. Normal HTTP 3-way handshake and data exchange
    # Client SYN
    p1 = IP(src="192.168.1.50", dst="192.168.1.100") / TCP(sport=54321, dport=80, flags="S", seq=1000)
    p1.time = base_time
    packets.append(p1)

    # Server SYN-ACK
    p2 = IP(src="192.168.1.100", dst="192.168.1.50") / TCP(sport=80, dport=54321, flags="SA", seq=2000, ack=1001)
    p2.time = base_time + 0.01
    packets.append(p2)

    # Client ACK + HTTP Request payload
    p3 = IP(src="192.168.1.50", dst="192.168.1.100") / TCP(sport=54321, dport=80, flags="PA", seq=1001, ack=2001) / b"GET /index.html HTTP/1.1\r\n\r\n"
    p3.time = base_time + 0.02
    packets.append(p3)

    # Server Response + FIN
    p4 = IP(src="192.168.1.100", dst="192.168.1.50") / TCP(sport=80, dport=54321, flags="FA", seq=2001, ack=1030) / b"HTTP/1.1 200 OK\r\n\r\nHello"
    p4.time = base_time + 0.05
    packets.append(p4)

    # Client FIN-ACK
    p5 = IP(src="192.168.1.50", dst="192.168.1.100") / TCP(sport=54321, dport=80, flags="FA", seq=1030, ack=2025)
    p5.time = base_time + 0.06
    packets.append(p5)

    # 2. UDP DNS query
    p6 = IP(src="192.168.1.50", dst="8.8.8.8") / UDP(sport=61234, dport=53) / b"\x00\x01\x01\x00"
    p6.time = base_time + 0.10
    packets.append(p6)

    # 3. ICMP Echo Request
    p7 = IP(src="192.168.1.50", dst="192.168.1.1") / ICMP(type=8, code=0) / b"pingdata12345678"
    p7.time = base_time + 0.15
    packets.append(p7)

    # 4. Port Scan / SYN Flood anomalous packets (S0 states)
    for port in [21, 22, 23, 443, 3306]:
        scan_pkt = IP(src="10.0.0.99", dst="192.168.1.100") / TCP(sport=40000 + port, dport=port, flags="S")
        scan_pkt.time = base_time + 0.20 + (port * 0.001)
        packets.append(scan_pkt)

    wrpcap(pcap_path, packets)
    yield pcap_path

    if os.path.exists(pcap_path):
        os.remove(pcap_path)


# ---------------------------------------------------------------------------
# 1. Packet Parser Unit Tests
# ---------------------------------------------------------------------------
def test_packet_parser_tcp():
    pkt = IP(src="10.0.0.1", dst="10.0.0.2", ttl=64) / TCP(sport=12345, dport=80, flags="PA") / b"payload_bytes"
    pkt.time = 1600000000.0
    parsed = PacketParser.parse_packet(pkt)

    assert parsed is not None
    assert parsed.src_ip == "10.0.0.1"
    assert parsed.dst_ip == "10.0.0.2"
    assert parsed.src_port == 12345
    assert parsed.dst_port == 80
    assert parsed.protocol == "TCP"
    assert parsed.flags.get("PSH") is True
    assert parsed.flags.get("ACK") is True
    assert parsed.flags.get("SYN") is False
    assert parsed.payload_size == len(b"payload_bytes")
    assert parsed.ttl == 64


def test_packet_parser_udp_and_icmp():
    udp_pkt = IP(src="192.168.1.1", dst="192.168.1.2") / UDP(sport=53, dport=1234) / b"data"
    parsed_udp = PacketParser.parse_packet(udp_pkt)
    assert parsed_udp is not None
    assert parsed_udp.protocol == "UDP"
    assert parsed_udp.src_port == 53
    assert parsed_udp.dst_port == 1234

    icmp_pkt = IP(src="192.168.1.1", dst="192.168.1.2") / ICMP(type=8, code=0)
    parsed_icmp = PacketParser.parse_packet(icmp_pkt)
    assert parsed_icmp is not None
    assert parsed_icmp.protocol == "ICMP"


def test_packet_parser_ipv6_and_non_ip():
    ip6_pkt = IPv6(src="2001:db8::1", dst="2001:db8::2") / TCP(sport=8080, dport=80, flags="S")
    parsed_ip6 = PacketParser.parse_packet(ip6_pkt)
    assert parsed_ip6 is not None
    assert parsed_ip6.src_ip == "2001:db8::1"
    assert parsed_ip6.dst_ip == "2001:db8::2"

    arp_pkt = Ether() / ARP()
    assert PacketParser.parse_packet(arp_pkt) is None


# ---------------------------------------------------------------------------
# 2. Flow Aggregator Tests
# ---------------------------------------------------------------------------
def test_flow_aggregator_bidirectional_and_closure():
    aggregator = FlowAggregator(timeout_seconds=5.0, max_packets=100)

    # 1. Client SYN
    p1 = PacketInfo(
        timestamp=100.0,
        src_ip="1.1.1.1",
        dst_ip="2.2.2.2",
        src_port=5000,
        dst_port=80,
        protocol="TCP",
        length=60,
        flags={"SYN": True, "ACK": False},
    )
    res = aggregator.process_packet(p1)
    assert len(res) == 0

    # 2. Server SYN-ACK (Backward packet)
    p2 = PacketInfo(
        timestamp=100.02,
        src_ip="2.2.2.2",
        dst_ip="1.1.1.1",
        src_port=80,
        dst_port=5000,
        protocol="TCP",
        length=60,
        flags={"SYN": True, "ACK": True},
    )
    res = aggregator.process_packet(p2)
    assert len(res) == 0

    # 3. Client FIN-ACK
    p3 = PacketInfo(
        timestamp=100.05,
        src_ip="1.1.1.1",
        dst_ip="2.2.2.2",
        src_port=5000,
        dst_port=80,
        protocol="TCP",
        length=100,
        flags={"FIN": True, "ACK": True},
    )
    res = aggregator.process_packet(p3)
    assert len(res) == 0

    # 4. Server FIN-ACK -> Closes flow
    p4 = PacketInfo(
        timestamp=100.06,
        src_ip="2.2.2.2",
        dst_ip="1.1.1.1",
        src_port=80,
        dst_port=5000,
        protocol="TCP",
        length=100,
        flags={"FIN": True, "ACK": True},
    )
    res = aggregator.process_packet(p4)
    assert len(res) == 1

    flow = res[0]
    assert flow.src_ip == "1.1.1.1"
    assert flow.dst_ip == "2.2.2.2"
    assert flow.fwd_packets == 2
    assert flow.bwd_packets == 2
    assert flow.total_packets == 4
    assert flow.fwd_bytes == 160
    assert flow.bwd_bytes == 160
    assert flow.service == "http"
    assert flow.duration == pytest.approx(0.06, rel=1e-3)


def test_flow_aggregator_expiration():
    aggregator = FlowAggregator(timeout_seconds=2.0)
    p1 = PacketInfo(
        timestamp=10.0,
        src_ip="1.1.1.1",
        dst_ip="2.2.2.2",
        src_port=123,
        dst_port=443,
        protocol="TCP",
        length=80,
        flags={"SYN": True},
    )
    aggregator.process_packet(p1)

    # Flush at t=11.0 (not expired)
    assert len(aggregator.flush_expired(current_time=11.0)) == 0

    # Flush at t=12.5 (expired)
    expired = aggregator.flush_expired(current_time=12.5)
    assert len(expired) == 1
    assert expired[0].service == "ssl_tls"


def test_service_inference():
    assert infer_service(1000, 80, "TCP") == "http"
    assert infer_service(1000, 443, "TCP") == "ssl_tls"
    assert infer_service(1000, 21, "TCP") == "ftp"
    assert infer_service(1000, 25, "TCP") == "smtp"
    assert infer_service(None, None, "ICMP") == "eco_i"
    assert infer_service(50000, 50001, "TCP") == "private"


# ---------------------------------------------------------------------------
# 3. Feature Extraction & Mapping Tests
# ---------------------------------------------------------------------------
def test_feature_extractor_and_mapper():
    extractor = FeatureExtractor(time_window_seconds=2.0, host_history_size=50)

    flow = FlowRecord(
        flow_id="test-1",
        src_ip="192.168.1.10",
        dst_ip="192.168.1.20",
        src_port=4000,
        dst_port=80,
        protocol="TCP",
        start_time=100.0,
        last_time=101.5,
        duration=1.5,
        fwd_packets=5,
        bwd_packets=5,
        total_packets=10,
        fwd_bytes=500,
        bwd_bytes=1500,
        total_bytes=2000,
        tcp_state="SF",
        service="http",
    )

    feats = extractor.extract_features(flow)
    assert feats.src_bytes == 500
    assert feats.dst_bytes == 1500
    assert feats.total_bytes == 2000
    assert feats.byte_ratio == pytest.approx(0.25, rel=1e-2)
    assert feats.count == 1
    assert feats.srv_count == 1

    # Map to synthetic features
    mapped = FeatureMapper.map_to_synthetic(feats)
    assert mapped["src_bytes"] == 500.0
    assert mapped["dst_bytes"] == 1500.0
    assert mapped["protocol_type_tcp"] == 1.0
    assert mapped["protocol_type_icmp"] == 0.0
    assert mapped["service_http"] == 1.0
    assert mapped["flag_SF"] == 1.0
    assert len(mapped) == 26


def test_model_compatibility_check():
    reports = FeatureMapper.get_all_compatibility("synthetic")
    assert "isolation_forest" in reports
    assert "autoencoder" in reports
    assert "lstm_autoencoder" in reports
    assert "random_forest" in reports
    assert "ensemble" in reports

    for model_name, rep in reports.items():
        assert rep.compatible is True
        assert rep.available_features >= 26
        assert len(rep.missing_features) == 0


# ---------------------------------------------------------------------------
# 4. Monitoring Buffer Tests
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_monitoring_buffer():
    buf = MonitoringBuffer(max_size=3, overflow_policy="drop_oldest")

    assert buf.push("item1") is True
    assert buf.push("item2") is True
    assert buf.push("item3") is True
    assert buf.size() == 3

    # Overflow should drop oldest ('item1')
    assert buf.push("item4") is True
    assert buf.size() == 3
    assert buf.total_dropped == 1

    batch = await buf.async_pop_batch(batch_size=2)
    assert batch == ["item2", "item3"]

    item = await buf.async_pop()
    assert item == "item4"
    assert buf.is_empty()


# ---------------------------------------------------------------------------
# 5. Monitoring State Telemetry Tests
# ---------------------------------------------------------------------------
def test_monitoring_state():
    state = MonitoringState()
    assert state.status == "STOPPED"
    assert state.running is False

    # 1. Starting
    state.record_start("pcap", "test.pcap", "synthetic")
    assert state.status == "STARTING"
    assert state.running is True

    # 2. Running
    state.record_running()
    assert state.status == "RUNNING"
    assert state.running is True

    state.increment_packets_captured(10)
    state.increment_packets_parsed(10)
    state.increment_flows_created(3)
    state.increment_events_processed(3, latency_ms=15.0, is_anomaly=True, alert_created=True)

    status = state.get_status()
    assert status.status == "RUNNING"
    assert status.running is True
    assert status.packets_captured == 10
    assert status.flows_created == 3
    assert status.events_processed == 3
    assert status.anomalies_detected == 3
    assert status.alerts_generated == 3
    assert status.avg_detection_latency_ms == pytest.approx(5.0, rel=1e-2)

    # 3. Stopping and Stopped
    state.record_stopping()
    assert state.status == "STOPPING"
    state.record_stop()
    assert state.status == "STOPPED"
    assert state.running is False

    # 4. Error state transition
    state.record_error("Capture thread crashed")
    assert state.status == "ERROR"
    assert state.running is False
    assert state.error_count == 1
    assert "Capture thread crashed" in state.last_error_message
    err_status = state.get_status()
    assert err_status.status == "ERROR"
    assert "Capture failed" in err_status.status_message


# ---------------------------------------------------------------------------
# 6. PCAP Replay Benchmark & Pipeline Test
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_pcap_capture_source_and_test_mode(sample_pcap_file):
    req = PCAPTestRequest(
        file=sample_pcap_file,
        max_packets=50,
        dataset_name="synthetic",
        generate_xai=False,
    )
    mgr = MonitoringManager()
    report = await mgr.test_pcap(req)

    assert report.status == "completed"
    assert report.packets_read > 0
    assert report.packets_parsed > 0
    assert report.flows_extracted > 0
    assert report.detections_completed > 0
    assert len(report.sample_flows) > 0
    assert "isolation_forest" in report.model_compatibility


# ---------------------------------------------------------------------------
# 7. Live Capture Driver Availability Diagnostic Test
# ---------------------------------------------------------------------------
def test_live_capture_availability_check():
    import platform
    avail, msg = LiveCaptureSource.check_capture_availability()
    assert isinstance(avail, bool)
    assert isinstance(msg, str)
    if platform.system().lower() == "windows":
        from scapy.config import conf as scapy_conf
        if not getattr(scapy_conf, "use_pcap", False):
            assert avail is False
            assert "Npcap" in msg

    # Verify interface enumeration
    ifaces = LiveCaptureSource.get_available_interfaces()
    assert isinstance(ifaces, list)
    if ifaces:
        assert "name" in ifaces[0]
        assert "is_default" in ifaces[0]

    # Verify interface resolution doesn't crash on arbitrary or empty name
    resolved_none = LiveCaptureSource.resolve_scapy_interface(None)
    assert resolved_none is None
    resolved_str = LiveCaptureSource.resolve_scapy_interface("Wi-Fi")
    assert resolved_str is not None


@pytest.mark.asyncio
async def test_live_capture_failure_and_manager_error_rollback():
    """Verify that starting live capture when driver is missing raises error and rolls back cleanly."""
    mgr = MonitoringManager()
    req = MonitoringStartRequest(
        source="live",
        interface="Wi-Fi",
        filter="tcp",
        max_packets=10,
        dataset_name="synthetic",
    )
    # Check driver availability
    avail, _ = LiveCaptureSource.check_capture_availability()
    if not avail:
        with pytest.raises((PermissionError, RuntimeError)):
            await mgr.start(req)
        # Verify manager rolled back and state reflects ERROR
        assert mgr.pipeline is None
        status = mgr.get_status()
        assert status.status == "ERROR"
        assert status.running is False
        assert status.error is not None


# ---------------------------------------------------------------------------
# 8. REST API Integration Tests
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_monitoring_api_endpoints(sample_pcap_file):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Compatibility matrix
        resp = await client.get("/api/v1/monitoring/compatibility?dataset_name=synthetic")
        assert resp.status_code == 200
        data = resp.json()
        assert "ensemble" in data
        assert data["ensemble"]["compatible"] is True

        # 2. Get initial status
        resp = await client.get("/api/v1/monitoring/status")
        assert resp.status_code == 200
        assert "running" in resp.json()

        # 3. Synchronous test-pcap endpoint
        resp = await client.post(
            "/api/v1/monitoring/test-pcap",
            json={
                "file": sample_pcap_file,
                "max_packets": 20,
                "dataset_name": "synthetic",
                "generate_xai": False,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "completed"
        assert data["packets_read"] > 0
        assert data["flows_extracted"] > 0

        # 4. Start monitoring session with PCAP
        start_payload = {
            "source": "pcap",
            "file": sample_pcap_file,
            "max_packets": 50,
            "replay_speed": 0.0,
            "dataset_name": "synthetic",
            "generate_xai": False,
        }
        resp = await client.post("/api/v1/monitoring/start", json=start_payload)
        assert resp.status_code == 200
        assert resp.json()["running"] is True

        # Let pipeline process briefly
        await asyncio.sleep(0.5)

        # 5. Check status during or after run
        resp = await client.get("/api/v1/monitoring/status")
        assert resp.status_code == 200

        # 6. Stop monitoring session
        resp = await client.post("/api/v1/monitoring/stop")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "stopped"
        assert "summary" in data

        # 7. Test interfaces enumeration endpoint
        resp = await client.get("/api/v1/monitoring/interfaces")
        assert resp.status_code == 200
        iface_data = resp.json()
        assert "interfaces" in iface_data
        assert "driver_available" in iface_data
        assert "driver_message" in iface_data
        assert isinstance(iface_data["interfaces"], list)

