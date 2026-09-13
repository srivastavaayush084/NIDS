import pytest
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
import numpy as np

from backend.app.ml.ensemble.schemas import (
    ModelContribution,
    ModelAgreement,
    LatencyBreakdown,
    EnsemblePrediction,
)
from backend.app.ml.explainability.schemas import (
    FeatureContribution,
    EnsembleExplanation,
    ModelExplanation,
)
from backend.app.alerts.schemas import (
    AlertDocument,
    AlertEventResult,
    AlertFilterParams,
    AlertPriority,
    AlertSeverity,
    AlertStatus,
    DeduplicationInfo,
    EnsembleEvidence,
    ModelEvidenceItem,
    NetworkEndpoint,
    XAIEvidence,
)
from backend.app.alerts.severity import map_severity_to_priority, evaluate_alert_severity
from backend.app.alerts.rules import AlertRuleEngine
from backend.app.alerts.deduplication import AlertDeduplicator
from backend.app.alerts.formatter import AlertFormatter
from backend.app.alerts.engine import AlertEngine
from backend.app.services.alert_service import AlertService
from backend.app.schemas.alert import AlertCreate


# =============================================================================
# Helper Fixtures
# =============================================================================

@pytest.fixture
def sample_high_ensemble_prediction() -> EnsemblePrediction:
    """Creates a sample high-risk ensemble prediction."""
    contributions = {
        "isolation_forest": ModelContribution(
            model_name="isolation_forest",
            model_type="unsupervised",
            native_score=0.85,
            normalized_score=82.0,
            decision_threshold=0.5,
            is_anomaly=True,
            prediction="attack",
            configured_weight=0.25,
            effective_weight=0.25,
            latency_ms=1.5,
            is_available=True,
        ),
        "autoencoder": ModelContribution(
            model_name="autoencoder",
            model_type="unsupervised",
            native_score=0.12,
            normalized_score=78.0,
            decision_threshold=0.05,
            is_anomaly=True,
            prediction="attack",
            configured_weight=0.25,
            effective_weight=0.25,
            latency_ms=2.0,
            is_available=True,
        ),
        "lstm_autoencoder": ModelContribution(
            model_name="lstm_autoencoder",
            model_type="sequential",
            native_score=0.18,
            normalized_score=85.0,
            decision_threshold=0.08,
            is_anomaly=True,
            prediction="attack",
            configured_weight=0.25,
            effective_weight=0.25,
            latency_ms=4.2,
            is_available=True,
        ),
        "random_forest": ModelContribution(
            model_name="random_forest",
            model_type="supervised",
            native_score=0.92,
            normalized_score=88.0,
            decision_threshold=0.5,
            is_anomaly=True,
            prediction="attack",
            configured_weight=0.25,
            effective_weight=0.25,
            latency_ms=1.1,
            is_available=True,
        ),
    }

    return EnsemblePrediction(
        prediction="attack",
        is_anomaly=True,
        risk_score=83.25,
        severity="CRITICAL",
        decision_threshold=50.0,
        reliability_score=1.0,
        agreement=ModelAgreement(
            models_total=4,
            models_available=4,
            models_anomalous=4,
            models_normal=0,
            agreement_ratio=1.0,
            disagreement_ratio=0.0,
            consensus_prediction="attack",
        ),
        contributions=contributions,
        participating_models=["isolation_forest", "autoencoder", "lstm_autoencoder", "random_forest"],
        missing_models=[],
        latency=LatencyBreakdown(total_ms=8.8),
    )


@pytest.fixture
def sample_flow_context() -> Dict[str, Any]:
    """Sample network flow context."""
    return {
        "source_ip": "192.168.1.105",
        "destination_ip": "10.0.0.1",
        "source_port": 49152,
        "destination_port": 443,
        "protocol": "TCP",
    }


@pytest.fixture
def sample_xai_explanation() -> EnsembleExplanation:
    """Creates a sample XAI ensemble explanation."""
    feat_contribs = [
        FeatureContribution(
            feature_name="src_bytes",
            contribution=0.45,
            absolute_contribution=0.45,
            rank=1,
            direction="increases_risk",
        ),
        FeatureContribution(
            feature_name="dst_host_count",
            contribution=0.32,
            absolute_contribution=0.32,
            rank=2,
            direction="increases_risk",
        ),
        FeatureContribution(
            feature_name="serror_rate",
            contribution=0.18,
            absolute_contribution=0.18,
            rank=3,
            direction="increases_risk",
        ),
    ]

    return EnsembleExplanation(
        explanation_id="exp-test-001",
        prediction="attack",
        is_anomaly=True,
        risk_score=83.25,
        severity="CRITICAL",
        reliability_score=1.0,
        fused_feature_contributions=feat_contribs,
        summary="High anomalous deviation driven by elevated src_bytes and dst_host_count.",
    )


class MockAlertRepository:
    """In-memory alert repository mock for testing lifecycle and deduplication."""

    def __init__(self):
        self.docs: Dict[str, Dict[str, Any]] = {}

    async def find_one(self, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        for d in self.docs.values():
            match = True
            for k, v in query.items():
                if d.get(k) != v:
                    match = False
                    break
            if match:
                return d
        return None

    async def find_by_alert_id(self, alert_id: str) -> Optional[Dict[str, Any]]:
        return self.docs.get(alert_id)

    async def find_active_by_fingerprint(self, fingerprint: str) -> Optional[Dict[str, Any]]:
        matches = []
        for d in self.docs.values():
            dedup = d.get("deduplication", {})
            if dedup.get("fingerprint") == fingerprint and d.get("status") in ["OPEN", "ACKNOWLEDGED", "new", "acknowledged"]:
                matches.append(d)
        if matches:
            matches.sort(key=lambda x: x.get("created_at", datetime.min), reverse=True)
            return matches[0]
        return None

    async def insert_one(self, document: Dict[str, Any]) -> Optional[str]:
        alert_id = document.get("alert_id") or f"alt-mock-{len(self.docs)+1}"
        document["alert_id"] = alert_id
        document["_id"] = alert_id
        self.docs[alert_id] = document
        return alert_id

    async def increment_occurrence(
        self,
        alert_id: str,
        timestamp: Optional[datetime] = None,
        latest_risk_score: Optional[float] = None,
    ) -> bool:
        if alert_id not in self.docs:
            return False
        d = self.docs[alert_id]
        now = timestamp or datetime.now(timezone.utc)
        d["deduplication"]["occurrence_count"] = d["deduplication"].get("occurrence_count", 1) + 1
        d["deduplication"]["last_seen"] = now
        d["updated_at"] = now
        if latest_risk_score is not None:
            d["risk_score"] = max(d.get("risk_score", 0.0), latest_risk_score)
        return True

    async def update_status(
        self,
        alert_id: str,
        status: str,
        assigned_to: Optional[str] = None,
        resolution_note: Optional[str] = None,
        dismissal_reason: Optional[str] = None,
    ) -> bool:
        if alert_id not in self.docs:
            return False
        d = self.docs[alert_id]
        d["status"] = status
        d["updated_at"] = datetime.now(timezone.utc)
        if assigned_to is not None:
            d["assigned_to"] = assigned_to
        if resolution_note is not None:
            d["resolution_note"] = resolution_note
        if dismissal_reason is not None:
            d["dismissal_reason"] = dismissal_reason
        return True

    async def find_many(
        self,
        query: Optional[Dict[str, Any]] = None,
        limit: int = 100,
        skip: int = 0,
        sort: Optional[List[tuple]] = None,
    ) -> List[Dict[str, Any]]:
        results = list(self.docs.values())
        if query:
            filtered = []
            for d in results:
                match = True
                for k, v in query.items():
                    if k == "severity" and d.get("severity") != v:
                        match = False
                    elif k == "status" and d.get("status") != v:
                        match = False
                    elif k == "source.ip" and d.get("source", {}).get("ip") != v:
                        match = False
                    elif k == "risk_score" and isinstance(v, dict) and "$gte" in v:
                        if d.get("risk_score", 0.0) < v["$gte"]:
                            match = False
                if match:
                    filtered.append(d)
            results = filtered
        return results[skip : skip + limit]

    async def count(self, query: Optional[Dict[str, Any]] = None) -> int:
        docs = await self.find_many(query, limit=10000)
        return len(docs)


class MockAuditLogRepository:
    """In-memory audit repository mock."""

    def __init__(self):
        self.logs: List[Dict[str, Any]] = []

    async def insert_one(self, document: Dict[str, Any]) -> Optional[str]:
        self.logs.append(document)
        return str(len(self.logs))


# =============================================================================
# Unit Tests: Severity & Priority
# =============================================================================

class TestAlertSeverityAndPriority:
    def test_severity_to_priority_mapping(self):
        assert map_severity_to_priority("LOW") == "LOW"
        assert map_severity_to_priority("MEDIUM") == "MEDIUM"
        assert map_severity_to_priority("HIGH") == "HIGH"
        assert map_severity_to_priority("CRITICAL") == "URGENT"

    def test_evaluate_alert_severity(self):
        assert evaluate_alert_severity(10.0) == "LOW"
        assert evaluate_alert_severity(35.0) == "MEDIUM"
        assert evaluate_alert_severity(65.0) == "HIGH"
        assert evaluate_alert_severity(85.0) == "CRITICAL"


# =============================================================================
# Unit Tests: Rule Engine
# =============================================================================

class TestAlertRuleEngine:
    def test_rule_engine_defaults_allow_high_risk(self, sample_high_ensemble_prediction):
        engine = AlertRuleEngine()
        should_alert, reason, severity = engine.should_generate_alert(sample_high_ensemble_prediction)
        assert should_alert is True
        assert reason == "alert_criteria_satisfied"
        assert severity == "CRITICAL"

    def test_rule_engine_global_disable(self, sample_high_ensemble_prediction):
        engine = AlertRuleEngine(alerts_enabled=False)
        should_alert, reason, severity = engine.should_generate_alert(sample_high_ensemble_prediction)
        assert should_alert is False
        assert reason == "alerts_disabled_globally"

    def test_rule_engine_severity_disable(self, sample_high_ensemble_prediction):
        engine = AlertRuleEngine(critical_enabled=False)
        should_alert, reason, severity = engine.should_generate_alert(sample_high_ensemble_prediction)
        assert should_alert is False
        assert reason == "severity_critical_disabled"

    def test_rule_engine_min_risk_threshold(self, sample_high_ensemble_prediction):
        engine = AlertRuleEngine(min_risk_score=90.0)
        should_alert, reason, severity = engine.should_generate_alert(sample_high_ensemble_prediction)
        assert should_alert is False
        assert reason == "risk_score_below_minimum_threshold"

    def test_rule_engine_anomaly_flag_requirement(self, sample_high_ensemble_prediction):
        sample_high_ensemble_prediction.is_anomaly = False
        engine = AlertRuleEngine(require_anomaly_flag=True)
        should_alert, reason, severity = engine.should_generate_alert(sample_high_ensemble_prediction)
        assert should_alert is False
        assert reason == "ensemble_prediction_is_normal"

    def test_rule_engine_agreement_ratio_threshold(self, sample_high_ensemble_prediction):
        engine = AlertRuleEngine(min_agreement_ratio=0.75)
        should_alert, reason, severity = engine.should_generate_alert(sample_high_ensemble_prediction)
        assert should_alert is True

        sample_high_ensemble_prediction.agreement.agreement_ratio = 0.50
        should_alert, reason, severity = engine.should_generate_alert(sample_high_ensemble_prediction)
        assert should_alert is False
        assert reason == "model_agreement_below_required_threshold"


# =============================================================================
# Unit Tests: Deduplication & Fingerprinting
# =============================================================================

class TestAlertDeduplication:
    def test_fingerprint_determinism(self):
        fp1 = AlertDeduplicator.generate_fingerprint(
            source_ip="192.168.1.50",
            destination_ip="10.0.0.5",
            source_port=54321,
            destination_port=80,
            protocol="TCP",
            alert_type="network_anomaly",
        )
        fp2 = AlertDeduplicator.generate_fingerprint(
            source_ip="192.168.1.50",
            destination_ip="10.0.0.5",
            source_port=54321,
            destination_port=80,
            protocol="TCP",
            alert_type="network_anomaly",
        )
        assert fp1 == fp2
        assert len(fp1) == 64  # SHA-256 hex string

    def test_fingerprint_timestamp_independence(self):
        # Two calls at different times must yield identical fingerprints for identical flows
        fp1 = AlertDeduplicator.generate_fingerprint(
            source_ip="10.1.1.1", destination_ip="10.1.1.2", source_port=1000, destination_port=22
        )
        fp2 = AlertDeduplicator.generate_fingerprint(
            source_ip="10.1.1.1", destination_ip="10.1.1.2", source_port=1000, destination_port=22
        )
        assert fp1 == fp2

    def test_fingerprint_divergence_for_different_endpoints(self):
        fp_base = AlertDeduplicator.generate_fingerprint(
            source_ip="10.1.1.1", destination_ip="10.1.1.2", source_port=1000, destination_port=22
        )
        fp_diff_port = AlertDeduplicator.generate_fingerprint(
            source_ip="10.1.1.1", destination_ip="10.1.1.2", source_port=1000, destination_port=80
        )
        fp_diff_ip = AlertDeduplicator.generate_fingerprint(
            source_ip="10.1.1.99", destination_ip="10.1.1.2", source_port=1000, destination_port=22
        )
        assert fp_base != fp_diff_port
        assert fp_base != fp_diff_ip

    def test_cooldown_window_evaluation(self):
        dedup = AlertDeduplicator(window_seconds=300)
        now = datetime.now(timezone.utc)

        # 100 seconds ago -> within cooldown
        recent_time = now - timedelta(seconds=100)
        assert dedup.is_within_cooldown(recent_time, current_time=now) is True

        # 400 seconds ago -> outside cooldown
        old_time = now - timedelta(seconds=400)
        assert dedup.is_within_cooldown(old_time, current_time=now) is False

    def test_cooldown_timezone_awareness(self):
        dedup = AlertDeduplicator(window_seconds=300)
        now_naive = datetime.now().replace(tzinfo=None)  # timezone naive
        seen_naive = now_naive - timedelta(seconds=60)
        # Should gracefully handle naive timestamps without throwing TypeError
        assert dedup.is_within_cooldown(seen_naive, current_time=now_naive) is True


# =============================================================================
# Unit Tests: Formatter
# =============================================================================

class TestAlertFormatter:
    def test_format_title_severities(self, sample_high_ensemble_prediction):
        # Critical with high consensus
        title_crit = AlertFormatter.format_title("CRITICAL", sample_high_ensemble_prediction)
        assert "Critical" in title_crit

        # High severity
        title_high = AlertFormatter.format_title("HIGH", sample_high_ensemble_prediction)
        assert "High-Risk" in title_high

        # Medium severity
        title_med = AlertFormatter.format_title("MEDIUM", sample_high_ensemble_prediction)
        assert "Elevated" in title_med

        # Low severity
        title_low = AlertFormatter.format_title("LOW", sample_high_ensemble_prediction)
        assert "Low-Risk" in title_low

    def test_format_description_structure(self, sample_high_ensemble_prediction, sample_xai_explanation):
        desc = AlertFormatter.format_description(
            severity="CRITICAL",
            prediction=sample_high_ensemble_prediction,
            source_ip="192.168.1.105",
            dest_ip="10.0.0.1",
            protocol="TCP",
            xai_evidence=XAIEvidence(
                summary=sample_xai_explanation.summary,
                top_features=[fc.model_dump() for fc in sample_xai_explanation.fused_feature_contributions],
                is_available=True,
            ),
        )
        assert "192.168.1.105" in desc
        assert "10.0.0.1" in desc
        assert "83.2/100.0" in desc or "83.3/100.0" in desc
        assert "Model consensus: 4 of 4" in desc
        assert "Explainability Analysis" in desc
        assert "src_bytes" in desc

    def test_format_description_length_limit(self, sample_high_ensemble_prediction):
        desc = AlertFormatter.format_description(
            severity="HIGH",
            prediction=sample_high_ensemble_prediction,
            max_length=80,
        )
        assert len(desc) <= 80
        assert desc.endswith("...")


# =============================================================================
# Unit Tests: Alert Engine Orchestration
# =============================================================================

class TestAlertEngine:
    def test_alert_engine_build_critical_alert(self, sample_high_ensemble_prediction, sample_xai_explanation, sample_flow_context):
        engine = AlertEngine()
        should_alert, doc, reason, severity, fp = engine.evaluate_and_build_alert(
            prediction=sample_high_ensemble_prediction,
            flow_context=sample_flow_context,
            explanation=sample_xai_explanation,
            detection_result_id="det-12345",
        )

        assert should_alert is True
        assert doc is not None
        assert doc.severity == "CRITICAL"
        assert doc.priority == "URGENT"
        assert doc.status == "OPEN"
        assert doc.risk_score == pytest.approx(83.25, 0.01)
        assert doc.detection_result_id == "det-12345"
        assert doc.source.ip == "192.168.1.105"
        assert doc.source.port == 49152
        assert doc.destination.ip == "10.0.0.1"
        assert doc.destination.port == 443
        assert len(doc.model_evidence) == 4
        assert doc.ensemble.agreement_ratio == 1.0
        assert doc.explanation is not None
        assert doc.explanation.is_available is True
        assert len(doc.explanation.top_features) == 3
        assert doc.deduplication.occurrence_count == 1
        assert doc.deduplication.fingerprint == fp

    def test_alert_engine_with_model_explanation(self, sample_high_ensemble_prediction, sample_flow_context):
        engine = AlertEngine()
        model_exp = ModelExplanation(
            model_name="random_forest",
            prediction="attack",
            is_anomaly=True,
            decision_threshold=50.0,
            explanation_method="shap_tree",
            sample_index=0,
            risk_score=88.0,
            severity="CRITICAL",
            feature_contributions=[
                FeatureContribution(feature_name="count", contribution=0.5, absolute_contribution=0.5, rank=1, direction="increases_risk")
            ],
            summary="High tree activation on count feature.",
        )
        should_alert, doc, reason, severity, fp = engine.evaluate_and_build_alert(
            prediction=sample_high_ensemble_prediction,
            flow_context=sample_flow_context,
            explanation=model_exp,
        )
        assert should_alert is True
        assert doc.explanation is not None
        assert doc.explanation.is_available is True
        assert doc.explanation.top_features[0]["feature_name"] == "count"

    def test_alert_engine_xai_resilience_on_none(self, sample_high_ensemble_prediction, sample_flow_context):
        engine = AlertEngine()
        should_alert, doc, reason, severity, fp = engine.evaluate_and_build_alert(
            prediction=sample_high_ensemble_prediction,
            flow_context=sample_flow_context,
            explanation=None,
        )
        assert should_alert is True
        assert doc is not None
        assert doc.explanation is None


# =============================================================================
# Integration Tests: AlertService Lifecycle, Deduplication & Audit Logs
# =============================================================================

@pytest.mark.asyncio
class TestAlertServiceIntegration:
    async def test_alert_service_create_new_alert(self, sample_high_ensemble_prediction, sample_xai_explanation, sample_flow_context):
        mock_alert_repo = MockAlertRepository()
        mock_audit_repo = MockAuditLogRepository()
        service = AlertService(
            alert_repo=mock_alert_repo,
            audit_repo=mock_audit_repo,
            alert_engine=AlertEngine(),
        )

        result = await service.process_detection_result(
            prediction=sample_high_ensemble_prediction,
            flow_context=sample_flow_context,
            explanation=sample_xai_explanation,
            detection_result_id="det-test-01",
        )

        assert result.alert_created is True
        assert result.deduplicated is False
        assert result.alert_id is not None
        assert result.severity == "CRITICAL"
        assert result.priority == "URGENT"
        assert result.occurrence_count == 1
        assert result.xai_available is True

        # Check repository state
        stored_doc = await mock_alert_repo.find_by_alert_id(result.alert_id)
        assert stored_doc is not None
        assert stored_doc["status"] == "OPEN"

        # Check audit log state
        assert len(mock_audit_repo.logs) == 1
        assert mock_audit_repo.logs[0]["action"] == "ALERT_CREATED"
        assert mock_audit_repo.logs[0]["resource"] == result.alert_id

    async def test_alert_service_deduplication_in_cooldown(self, sample_high_ensemble_prediction, sample_flow_context):
        mock_alert_repo = MockAlertRepository()
        mock_audit_repo = MockAuditLogRepository()
        service = AlertService(
            alert_repo=mock_alert_repo,
            audit_repo=mock_audit_repo,
            alert_engine=AlertEngine(),
        )

        # 1. First detection event -> creates alert
        res1 = await service.process_detection_result(
            prediction=sample_high_ensemble_prediction,
            flow_context=sample_flow_context,
        )
        assert res1.alert_created is True
        assert res1.occurrence_count == 1
        orig_alert_id = res1.alert_id

        # 2. Second detection event for identical flow 10 seconds later -> deduplicated
        res2 = await service.process_detection_result(
            prediction=sample_high_ensemble_prediction,
            flow_context=sample_flow_context,
        )
        assert res2.alert_created is False
        assert res2.deduplicated is True
        assert res2.alert_id == orig_alert_id
        assert res2.occurrence_count == 2

        # Check repository occurrence count updated
        stored_doc = await mock_alert_repo.find_by_alert_id(orig_alert_id)
        assert stored_doc["deduplication"]["occurrence_count"] == 2

        # Check audit logs (1 created, 1 deduplicated)
        assert len(mock_audit_repo.logs) == 2
        assert mock_audit_repo.logs[1]["action"] == "ALERT_DEDUPLICATED"

    async def test_alert_service_lifecycle_transitions(self, sample_high_ensemble_prediction, sample_flow_context):
        mock_alert_repo = MockAlertRepository()
        mock_audit_repo = MockAuditLogRepository()
        service = AlertService(
            alert_repo=mock_alert_repo,
            audit_repo=mock_audit_repo,
        )

        # Create alert
        res = await service.process_detection_result(
            prediction=sample_high_ensemble_prediction,
            flow_context=sample_flow_context,
        )
        alert_id = res.alert_id

        # 1. Acknowledge Alert
        ack_success = await service.acknowledge_alert(alert_id=alert_id, user_id="analyst_alice")
        assert ack_success is True
        doc_ack = await mock_alert_repo.find_by_alert_id(alert_id)
        assert doc_ack["status"] == "ACKNOWLEDGED"
        assert doc_ack["assigned_to"] == "analyst_alice"

        # 2. Resolve Alert
        res_success = await service.resolve_alert(
            alert_id=alert_id,
            resolution_note="Isolated malicious host and updated perimeter firewall rules.",
            user_id="analyst_alice",
        )
        assert res_success is True
        doc_res = await mock_alert_repo.find_by_alert_id(alert_id)
        assert doc_res["status"] == "RESOLVED"
        assert doc_res["resolution_note"] == "Isolated malicious host and updated perimeter firewall rules."

        # 3. Dismiss Alert test on a new alert
        res_dismiss_test = await service.process_detection_result(
            prediction=sample_high_ensemble_prediction,
            flow_context={"source_ip": "10.0.0.99", "destination_ip": "10.0.0.1"},
        )
        new_alert_id = res_dismiss_test.alert_id
        dismiss_success = await service.dismiss_alert(
            alert_id=new_alert_id,
            dismissal_reason="Known vulnerability scanner scheduled run.",
            user_id="analyst_bob",
        )
        assert dismiss_success is True
        doc_dismiss = await mock_alert_repo.find_by_alert_id(new_alert_id)
        assert doc_dismiss["status"] == "DISMISSED"
        assert doc_dismiss["dismissal_reason"] == "Known vulnerability scanner scheduled run."

    async def test_alert_service_query_filtering(self, sample_high_ensemble_prediction):
        mock_alert_repo = MockAlertRepository()
        service = AlertService(alert_repo=mock_alert_repo)

        # Seed two alerts
        await service.process_detection_result(
            prediction=sample_high_ensemble_prediction,
            flow_context={"source_ip": "192.168.1.10"},
        )
        await service.process_detection_result(
            prediction=sample_high_ensemble_prediction,
            flow_context={"source_ip": "192.168.1.20"},
        )

        # Query all
        res_all = await service.query_alerts(AlertFilterParams(limit=10))
        assert res_all["total"] == 2
        assert len(res_all["alerts"]) == 2

        # Filter by source IP
        res_filtered = await service.query_alerts(AlertFilterParams(source_ip="192.168.1.10"))
        assert res_filtered["total"] == 1
        assert res_filtered["alerts"][0]["source"]["ip"] == "192.168.1.10"

    async def test_alert_service_legacy_compatibility(self):
        mock_alert_repo = MockAlertRepository()
        service = AlertService(alert_repo=mock_alert_repo)

        # Test legacy create_alert
        legacy_create = AlertCreate(
            title="Legacy Probe Alert",
            description="Test description",
            severity="MEDIUM",
            anomaly_score=0.6,
            source_ip="1.2.3.4",
            destination_ip="5.6.7.8",
        )
        resp = await service.create_alert(legacy_create)
        assert resp.title == "Legacy Probe Alert"
        assert resp.severity == "MEDIUM"
        assert resp.id is not None

        # Test legacy list_alerts
        list_resp = await service.list_alerts(limit=10, skip=0)
        assert list_resp.total == 1
        assert len(list_resp.alerts) == 1
        assert list_resp.alerts[0].title == "Legacy Probe Alert"


# =============================================================================
# Schema & Summary Validation Tests
# =============================================================================

class TestAlertSchemaValidation:
    def test_alert_document_to_summary_dict(self):
        doc = AlertDocument(
            alert_id="alt-summary-001",
            title="Suspicious Outbound Tunnel",
            description="Flow exhibiting periodic beaconing behavior.",
            severity="HIGH",
            priority="HIGH",
            status="OPEN",
            risk_score=72.5,
            source=NetworkEndpoint(ip="10.0.1.5", port=4444),
            destination=NetworkEndpoint(ip="198.51.100.1", port=80),
            deduplication=DeduplicationInfo(
                fingerprint="abcd1234efgh5678",
                occurrence_count=3,
            ),
        )
        summary = doc.to_summary_dict()
        assert summary["alert_id"] == "alt-summary-001"
        assert summary["severity"] == "HIGH"
        assert summary["priority"] == "HIGH"
        assert summary["risk_score"] == 72.5
        assert summary["source_ip"] == "10.0.1.5"
        assert summary["destination_ip"] == "198.51.100.1"
        assert summary["occurrence_count"] == 3
        assert summary["xai_attached"] is False
