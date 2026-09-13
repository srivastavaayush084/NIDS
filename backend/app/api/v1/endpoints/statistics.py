from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Query, Depends
from backend.app.services.statistics_service import statistics_service
from backend.app.schemas.statistics import (
    DashboardSummaryStatistics,
    AlertStatisticsResponse,
    ModelStatisticsResponse,
)
from backend.app.core.logging import logger
from backend.app.auth.dependencies import require_any_authenticated
from backend.app.models.user import UserDocument

router = APIRouter()


@router.get("/summary", response_model=DashboardSummaryStatistics, summary="Dashboard Overview Statistics")
async def get_dashboard_summary(
    start_time: Optional[datetime] = Query(None, description="Filter statistics from this timestamp (ISO 8601)"),
    end_time: Optional[datetime] = Query(None, description="Filter statistics up to this timestamp (ISO 8601)"),
    current_user: UserDocument = Depends(require_any_authenticated),
):
    """
    Retrieve real-time aggregate statistics for security operations center (SOC) dashboards.
    Includes total detections, anomaly rates, alert counts by severity & status, average risk score,
    and active model health indicators.
    """
    logger.info(f"Fetching dashboard summary stats (start={start_time}, end={end_time})")
    return await statistics_service.get_dashboard_summary(start_time=start_time, end_time=end_time)


@router.get("/alerts", response_model=AlertStatisticsResponse, summary="Alert Aggregate Statistics")
async def get_alert_statistics(
    start_time: Optional[datetime] = Query(None, description="Filter statistics from this timestamp (ISO 8601)"),
    end_time: Optional[datetime] = Query(None, description="Filter statistics up to this timestamp (ISO 8601)"),
    current_user: UserDocument = Depends(require_any_authenticated),
):
    """
    Retrieve detailed alert analytics, including status breakdowns (OPEN, ACKNOWLEDGED, RESOLVED, DISMISSED),
    severity distributions (CRITICAL, HIGH, MEDIUM, LOW), top attacking source IPs, and top targeted destination IPs.
    """
    logger.info(f"Fetching alert statistics (start={start_time}, end={end_time})")
    return await statistics_service.get_alert_statistics(start_time=start_time, end_time=end_time)


@router.get("/models", response_model=ModelStatisticsResponse, summary="Model Evaluation & Comparison Metrics")
async def get_model_statistics(
    current_user: UserDocument = Depends(require_any_authenticated),
):
    """
    Retrieve comparative evaluation metrics across all anomaly detection models and baseline classifiers
    (Isolation Forest, Autoencoder, LSTM Autoencoder, Random Forest, and Ensemble Engine), comparing performance
    on both known attack distributions and novel zero-day attack scenarios.
    """
    logger.info("Fetching model evaluation benchmark metrics")
    return await statistics_service.get_model_statistics()

