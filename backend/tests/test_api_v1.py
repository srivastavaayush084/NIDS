import pytest
import uuid
from datetime import datetime, timezone
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.auth.dependencies import get_current_user
from backend.app.models.user import UserDocument


@pytest.fixture(autouse=True)
def override_auth_for_api_tests():
    """Ensure standard API integration tests execute with authenticated admin permissions."""
    mock_user = UserDocument(
        id="usr-api-tester",
        user_id="usr-api-tester",
        username="api_tester",
        email="tester@zeroday.ai",
        hashed_password="$2b$12$mockhashedpasswordsample123456789012345678901234567890",
        role="admin",
        is_active=True,
    )
    app.dependency_overrides[get_current_user] = lambda: mock_user
    yield
    app.dependency_overrides.pop(get_current_user, None)


# 26 standard synthetic feature vector representing normal/benign network traffic
SAMPLE_BENIGN_FEATURES = {
    "src_bytes": 150.0,
    "dst_bytes": 350.0,
    "count": 5.0,
    "srv_count": 5.0,
    "serror_rate": 0.0,
    "same_srv_rate": 1.0,
    "diff_srv_rate": 0.0,
    "dst_host_count": 10.0,
    "dst_host_srv_count": 10.0,
    "feat_byte_ratio": 0.428,
    "feat_total_bytes": 500.0,
    "feat_src_byte_rate": 30.0,
    "feat_packet_ratio": 1.0,
    "protocol_type_icmp": 0.0,
    "protocol_type_tcp": 1.0,
    "service_eco_i": 0.0,
    "service_ftp": 0.0,
    "service_ftp_data": 0.0,
    "service_http": 1.0,
    "service_private": 0.0,
    "service_smtp": 0.0,
    "service_ssl_tls": 0.0,
    "service_telnet": 0.0,
    "flag_REJ": 0.0,
    "flag_S0": 0.0,
    "flag_SF": 1.0,
}

# 26 standard synthetic feature vector representing anomalous/attack network traffic
SAMPLE_ATTACK_FEATURES = {
    "src_bytes": 50000.0,
    "dst_bytes": 0.0,
    "count": 500.0,
    "srv_count": 500.0,
    "serror_rate": 1.0,
    "same_srv_rate": 1.0,
    "diff_srv_rate": 0.0,
    "dst_host_count": 255.0,
    "dst_host_srv_count": 1.0,
    "feat_byte_ratio": 50000.0,
    "feat_total_bytes": 50000.0,
    "feat_src_byte_rate": 10000.0,
    "feat_packet_ratio": 0.01,
    "protocol_type_icmp": 0.0,
    "protocol_type_tcp": 1.0,
    "service_eco_i": 0.0,
    "service_ftp": 0.0,
    "service_ftp_data": 0.0,
    "service_http": 0.0,
    "service_private": 1.0,
    "service_smtp": 0.0,
    "service_ssl_tls": 0.0,
    "service_telnet": 0.0,
    "flag_REJ": 0.0,
    "flag_S0": 1.0,
    "flag_SF": 0.0,
}


# =============================================================================
# 1. Health & Status Probe Tests
# =============================================================================

def test_health_v1_endpoint(client: TestClient):
    """Test /api/v1/health returns complete status with models and services."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["healthy", "degraded"]
    assert "database" in data
    assert "services" in data
    assert "api" in data["services"]
    assert "ml_engine" in data["services"]


def test_request_id_and_timing_headers(client: TestClient):
    """Verify X-Request-ID and X-Process-Time headers are present in responses."""
    # Test auto-generated Request ID
    res1 = client.get("/api/v1/health")
    assert "x-request-id" in res1.headers
    assert "x-process-time" in res1.headers
    assert res1.headers["x-request-id"].startswith("req-")

    # Test propagated custom Request ID
    custom_id = "test-custom-trace-12345"
    res2 = client.get("/api/v1/health", headers={"X-Request-ID": custom_id})
    assert res2.headers["x-request-id"] == custom_id


# =============================================================================
# 2. Event Ingestion Tests
# =============================================================================

def test_ingest_single_event(client: TestClient):
    """Test POST /api/v1/events ingests a single network flow record."""
    payload = {
        "source_ip": "192.168.1.50",
        "destination_ip": "10.0.0.1",
        "source_port": 54321,
        "destination_port": 80,
        "protocol": "TCP",
        "dataset_name": "synthetic",
        "features": SAMPLE_BENIGN_FEATURES,
    }
    response = client.post("/api/v1/events", json=payload)
    assert response.status_code == 201
    res_data = response.json()
    assert res_data["success"] is True
    data = res_data["data"]
    assert "event_id" in data
    assert data["event_id"].startswith("evt-")
    assert data["status"] == "stored"
    assert data["source_ip"] == "192.168.1.50"


def test_ingest_batch_events(client: TestClient):
    """Test POST /api/v1/events/batch ingests a batch of network flow records."""
    payload = {
        "source": "suricata_sensor",
        "events": [
            {
                "source_ip": "192.168.1.10",
                "destination_ip": "10.0.0.5",
                "source_port": 50000 + i,
                "destination_port": 443,
                "protocol": "TCP",
                "features": SAMPLE_BENIGN_FEATURES,
            }
            for i in range(5)
        ]
    }
    response = client.post("/api/v1/events/batch", json=payload)
    assert response.status_code == 201
    res_data = response.json()
    assert res_data["success"] is True
    data = res_data["data"]
    assert data["total"] == 5
    assert data["stored"] == 5
    assert len(data["event_ids"]) == 5


def test_ingest_event_validation_error(client: TestClient):
    """Test POST /api/v1/events returns structured 422 on invalid payload."""
    # Out of range port number (must be <= 65535)
    invalid_payload = {
        "source_ip": "192.168.1.50",
        "destination_port": 999999,
        "features": SAMPLE_BENIGN_FEATURES,
    }
    response = client.post("/api/v1/events", json=invalid_payload)
    assert response.status_code == 422
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "VALIDATION_ERROR"
    assert "details" in data["error"]
    assert len(data["error"]["details"]) > 0


# =============================================================================
# 3. ML Detection Pipeline Tests
# =============================================================================

def test_single_event_detection_pipeline(client: TestClient):
    """Test POST /api/v1/detection executes multi-model inference and XAI explanation."""
    payload = {
        "features": SAMPLE_BENIGN_FEATURES,
        "dataset_name": "synthetic",
        "generate_xai": True,
        "flow_context": {
            "source_ip": "192.168.1.100",
            "destination_ip": "10.0.0.1",
            "protocol": "TCP",
        }
    }
    response = client.post("/api/v1/detection", json=payload)
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["success"] is True
    data = res_data["data"]

    assert "detection_id" in data
    assert data["detection_id"].startswith("det-")
    assert "is_anomaly" in data
    assert "risk_score" in data
    assert 0.0 <= data["risk_score"] <= 100.0
    assert "severity" in data
    assert data["severity"] in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    assert "prediction" in data
    assert data["prediction"] in ["normal", "attack"]
    assert "models" in data
    
    model_names = [m["name"] for m in data["models"]]
    assert "isolation_forest" in model_names
    assert "autoencoder" in model_names
    assert "random_forest" in model_names

    assert "processing_time_ms" in data

    # Verify XAI explanation if generated
    if data.get("explanation"):
        assert "summary" in data["explanation"]


def test_single_event_attack_detection(client: TestClient):
    """Test POST /api/v1/detection flags attack traffic with high risk and alert."""
    payload = {
        "features": SAMPLE_ATTACK_FEATURES,
        "dataset_name": "synthetic",
        "generate_xai": True,
        "flow_context": {
            "source_ip": "45.33.32.156",
            "destination_ip": "10.0.0.20",
            "source_port": 61234,
            "destination_port": 4444,
            "protocol": "TCP",
        }
    }
    response = client.post("/api/v1/detection", json=payload)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["risk_score"] >= 0.0
    assert "models" in data


def test_batch_detection_pipeline(client: TestClient):
    """Test POST /api/v1/detection/batch executes batch analysis."""
    events = [
        {"features": SAMPLE_BENIGN_FEATURES, "source_ip": "192.168.1.1", "destination_port": 80},
        {"features": SAMPLE_ATTACK_FEATURES, "source_ip": "45.33.32.1", "destination_port": 4444},
        {"features": SAMPLE_BENIGN_FEATURES, "source_ip": "192.168.1.2", "destination_port": 443},
    ]
    payload = {
        "events": events,
        "dataset_name": "synthetic",
        "generate_xai": False,
    }
    response = client.post("/api/v1/detection/batch", json=payload)
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["success"] is True
    data = res_data["data"]

    assert "results" in data
    assert len(data["results"]) == 3
    assert "total" in data
    assert data["total"] == 3
    assert "anomalies" in data
    assert "successful" in data
    assert data["successful"] == 3


def test_sequence_detection_pipeline(client: TestClient):
    """Test POST /api/v1/detection/sequence performs temporal window LSTM detection."""
    # Sequence of 3 consecutive event feature vectors matching calibrated synthetic model seq_len
    seq = [SAMPLE_BENIGN_FEATURES for _ in range(3)]
    payload = {
        "sequence": seq,
        "dataset_name": "synthetic",
        "generate_xai": True,
        "flow_context": {
            "source_ip": "192.168.1.100",
            "destination_ip": "10.0.0.1",
        }
    }
    response = client.post("/api/v1/detection/sequence", json=payload)
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["success"] is True
    data = res_data["data"]

    assert "detection_id" in data
    assert "sequence_length" in data
    assert data["sequence_length"] == 3
    assert "reconstruction_error" in data
    assert "is_anomaly" in data
    assert "risk_score" in data


def test_query_detection_history_and_detail(client: TestClient):
    """Test GET /api/v1/detection lists results and GET /api/v1/detection/{id} fetches single record."""
    # 1. Ingest/Detect an event to ensure at least one record exists
    det_res = client.post("/api/v1/detection", json={
        "features": SAMPLE_BENIGN_FEATURES,
        "dataset_name": "synthetic",
        "generate_xai": False,
    })
    det_id = det_res.json()["data"]["detection_id"]

    # 2. Query detection history
    list_res = client.get("/api/v1/detection?page=1&page_size=10")
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert list_data["success"] is True
    assert "data" in list_data
    assert "pagination" in list_data
    assert list_data["pagination"]["page"] == 1

    # 3. Query specific detection by ID
    get_res = client.get(f"/api/v1/detection/{det_id}")
    assert get_res.status_code == 200
    get_data = get_res.json()
    assert get_data["success"] is True
    assert get_data["data"]["detection_id"] == det_id


def test_get_nonexistent_detection_404(client: TestClient):
    """Test GET /api/v1/detection/nonexistent returns 404."""
    response = client.get("/api/v1/detection/det-nonexistent-id-999")
    assert response.status_code == 404
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "HTTP_404"


# =============================================================================
# 4. Security Alerts Lifecycle Tests
# =============================================================================

def test_alerts_listing(client: TestClient):
    """Test GET /api/v1/alerts lists security alerts with pagination."""
    response = client.get("/api/v1/alerts?page=1&page_size=20")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "data" in data
    assert "pagination" in data
    assert data["pagination"]["page"] == 1


def test_alert_lifecycle_transitions(client: TestClient):
    """Test alert lifecycle: detection -> alert generation -> acknowledge -> resolve with audit checks."""
    # 1. Trigger an attack detection to generate and persist a live security alert
    attack_payload = {
        "features": SAMPLE_ATTACK_FEATURES,
        "dataset_name": "synthetic",
        "generate_xai": True,
        "flow_context": {
            "source_ip": f"198.51.100.{uuid.uuid4().int % 250 + 1}",
            "destination_ip": "10.0.0.15",
            "source_port": 54321,
            "destination_port": 443,
            "protocol": "TCP",
        }
    }
    det_res = client.post("/api/v1/detection", json=attack_payload)
    assert det_res.status_code == 200
    det_data = det_res.json()["data"]
    
    assert det_data.get("alert") is not None
    assert det_data["alert"]["created"] is True
    alert_id = det_data["alert"]["alert_id"]
    assert alert_id is not None

    # 2. Get Alert Details via GET /api/v1/alerts/{alert_id}
    detail_res = client.get(f"/api/v1/alerts/{alert_id}")
    assert detail_res.status_code == 200
    assert detail_res.json()["data"]["alert_id"] == alert_id
    assert detail_res.json()["data"]["status"] == "OPEN"

    # 3. Acknowledge Alert via PATCH /api/v1/alerts/{alert_id}/acknowledge
    ack_res = client.patch(
        f"/api/v1/alerts/{alert_id}/acknowledge",
        json={"user_id": "lead_soc_analyst"}
    )
    assert ack_res.status_code == 200
    ack_data = ack_res.json()
    assert ack_data["success"] is True
    assert ack_data["data"]["status"] == "ACKNOWLEDGED"

    # 4. Resolve Alert via PATCH /api/v1/alerts/{alert_id}/resolve
    res_res = client.patch(
        f"/api/v1/alerts/{alert_id}/resolve",
        json={
            "resolution_note": "Host isolated and malicious beaconing terminated successfully.",
            "user_id": "lead_soc_analyst"
        }
    )
    assert res_res.status_code == 200
    res_data = res_res.json()
    assert res_data["success"] is True
    assert res_data["data"]["status"] == "RESOLVED"
    assert res_data["data"]["resolution_note"] == "Host isolated and malicious beaconing terminated successfully."

    # 5. Verify terminal state transition guard (cannot acknowledge a resolved alert)
    bad_ack = client.patch(
        f"/api/v1/alerts/{alert_id}/acknowledge",
        json={"user_id": "other_analyst"}
    )
    assert bad_ack.status_code == 409


def test_dismiss_alert_lifecycle(client: TestClient):
    """Test dismissing an alert with dismissal reasons."""
    # 1. Trigger an attack detection to generate an alert
    attack_payload = {
        "features": SAMPLE_ATTACK_FEATURES,
        "dataset_name": "synthetic",
        "generate_xai": False,
        "flow_context": {
            "source_ip": f"192.168.1.{uuid.uuid4().int % 250 + 1}",
            "destination_ip": "10.0.0.50",
            "source_port": 61234,
            "destination_port": 8080,
            "protocol": "TCP",
        }
    }
    det_res = client.post("/api/v1/detection", json=attack_payload)
    assert det_res.status_code == 200
    det_data = det_res.json()["data"]
    assert det_data.get("alert") is not None
    alert_id = det_data["alert"]["alert_id"]

    # 2. Dismiss Alert via PATCH /api/v1/alerts/{alert_id}/dismiss
    dismiss_res = client.patch(
        f"/api/v1/alerts/{alert_id}/dismiss",
        json={
            "dismissal_reason": "Verified authorized penetration test from secops subnet.",
            "user_id": "soc_lead"
        }
    )
    assert dismiss_res.status_code == 200
    assert dismiss_res.json()["data"]["status"] == "DISMISSED"


def test_alert_not_found_404(client: TestClient):
    """Test 404 response on unknown alert ID."""
    response = client.get("/api/v1/alerts/alt-nonexistent-id-999")
    assert response.status_code == 404
    assert response.json()["success"] is False


# =============================================================================
# 5. ML Models Registry & Metadata Tests
# =============================================================================

def test_models_listing(client: TestClient):
    """Test GET /api/v1/models returns catalog of all registered models."""
    response = client.get("/api/v1/models")
    assert response.status_code == 200
    data = response.json()
    assert "models" in data
    assert data["total"] >= 5
    
    model_ids = [m["model_id"] for m in data["models"]]
    assert "isolation_forest" in model_ids
    assert "autoencoder" in model_ids
    assert "lstm_autoencoder" in model_ids
    assert "random_forest" in model_ids
    assert "ensemble" in model_ids

    # Verify safe attributes (no internal file paths exposed in top fields)
    for model in data["models"]:
        assert "model_id" in model
        assert "display_name" in model
        assert "model_type" in model
        assert "framework" in model
        assert "version" in model
        assert "is_trained" in model


def test_get_individual_model_details(client: TestClient):
    """Test GET /api/v1/models/{model_name} returns detailed info for valid model."""
    for model_name in ["isolation_forest", "autoencoder", "lstm_autoencoder", "random_forest", "ensemble"]:
        response = client.get(f"/api/v1/models/{model_name}")
        assert response.status_code == 200
        data = response.json()
        assert data["model_id"] == model_name
        assert data["display_name"] is not None
        assert data["model_type"] is not None


def test_get_nonexistent_model_404(client: TestClient):
    """Test GET /api/v1/models/{model_name} returns 404 for unknown model."""
    response = client.get("/api/v1/models/quantum_neural_net_v99")
    assert response.status_code == 404
    data = response.json()
    assert data["success"] is False
    assert "not found" in data["error"]["message"].lower()


# =============================================================================
# 6. System Statistics & Metrics Tests
# =============================================================================

def test_dashboard_summary_statistics(client: TestClient):
    """Test GET /api/v1/statistics/summary returns aggregate telemetry."""
    response = client.get("/api/v1/statistics/summary")
    assert response.status_code == 200
    data = response.json()

    assert "total_detections" in data
    assert "total_anomalies" in data
    assert "anomaly_rate" in data
    assert "total_alerts" in data
    assert "alerts_by_status" in data
    assert "alerts_by_severity" in data
    assert "average_risk_score" in data
    assert "active_models_count" in data


def test_alert_statistics_breakdown(client: TestClient):
    """Test GET /api/v1/statistics/alerts returns alert analytics and top targets."""
    response = client.get("/api/v1/statistics/alerts")
    assert response.status_code == 200
    data = response.json()

    assert "total_alerts" in data
    assert "open_alerts" in data
    assert "severity_breakdown" in data
    assert "status_breakdown" in data
    assert "top_source_ips" in data
    assert "top_destination_ips" in data


def test_model_evaluation_statistics(client: TestClient):
    """Test GET /api/v1/statistics/models returns Phase 8 comparison metrics."""
    response = client.get("/api/v1/statistics/models")
    assert response.status_code == 200
    data = response.json()

    assert "models" in data
    assert len(data["models"]) >= 8  # At least 4 models x 2 evaluation types
    assert "generated_at" in data

    # Check that known attacks and unseen zero-day benchmarks are present
    eval_types = {m["evaluation_type"] for m in data["models"]}
    assert "known_attacks" in eval_types
    assert "unseen_zero_day" in eval_types

    for item in data["models"]:
        assert "model_name" in item
        assert "precision" in item
        assert "recall" in item
        assert "f1_score" in item
        assert "roc_auc" in item
        assert "latency_ms" in item
