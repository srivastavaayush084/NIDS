import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient

from backend.app.models.user import UserDocument
from backend.app.monitoring.schemas import MonitoringStatusResponse


def test_public_health_probes_unauthenticated(client: TestClient):
    """Health endpoints MUST remain publicly accessible without credentials."""
    res1 = client.get("/api/v1/health")
    assert res1.status_code == 200
    assert res1.json()["status"] == "healthy"

    res2 = client.get("/health")
    assert res2.status_code == 200


def test_unauthenticated_request_to_protected_endpoints_fails_401(client: TestClient):
    """Unauthenticated access to any protected resource must return HTTP 401."""
    protected_urls = [
        ("GET", "/api/v1/statistics/summary"),
        ("GET", "/api/v1/alerts"),
        ("GET", "/api/v1/monitoring/status"),
        ("POST", "/api/v1/monitoring/start"),
        ("POST", "/api/v1/detection"),
        ("GET", "/api/v1/models"),
        ("GET", "/api/v1/users"),
    ]

    for method, url in protected_urls:
        if method == "GET":
            res = client.get(url)
        else:
            res = client.post(url, json={"source": "live", "interface": "eth0"})
        assert res.status_code == 401, f"Expected 401 for {method} {url}, got {res.status_code}"


def test_viewer_role_telemetry_allowed_triage_forbidden(client: TestClient, viewer_headers, mock_viewer_user):
    """Viewer can read dashboards/telemetry but cannot perform triage or control capture."""
    with patch("backend.app.database.repository.UserRepository.get_user_by_id", new_callable=AsyncMock) as mock_auth_user, \
         patch("backend.app.services.audit_service.audit_service.log_event", new_callable=AsyncMock):

        mock_auth_user.return_value = mock_viewer_user.model_dump()

        # 1. Allowed: Read statistics summary
        with patch("backend.app.services.statistics_service.statistics_service.get_dashboard_summary", new_callable=AsyncMock) as mock_stats:
            mock_stats.return_value = {
                "generated_at": datetime.now(timezone.utc),
                "total_events_analyzed": 100,
                "anomalies_detected": 10,
                "anomaly_rate": 0.1,
                "total_alerts": 10,
                "active_alerts": 5,
                "alerts_by_severity": {"CRITICAL": 2, "HIGH": 3, "MEDIUM": 3, "LOW": 2},
                "alerts_by_status": {"OPEN": 5, "ACKNOWLEDGED": 2, "RESOLVED": 2, "DISMISSED": 1},
                "average_risk_score": 75.5,
                "model_status": {},
            }

            res = client.get("/api/v1/statistics/summary", headers=viewer_headers)
            assert res.status_code == 200

        # 2. Allowed: Read monitoring status
        with patch("backend.app.monitoring.manager.monitoring_manager.get_status") as mock_mon_stat:
            mock_mon_stat.return_value = MonitoringStatusResponse(
                running=False,
                active=False,
                source="inactive",
                target="None",
                session_uptime_seconds=0.0,
                packets_captured=0,
                packets_dropped=0,
                capture_rate_pps=0.0,
                total_bytes_captured=0,
                events_generated=0,
                events_queued=0,
                filter_expression="",
                live_interfaces=[],
            )

            res = client.get("/api/v1/monitoring/status", headers=viewer_headers)
            assert res.status_code == 200

        # 3. Forbidden (403): Start monitoring capture
        res = client.post("/api/v1/monitoring/start", json={"source": "live", "interface": "eth0"}, headers=viewer_headers)
        assert res.status_code == 403

        # 4. Forbidden (403): Triage alert acknowledge
        res = client.patch("/api/v1/alerts/alt-12345/acknowledge", json={}, headers=viewer_headers)
        assert res.status_code == 403

        # 5. Forbidden (403): Predict anomaly
        res = client.post("/api/v1/detection", json={"features": {}}, headers=viewer_headers)
        assert res.status_code == 403

        # 6. Forbidden (403): User management
        res = client.get("/api/v1/users", headers=viewer_headers)
        assert res.status_code == 403


def test_analyst_role_triage_allowed_user_mgmt_forbidden(client: TestClient, analyst_headers, mock_analyst_user):
    """Analyst can triage and control capture, but cannot manage users or alter DB indexes."""
    with patch("backend.app.database.repository.UserRepository.get_user_by_id", new_callable=AsyncMock) as mock_auth_user, \
         patch("backend.app.services.audit_service.audit_service.log_event", new_callable=AsyncMock):

        mock_auth_user.return_value = mock_analyst_user.model_dump()

        # 1. Allowed: Triage alert acknowledge
        with patch("backend.app.services.alert_service.alert_service.get_alert", new_callable=AsyncMock) as mock_get_alt, \
             patch("backend.app.services.alert_service.alert_service.acknowledge_alert", new_callable=AsyncMock) as mock_ack:
            mock_get_alt.return_value = {"alert_id": "alt-test-01", "status": "OPEN"}
            mock_ack.return_value = True

            res = client.patch("/api/v1/alerts/alt-test-01/acknowledge", json={}, headers=analyst_headers)
            assert res.status_code == 200
            assert res.json()["success"] is True

        # 2. Allowed: Monitoring controls
        with patch("backend.app.monitoring.manager.monitoring_manager.start", new_callable=AsyncMock) as mock_mon_start:
            mock_mon_start.return_value = MonitoringStatusResponse(
                running=True,
                active=True,
                source="live",
                target="eth0",
                session_uptime_seconds=1.0,
                packets_captured=0,
                packets_dropped=0,
                capture_rate_pps=0.0,
                total_bytes_captured=0,
                events_generated=0,
                events_queued=0,
                filter_expression="",
                live_interfaces=[],
            )

            res = client.post("/api/v1/monitoring/start", json={"source": "live", "interface": "eth0"}, headers=analyst_headers)
            assert res.status_code == 200

        # 3. Forbidden (403): User management list
        res = client.get("/api/v1/users", headers=analyst_headers)
        assert res.status_code == 403

        # 4. Forbidden (403): Provision user
        res = client.post("/api/v1/users", json={"username": "hacker"}, headers=analyst_headers)
        assert res.status_code == 403


def test_admin_role_full_access(client: TestClient, admin_headers, mock_admin_user):
    """Admin has unrestricted access to user management, triage, and telemetry."""
    with patch("backend.app.database.repository.UserRepository.get_user_by_id", new_callable=AsyncMock) as mock_auth_user:
        mock_auth_user.return_value = mock_admin_user.model_dump()

        # 1. Allowed: User management
        with patch("backend.app.database.repository.UserRepository.list_users", new_callable=AsyncMock) as mock_list, \
             patch("backend.app.database.repository.UserRepository.count", new_callable=AsyncMock) as mock_count:
            mock_list.return_value = []
            mock_count.return_value = 0
            res = client.get("/api/v1/users", headers=admin_headers)
            assert res.status_code == 200

        # 2. Allowed: Alert triage
        with patch("backend.app.services.alert_service.alert_service.get_alert", new_callable=AsyncMock) as mock_get_alt, \
             patch("backend.app.services.alert_service.alert_service.acknowledge_alert", new_callable=AsyncMock) as mock_ack:
            mock_get_alt.return_value = {"alert_id": "alt-test-admin", "status": "OPEN"}
            mock_ack.return_value = True

            res = client.patch("/api/v1/alerts/alt-test-admin/acknowledge", json={}, headers=admin_headers)
            assert res.status_code == 200
            assert res.json()["success"] is True
