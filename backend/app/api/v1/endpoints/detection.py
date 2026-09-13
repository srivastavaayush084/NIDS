from datetime import datetime
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, Depends, status

from backend.app.core.config import settings
from backend.app.schemas.detection import (
    SingleDetectionRequest,
    SingleDetectionResponse,
    BatchDetectionRequest,
    BatchDetectionResponse,
    SequenceDetectionRequest,
    SequenceDetectionResponse,
    DetectionFilterParams,
    DetectionRequest,
    DetectionResult,
    BatchDetectionResponse as LegacyBatchDetectionResponse,
)
from backend.app.services.detection_service import detection_service
from backend.app.auth.dependencies import require_analyst_or_admin, require_any_authenticated
from backend.app.models.user import UserDocument

router = APIRouter()


@router.post(
    "",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Analyze Single Network Flow Event",
)
async def analyze_single_event(
    request_in: SingleDetectionRequest,
    current_user: UserDocument = Depends(require_analyst_or_admin),
):
    """
    Execute full detection pipeline on a single network event flow:
    preprocessing -> multi-model ensemble inference -> XAI explanation -> alert generation -> persistence.
    """
    result = await detection_service.detect_single(
        features=request_in.features,
        dataset_name=request_in.dataset_name,
        generate_xai=request_in.generate_xai if request_in.generate_xai is not None else True,
        flow_context=request_in.flow_context,
    )
    return {
        "success": True,
        "data": result.model_dump(),
    }


@router.post(
    "/batch",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Analyze Batch of Network Flow Events",
)
async def analyze_batch_events(
    request_in: BatchDetectionRequest,
    current_user: UserDocument = Depends(require_analyst_or_admin),
):
    """
    Execute batch detection across multiple network flow records.
    Enforces batch size limits and isolates per-record failures.
    """
    result = await detection_service.detect_batch(
        events=request_in.events,
        dataset_name=request_in.dataset_name,
        generate_xai=request_in.generate_xai or False,
    )
    return {
        "success": True,
        "data": result.model_dump(),
    }


@router.post(
    "/sequence",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Analyze Temporal Event Sequence (LSTM Autoencoder)",
)
async def analyze_sequence_events(
    request_in: SequenceDetectionRequest,
    current_user: UserDocument = Depends(require_analyst_or_admin),
):
    """
    Execute sequential time-series anomaly detection on a sliding window of consecutive network events.
    """
    result = await detection_service.detect_sequence(
        sequence=request_in.sequence,
        dataset_name=request_in.dataset_name,
        generate_xai=request_in.generate_xai if request_in.generate_xai is not None else True,
        flow_context=request_in.flow_context,
    )
    return {
        "success": True,
        "data": result.model_dump(),
    }


@router.get(
    "",
    response_model=Dict[str, Any],
    summary="Query Detection Results History",
)
async def list_detections(
    start_time: Optional[datetime] = Query(None, description="Filter start timestamp"),
    end_time: Optional[datetime] = Query(None, description="Filter end timestamp"),
    severity: Optional[str] = Query(None, description="Filter by severity: LOW, MEDIUM, HIGH, CRITICAL"),
    prediction: Optional[str] = Query(None, description="Filter by prediction: normal, attack"),
    is_anomaly: Optional[bool] = Query(None, description="Filter by boolean anomaly flag"),
    min_risk_score: Optional[float] = Query(None, ge=0.0, le=100.0, description="Minimum composite risk score"),
    dataset_name: Optional[str] = Query(None, description="Filter by dataset/pipeline"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: UserDocument = Depends(require_any_authenticated),
):
    """
    Retrieve historical detection records with pagination, filtering, and sorting (newest first).
    """
    params = DetectionFilterParams(
        start_time=start_time,
        end_time=end_time,
        severity=severity,
        prediction=prediction,
        is_anomaly=is_anomaly,
        min_risk_score=min_risk_score,
        dataset_name=dataset_name,
        page=page,
        page_size=page_size,
    )
    res = await detection_service.query_detections(params)
    return {
        "success": True,
        "data": res["items"],
        "pagination": {
            "page": res["page"],
            "page_size": res["page_size"],
            "total": res["total"],
            "total_pages": res["total_pages"],
        },
    }


@router.get(
    "/{detection_id}",
    response_model=Dict[str, Any],
    summary="Get Single Detection Result by ID",
)
async def get_detection_detail(
    detection_id: str,
    current_user: UserDocument = Depends(require_any_authenticated),
):
    """
    Retrieve detailed metadata, model breakdown, XAI summary, and alert reference for a single detection event.
    """
    doc = await detection_service.get_detection(detection_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Detection record '{detection_id}' not found.",
        )
    return {
        "success": True,
        "data": doc,
    }


# =============================================================================
# Legacy Routes (Phases 1-2 Compatibility)
# =============================================================================

@router.post("/analyze", response_model=DetectionResult, summary="Analyze Single Network Flow (Legacy)")
async def analyze_flow_legacy(
    request: DetectionRequest,
    current_user: UserDocument = Depends(require_analyst_or_admin),
):
    """Legacy endpoint for single network flow analysis."""
    return await detection_service.run_detection(request)


@router.post("/analyze/batch", response_model=LegacyBatchDetectionResponse, summary="Analyze Batch of Flows (Legacy)")
async def analyze_batch_legacy(
    request: Any,
    current_user: UserDocument = Depends(require_analyst_or_admin),
):
    """Legacy endpoint for batch network flow analysis."""
    return await detection_service.run_batch_detection(request)

