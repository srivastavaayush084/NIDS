from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class DashboardSummaryStatistics(BaseModel):
    """Aggregated dashboard telemetry metrics."""
    total_detections: int = 0
    total_anomalies: int = 0
    anomaly_rate: float = 0.0
    total_alerts: int = 0
    alerts_by_status: Dict[str, int] = Field(default_factory=lambda: {
        "OPEN": 0,
        "ACKNOWLEDGED": 0,
        "RESOLVED": 0,
        "DISMISSED": 0,
    })
    alerts_by_severity: Dict[str, int] = Field(default_factory=lambda: {
        "CRITICAL": 0,
        "HIGH": 0,
        "MEDIUM": 0,
        "LOW": 0,
    })
    average_risk_score: float = 0.0
    active_models_count: int = 4
    last_detection_time: Optional[datetime] = None


class AlertStatisticsResponse(BaseModel):
    """Detailed analytics breakdown for security incident alerts."""
    total_alerts: int = 0
    open_alerts: int = 0
    acknowledged_alerts: int = 0
    resolved_alerts: int = 0
    dismissed_alerts: int = 0
    severity_breakdown: Dict[str, int] = Field(default_factory=dict)
    status_breakdown: Dict[str, int] = Field(default_factory=dict)
    top_source_ips: List[Dict[str, Any]] = Field(default_factory=list)
    top_destination_ips: List[Dict[str, Any]] = Field(default_factory=list)
    average_risk_score: float = 0.0


class ModelEvaluationMetricItem(BaseModel):
    """Standardized evaluation benchmark metrics for an individual model."""
    model_name: str
    dataset_name: str = "synthetic"
    evaluation_type: str = "standard"  # 'standard' or 'unseen_zero_day'
    precision: float
    recall: float
    f1_score: float
    roc_auc: Optional[float] = None
    pr_auc: Optional[float] = None
    false_positive_rate: Optional[float] = None
    false_negative_rate: Optional[float] = None
    latency_ms: float = 0.0


class ModelStatisticsResponse(BaseModel):
    """Aggregated evaluation and performance metrics across all models."""
    models: List[ModelEvaluationMetricItem] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
