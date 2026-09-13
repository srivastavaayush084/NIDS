import pytest
from pydantic import ValidationError
from backend.app.models.user import UserDocument
from backend.app.models.network_log import NetworkLogDocument
from backend.app.models.alert import AlertDocument
from backend.app.models.detection_result import DetectionResultDocument
from backend.app.models.system_event import SystemEventDocument
from backend.app.models.audit_log import AuditLogDocument


def test_user_document_validation():
    """Test User document validation for email and fields."""
    user = UserDocument(
        username="sec_analyst",
        email="analyst@zeroday.ai",
        hashed_password="secure_hashed_password",
        role="analyst"
    )
    assert user.username == "sec_analyst"
    assert user.role == "analyst"
    assert user.is_active is True

    # Invalid email should raise ValidationError
    with pytest.raises(ValidationError):
        UserDocument(
            username="bad_user",
            email="not-an-email",
            hashed_password="pw"
        )


def test_network_log_validation():
    """Test Network Log validation for ports and packet numbers."""
    log = NetworkLogDocument(
        source_ip="192.168.1.50",
        destination_ip="10.0.0.1",
        source_port=54321,
        destination_port=443,
        protocol="TCP",
        packet_count=10,
        byte_count=5000,
        flow_duration=1.25,
        features={"byte_rate": 4000.0}
    )
    assert log.source_port == 54321
    assert log.destination_port == 443
    assert log.features["byte_rate"] == 4000.0

    # Invalid port (> 65535) should raise ValidationError
    with pytest.raises(ValidationError):
        NetworkLogDocument(
            source_port=70000
        )


def test_alert_document_validation():
    """Test Alert document validation for status and severity literals."""
    alert = AlertDocument(
        title="Suspicious Outbound Burst",
        description="Uncharacterized beaconing detected",
        severity="HIGH",
        status="new",
        anomaly_score=0.92
    )
    assert alert.severity == "HIGH"
    assert alert.status == "new"
    assert alert.anomaly_score == 0.92

    # Invalid status should raise ValidationError
    with pytest.raises(ValidationError):
        AlertDocument(
            title="Bad Alert",
            description="desc",
            status="invalid_status"
        )

    # Anomaly score > 1.0 should raise ValidationError
    with pytest.raises(ValidationError):
        AlertDocument(
            title="Bad Alert",
            description="desc",
            anomaly_score=1.5
        )


def test_detection_result_validation():
    """Test Detection Result validation."""
    det = DetectionResultDocument(
        model_name="isolation_forest",
        prediction=True,
        anomaly_score=0.88,
        severity="HIGH",
        contributing_features=[{"feature": "dst_bytes", "score": 0.85}],
        explanation="Abnormal byte count deviation"
    )
    assert det.model_name == "isolation_forest"
    assert det.prediction is True
    assert len(det.contributing_features) == 1


def test_system_event_validation():
    """Test System Event document validation."""
    event = SystemEventDocument(
        event_type="DB_CONNECTED",
        level="INFO",
        component="backend.database",
        message="MongoDB client pool connected."
    )
    assert event.event_type == "DB_CONNECTED"
    assert event.level == "INFO"

    # Invalid event level should raise ValidationError
    with pytest.raises(ValidationError):
        SystemEventDocument(
            event_type="TEST",
            level="INVALID_LEVEL",
            message="msg"
        )


def test_audit_log_validation():
    """Test Audit Log document validation."""
    audit = AuditLogDocument(
        user_id="analyst_01",
        action="ALERT_STATUS_UPDATE",
        resource="alerts",
        resource_id="alert_123",
        status="SUCCESS"
    )
    assert audit.action == "ALERT_STATUS_UPDATE"
    assert audit.status == "SUCCESS"

    # Invalid audit status should raise ValidationError
    with pytest.raises(ValidationError):
        AuditLogDocument(
            action="TEST",
            resource="test",
            status="UNKNOWN_STATUS"
        )
