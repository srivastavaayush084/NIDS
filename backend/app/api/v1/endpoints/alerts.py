from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, Query, Depends, status

from backend.app.core.config import settings
from backend.app.alerts.schemas import AlertFilterParams, AlertSeverity, AlertStatus
from backend.app.services.alert_service import alert_service
from backend.app.schemas.alert import AlertCreate, AlertResponse, AlertListResponse
from backend.app.auth.dependencies import require_any_authenticated, require_analyst_or_admin
from backend.app.models.user import UserDocument

router = APIRouter()


class AcknowledgeAlertRequest(BaseModel):
    user_id: Optional[str] = Field(default=None, description="Analyst identifier taking ownership")


class ResolveAlertRequest(BaseModel):
    resolution_note: str = Field(..., min_length=3, max_length=1000, description="Detailed explanation of resolution or remediation")
    user_id: Optional[str] = Field(default=None, description="Analyst identifier resolving the incident")


class DismissAlertRequest(BaseModel):
    dismissal_reason: str = Field(..., min_length=3, max_length=1000, description="Reason for dismissal (e.g., false positive, authorized scan)")
    user_id: Optional[str] = Field(default=None, description="Analyst identifier dismissing the alert")


@router.get(
    "",
    response_model=Dict[str, Any],
    summary="List Security Incident Alerts",
)
async def list_security_alerts(
    severity: Optional[str] = Query(None, description="Filter by severity: LOW, MEDIUM, HIGH, CRITICAL"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status: OPEN, ACKNOWLEDGED, RESOLVED, DISMISSED"),
    alert_type: Optional[str] = Query(None, description="Filter by alert type"),
    source_ip: Optional[str] = Query(None, description="Filter by source IP"),
    destination_ip: Optional[str] = Query(None, description="Filter by destination IP"),
    start_time: Optional[datetime] = Query(None, description="Filter start timestamp"),
    end_time: Optional[datetime] = Query(None, description="Filter end timestamp"),
    min_risk_score: Optional[float] = Query(None, ge=0.0, le=100.0, description="Minimum risk score threshold"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: UserDocument = Depends(require_any_authenticated),
):
    """
    Retrieve security incident alerts with pagination, filtering, and sorting (newest first).
    """
    sev = severity.upper() if severity else None
    stat = status_filter.upper() if status_filter else None
    limit = min(page_size, settings.MAX_PAGE_SIZE)
    skip = (page - 1) * limit

    params = AlertFilterParams(
        severity=sev,  # type: ignore
        status=stat,  # type: ignore
        alert_type=alert_type,
        source_ip=source_ip,
        destination_ip=destination_ip,
        start_time=start_time,
        end_time=end_time,
        min_risk_score=min_risk_score,
        limit=limit,
        skip=skip,
        sort_by="created_at",
        sort_desc=True,
    )

    res = await alert_service.query_alerts(params)
    total = res["total"]
    total_pages = (total + limit - 1) // limit if limit > 0 else 1

    return {
        "success": True,
        "data": res["alerts"],
        "pagination": {
            "page": page,
            "page_size": limit,
            "total": total,
            "total_pages": total_pages,
        },
    }


@router.get(
    "/{alert_id}",
    response_model=Dict[str, Any],
    summary="Get Security Alert Details",
)
async def get_alert_detail(
    alert_id: str,
    current_user: UserDocument = Depends(require_any_authenticated),
):
    """
    Retrieve full security alert document including multi-model evidence, XAI attributions, and deduplication info.
    """
    doc = await alert_service.get_alert(alert_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Security alert '{alert_id}' not found.",
        )
    return {
        "success": True,
        "data": doc,
    }


@router.patch(
    "/{alert_id}/acknowledge",
    response_model=Dict[str, Any],
    summary="Acknowledge Security Alert",
)
async def acknowledge_alert(
    alert_id: str,
    body: Optional[AcknowledgeAlertRequest] = None,
    current_user: UserDocument = Depends(require_analyst_or_admin),
):
    """
    Transition an alert state from OPEN to ACKNOWLEDGED.
    Records audit log and assigns incident to analyst.
    """
    existing = await alert_service.get_alert(alert_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Security alert '{alert_id}' not found.",
        )

    current_status = str(existing.get("status", "")).upper()
    if current_status in ["RESOLVED", "DISMISSED"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot acknowledge alert '{alert_id}' because it is already in terminal state '{current_status}'.",
        )

    user_id = (body.user_id if body and body.user_id else current_user.username)
    success = await alert_service.acknowledge_alert(alert_id=alert_id, user_id=user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to update alert '{alert_id}'.",
        )

    updated_doc = await alert_service.get_alert(alert_id)
    return {
        "success": True,
        "data": updated_doc,
        "message": f"Alert '{alert_id}' acknowledged by {user_id}.",
    }


@router.patch(
    "/{alert_id}/resolve",
    response_model=Dict[str, Any],
    summary="Resolve Security Alert",
)
async def resolve_alert(
    alert_id: str,
    body: ResolveAlertRequest,
    current_user: UserDocument = Depends(require_analyst_or_admin),
):
    """
    Transition an alert state to RESOLVED with required operational notes.
    """
    existing = await alert_service.get_alert(alert_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Security alert '{alert_id}' not found.",
        )

    current_status = str(existing.get("status", "")).upper()
    if current_status == "RESOLVED":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Alert '{alert_id}' is already RESOLVED.",
        )

    user_id = body.user_id or current_user.username
    success = await alert_service.resolve_alert(
        alert_id=alert_id,
        resolution_note=body.resolution_note,
        user_id=user_id,
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to resolve alert '{alert_id}'.",
        )

    updated_doc = await alert_service.get_alert(alert_id)
    return {
        "success": True,
        "data": updated_doc,
        "message": f"Alert '{alert_id}' resolved.",
    }


@router.patch(
    "/{alert_id}/dismiss",
    response_model=Dict[str, Any],
    summary="Dismiss Security Alert",
)
async def dismiss_alert(
    alert_id: str,
    body: DismissAlertRequest,
    current_user: UserDocument = Depends(require_analyst_or_admin),
):
    """
    Transition an alert state to DISMISSED with required dismissal reason.
    """
    existing = await alert_service.get_alert(alert_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Security alert '{alert_id}' not found.",
        )

    current_status = str(existing.get("status", "")).upper()
    if current_status == "DISMISSED":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Alert '{alert_id}' is already DISMISSED.",
        )

    user_id = body.user_id or current_user.username
    success = await alert_service.dismiss_alert(
        alert_id=alert_id,
        dismissal_reason=body.dismissal_reason,
        user_id=user_id,
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to dismiss alert '{alert_id}'.",
        )

    updated_doc = await alert_service.get_alert(alert_id)
    return {
        "success": True,
        "data": updated_doc,
        "message": f"Alert '{alert_id}' dismissed.",
    }


# =============================================================================
# Legacy Alert Endpoints (Phases 1-2 Compatibility)
# =============================================================================

@router.post("/legacy", response_model=AlertResponse, summary="Create Security Alert (Legacy)")
async def create_alert_legacy(
    alert_in: AlertCreate,
    current_user: UserDocument = Depends(require_analyst_or_admin),
):
    """Legacy helper for direct AlertCreate ingestion."""
    return await alert_service.create_alert(alert_in)

