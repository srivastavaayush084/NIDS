from datetime import datetime, timezone
from typing import Any, Dict, Optional, Literal
from backend.app.core.logging import logger
from backend.app.database.repository import AuditLogRepository

AuditStatus = Literal["SUCCESS", "FAILURE", "DENIED"]


class AuditService:
    """Centralized security audit event recording service."""

    def __init__(self, repo: Optional[AuditLogRepository] = None):
        self._repo = repo

    @property
    def repo(self) -> AuditLogRepository:
        if self._repo is None:
            self._repo = AuditLogRepository()
        return self._repo

    async def log_event(
        self,
        action: str,
        resource: str,
        status: AuditStatus = "SUCCESS",
        user_id: Optional[str] = None,
        resource_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """
        Record a security or compliance event in the audit_logs collection.
        Safely omits credentials, tokens, and raw passwords.
        """
        safe_meta = metadata or {}
        # Ensure sensitive keys are filtered
        for k in ["password", "token", "secret", "access_token", "refresh_token"]:
            if k in safe_meta:
                safe_meta[k] = "[REDACTED]"

        doc = {
            "timestamp": datetime.now(timezone.utc),
            "user_id": user_id or "system",
            "action": action,
            "resource": resource,
            "resource_id": resource_id,
            "ip_address": ip_address,
            "status": status,
            "metadata": safe_meta,
        }

        try:
            inserted_id = await self.repo.insert_one(doc)
            logger.info(
                f"[AUDIT] action={action} resource={resource} user={user_id} status={status} id={inserted_id}"
            )
            return inserted_id
        except Exception as e:
            logger.warning(f"Failed to record audit log event: {str(e)}")
            return None


audit_service = AuditService()
