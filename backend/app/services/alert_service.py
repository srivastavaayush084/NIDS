import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.database.repository import AlertRepository, AuditLogRepository
from backend.app.ml.ensemble.schemas import EnsemblePrediction
from backend.app.ml.explainability.schemas import EnsembleExplanation, ModelExplanation
from backend.app.alerts.schemas import (
    AlertDocument,
    AlertEventResult,
    AlertFilterParams,
    AlertPriority,
    AlertSeverity,
    AlertStatus,
)
from backend.app.alerts.engine import AlertEngine
from backend.app.schemas.alert import AlertCreate, AlertResponse, AlertListResponse


class AlertService:
    """
    Core business logic service orchestrating security alert lifecycle,
    deduplication, Explainable AI attachment, MongoDB persistence, and audit logging.
    """

    def __init__(
        self,
        alert_repo: Optional[AlertRepository] = None,
        audit_repo: Optional[AuditLogRepository] = None,
        alert_engine: Optional[AlertEngine] = None,
    ):
        self.repository = alert_repo or AlertRepository()
        self.audit_repo = audit_repo or AuditLogRepository()
        self.alert_engine = alert_engine or AlertEngine()

    async def _write_audit_log(
        self,
        action: str,
        resource: str,
        user_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Write an auditable record to the audit_logs collection."""
        try:
            audit_entry = {
                "timestamp": datetime.now(timezone.utc),
                "action": action,
                "resource": resource,
                "user_id": user_id or "system_alert_engine",
                "details": details or {},
            }
            await self.audit_repo.insert_one(audit_entry)
        except Exception as e:
            logger.warning(f"Failed to record alert audit log: {e}")

    async def process_detection_result(
        self,
        prediction: EnsemblePrediction,
        flow_context: Optional[Dict[str, Any]] = None,
        explanation: Optional[Union[EnsembleExplanation, ModelExplanation]] = None,
        detection_result_id: Optional[str] = None,
    ) -> AlertEventResult:
        """
        Process an ensemble detection result through the Alert Engine:
        1. Evaluate rule engine and create AlertDocument.
        2. Perform deterministic fingerprinting and check temporal cooldown deduplication.
        3. If duplicate within window: increment occurrence count and audit.
        4. If new alert: insert into MongoDB, audit creation, and return result.
        """
        should_alert, alert_doc, reason, severity, fingerprint = self.alert_engine.evaluate_and_build_alert(
            prediction=prediction,
            flow_context=flow_context,
            explanation=explanation,
            detection_result_id=detection_result_id,
        )

        if not should_alert or alert_doc is None:
            return AlertEventResult(
                alert_created=False,
                deduplicated=False,
                severity=severity,
                risk_score=prediction.risk_score,
                fingerprint=fingerprint,
                reason=reason,
            )

        # Check for active existing alert with matching fingerprint
        active_alert = await self.repository.find_active_by_fingerprint(fingerprint)

        if active_alert:
            # Check cooldown window
            dedup_data = active_alert.get("deduplication", {})
            last_seen = dedup_data.get("last_seen", active_alert.get("created_at", datetime.now(timezone.utc)))
            
            if isinstance(last_seen, str):
                try:
                    last_seen = datetime.fromisoformat(last_seen)
                except ValueError:
                    last_seen = datetime.now(timezone.utc)

            if self.alert_engine.deduplicator.is_within_cooldown(last_seen):
                # Within cooldown: Deduplicate and increment occurrence
                target_alert_id = active_alert.get("alert_id", str(active_alert.get("_id", "")))
                current_count = int(dedup_data.get("occurrence_count", 1)) + 1
                await self.repository.increment_occurrence(
                    alert_id=target_alert_id,
                    timestamp=alert_doc.timestamp,
                    latest_risk_score=alert_doc.risk_score,
                )

                logger.info(
                    f"Deduplicated recurring incident for Alert [{target_alert_id}]. "
                    f"New occurrence count: {current_count}"
                )

                await self._write_audit_log(
                    action="ALERT_DEDUPLICATED",
                    resource=target_alert_id,
                    details={
                        "fingerprint": fingerprint,
                        "occurrence_count": current_count,
                        "risk_score": alert_doc.risk_score,
                        "flow_context": flow_context or {},
                    },
                )

                return AlertEventResult(
                    alert_created=False,
                    alert_id=target_alert_id,
                    deduplicated=True,
                    severity=active_alert.get("severity", severity),
                    priority=active_alert.get("priority", alert_doc.priority),
                    risk_score=max(active_alert.get("risk_score", 0.0), alert_doc.risk_score),
                    status=active_alert.get("status", "OPEN"),
                    fingerprint=fingerprint,
                    occurrence_count=current_count,
                    xai_available=bool(alert_doc.explanation and alert_doc.explanation.is_available),
                    reason="alert_deduplicated_within_cooldown_window",
                )

        # New incident: Persist fresh alert document
        doc_dict = alert_doc.model_dump(by_alias=True)
        if not doc_dict.get("_id"):
            doc_dict["_id"] = alert_doc.alert_id
        inserted_id = await self.repository.insert_one(doc_dict)
        if inserted_id:
            alert_doc.id = inserted_id

        await self._write_audit_log(
            action="ALERT_CREATED",
            resource=alert_doc.alert_id,
            details={
                "title": alert_doc.title,
                "severity": alert_doc.severity,
                "priority": alert_doc.priority,
                "risk_score": alert_doc.risk_score,
                "fingerprint": fingerprint,
                "xai_attached": bool(alert_doc.explanation and alert_doc.explanation.is_available),
            },
        )

        logger.info(f"Persisted new Security Alert [{alert_doc.severity}|{alert_doc.priority}] {alert_doc.alert_id}")

        return AlertEventResult(
            alert_created=True,
            alert_id=alert_doc.alert_id,
            deduplicated=False,
            severity=alert_doc.severity,
            priority=alert_doc.priority,
            risk_score=alert_doc.risk_score,
            status=alert_doc.status,
            fingerprint=fingerprint,
            occurrence_count=1,
            xai_available=bool(alert_doc.explanation and alert_doc.explanation.is_available),
            reason="new_alert_created",
            alert=alert_doc,
        )

    async def get_alert(self, alert_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve single alert by alert_id."""
        doc = await self.repository.find_by_alert_id(alert_id)
        if not doc:
            doc = await self.repository.find_one({"_id": alert_id})
        return doc

    async def acknowledge_alert(self, alert_id: str, user_id: Optional[str] = None) -> bool:
        """Transition alert status from OPEN to ACKNOWLEDGED."""
        updated = await self.repository.update_status(
            alert_id=alert_id,
            status="ACKNOWLEDGED",
            assigned_to=user_id,
        )
        if updated:
            await self._write_audit_log(
                action="ALERT_ACKNOWLEDGED",
                resource=alert_id,
                user_id=user_id,
            )
            logger.info(f"Alert [{alert_id}] marked as ACKNOWLEDGED by {user_id or 'system'}")
        return updated

    async def resolve_alert(
        self,
        alert_id: str,
        resolution_note: str,
        user_id: Optional[str] = None,
    ) -> bool:
        """Transition alert status to RESOLVED with operational notes."""
        updated = await self.repository.update_status(
            alert_id=alert_id,
            status="RESOLVED",
            assigned_to=user_id,
            resolution_note=resolution_note,
        )
        if updated:
            await self._write_audit_log(
                action="ALERT_RESOLVED",
                resource=alert_id,
                user_id=user_id,
                details={"resolution_note": resolution_note},
            )
            logger.info(f"Alert [{alert_id}] marked as RESOLVED by {user_id or 'system'}")
        return updated

    async def dismiss_alert(
        self,
        alert_id: str,
        dismissal_reason: str,
        user_id: Optional[str] = None,
    ) -> bool:
        """Transition alert status to DISMISSED (e.g. verified false positive or benign noise)."""
        updated = await self.repository.update_status(
            alert_id=alert_id,
            status="DISMISSED",
            assigned_to=user_id,
            dismissal_reason=dismissal_reason,
        )
        if updated:
            await self._write_audit_log(
                action="ALERT_DISMISSED",
                resource=alert_id,
                user_id=user_id,
                details={"dismissal_reason": dismissal_reason},
            )
            logger.info(f"Alert [{alert_id}] marked as DISMISSED by {user_id or 'system'}")
        return updated

    async def query_alerts(
        self,
        params: Optional[AlertFilterParams] = None,
    ) -> Dict[str, Any]:
        """Query security alerts with comprehensive filtering, pagination, and sorting."""
        p = params or AlertFilterParams()
        query: Dict[str, Any] = {}

        if p.severity:
            query["severity"] = p.severity
        if p.status:
            query["status"] = p.status
        if p.alert_type:
            query["alert_type"] = p.alert_type
        if p.source_ip:
            query["source.ip"] = p.source_ip
        if p.destination_ip:
            query["destination.ip"] = p.destination_ip
        if p.fingerprint:
            query["deduplication.fingerprint"] = p.fingerprint
        if p.min_risk_score is not None:
            query["risk_score"] = {"$gte": p.min_risk_score}
        if p.start_time or p.end_time:
            time_filter: Dict[str, Any] = {}
            if p.start_time:
                time_filter["$gte"] = p.start_time
            if p.end_time:
                time_filter["$lte"] = p.end_time
            query["created_at"] = time_filter

        sort_dir = -1 if p.sort_desc else 1
        sort_order = [(p.sort_by, sort_dir)]

        docs = await self.repository.find_many(query, limit=p.limit, skip=p.skip, sort=sort_order)
        total = await self.repository.count(query)

        return {
            "total": total,
            "page": (p.skip // p.limit) + 1 if p.limit > 0 else 1,
            "limit": p.limit,
            "alerts": docs,
        }

    # =========================================================================
    # Backwards Compatibility API Layer
    # =========================================================================
    async def create_alert(self, alert_in: AlertCreate) -> AlertResponse:
        """Legacy helper for direct AlertCreate ingestion."""
        now = datetime.now(timezone.utc)
        doc = alert_in.model_dump()
        doc["created_at"] = now
        doc["updated_at"] = now
        doc["alert_id"] = f"alt-{uuid.uuid4().hex[:12]}"
        
        inserted_id = await self.repository.insert_one(doc) or "stub_id"
        logger.info(f"Created security alert [{alert_in.severity}] {alert_in.title}")

        return AlertResponse(
            id=inserted_id,
            **doc
        )

    async def list_alerts(self, limit: int = 50, skip: int = 0) -> AlertListResponse:
        """Legacy helper for paginated alert listing."""
        docs = await self.repository.find_many({}, limit=limit, skip=skip, sort=[("created_at", -1)])
        total = await self.repository.count({})

        alerts = []
        for idx, d in enumerate(docs):
            raw_status = str(d.get("status", "new")).lower()
            if raw_status == "open":
                status_val = "new"
            elif raw_status in ["new", "acknowledged", "resolved", "dismissed"]:
                status_val = raw_status
            else:
                status_val = "new"

            raw_sev = str(d.get("severity", "MEDIUM")).upper()
            sev_val = raw_sev if raw_sev in ["INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"] else "MEDIUM"

            src_ip = d.get("source_ip")
            if not src_ip and isinstance(d.get("source"), dict):
                src_ip = d.get("source", {}).get("ip")

            dst_ip = d.get("destination_ip")
            if not dst_ip and isinstance(d.get("destination"), dict):
                dst_ip = d.get("destination", {}).get("ip")

            expl = d.get("explanation")
            if isinstance(expl, dict):
                expl = expl.get("summary")
            elif not isinstance(expl, str):
                expl = None

            now = datetime.now(timezone.utc)
            ts = d.get("timestamp") or d.get("created_at") or now
            created = d.get("created_at") or now
            updated = d.get("updated_at")

            raw_score = d.get("anomaly_score")
            if raw_score is None:
                risk = d.get("risk_score", 0.0)
                score_val = min(1.0, max(0.0, float(risk) / 100.0))
            else:
                score_val = float(raw_score)

            alerts.append(
                AlertResponse(
                    id=str(d.get("_id", d.get("alert_id", f"alt-{idx}"))),
                    title=d.get("title", "Anomaly Alert"),
                    description=d.get("description", ""),
                    alert_type=d.get("alert_type", "ZERO_DAY_ANOMALY"),
                    severity=sev_val,
                    anomaly_score=score_val,
                    source_ip=src_ip,
                    destination_ip=dst_ip,
                    status=status_val,
                    explanation=expl,
                    detection_result_id=d.get("detection_result_id"),
                    timestamp=ts,
                    created_at=created,
                    updated_at=updated,
                )
            )

        return AlertListResponse(
            total=total,
            page=(skip // limit) + 1 if limit > 0 else 1,
            limit=limit,
            alerts=alerts
        )


alert_service = AlertService()
