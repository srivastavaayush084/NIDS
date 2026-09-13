from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock


def test_health_check_endpoint(client: TestClient):
    """Test that /api/health returns 200 OK with expected Phase 2 schema structure."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "database" in data
    assert "environment" in data
    assert "timestamp" in data
    assert "version" in data
    assert "services" in data
    assert "api" in data["services"]
    assert "database" in data["services"]
    assert "ml_engine" in data["services"]
    assert "connected" in data["services"]["database"]["details"]


def test_health_check_v1_endpoint(client: TestClient):
    """Test that /api/v1/health alias returns 200 OK."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "database" in data


def test_health_check_degraded_when_db_down(client: TestClient):
    """Verify health endpoint gracefully returns degraded status without crashing when DB is down."""
    with patch(
        "backend.app.api.v1.endpoints.health.check_mongo_health",
        new=AsyncMock(return_value=(False, None, {"status": "disconnected", "connected": False}))
    ):
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"
        assert data["database"] == "disconnected"
        assert data["services"]["database"]["status"] == "disconnected"
