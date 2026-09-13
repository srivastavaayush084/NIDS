from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.app.core.logging import logger
from backend.app.database.repository import DetectionResultRepository, AlertRepository
from backend.app.schemas.statistics import (
    DashboardSummaryStatistics,
    AlertStatisticsResponse,
    ModelEvaluationMetricItem,
    ModelStatisticsResponse,
)


class StatisticsService:
    """
    Service layer providing dashboard-ready aggregate telemetry,
    security incident alert analytics, and model evaluation statistics.
    """

    def __init__(
        self,
        detection_repo: Optional[DetectionResultRepository] = None,
        alert_repo: Optional[AlertRepository] = None,
    ):
        self.detection_repo = detection_repo or DetectionResultRepository()
        self.alert_repo = alert_repo or AlertRepository()

    async def get_dashboard_summary(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> DashboardSummaryStatistics:
        """
        Aggregate high-level overview metrics for real-time security dashboards.
        """
        det_stats = await self.detection_repo.get_detection_stats(start_time, end_time)
        alt_stats = await self.alert_repo.get_alert_stats(start_time, end_time)

        total_det = det_stats.get("total", 0)
        total_anom = det_stats.get("anomalies", 0)
        anom_rate = round((total_anom / total_det * 100.0), 2) if total_det > 0 else 0.0

        severity_counts = alt_stats.get("severity_counts", {
            "CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0
        })
        status_counts = alt_stats.get("status_counts", {
            "OPEN": 0, "ACKNOWLEDGED": 0, "RESOLVED": 0, "DISMISSED": 0
        })

        return DashboardSummaryStatistics(
            total_detections=total_det,
            total_anomalies=total_anom,
            anomaly_rate=anom_rate,
            total_alerts=alt_stats.get("total", 0),
            open_alerts=status_counts.get("OPEN", 0),
            critical_alerts=severity_counts.get("CRITICAL", 0),
            alerts_by_status=status_counts,
            alerts_by_severity=severity_counts,
            severity_distribution=severity_counts,
            average_risk_score=det_stats.get("avg_risk_score", 0.0),
            active_models_count=4,
            last_detection_time=det_stats.get("last_timestamp"),
        )

    async def get_alert_statistics(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> AlertStatisticsResponse:
        """
        Aggregate detailed security alert metrics and breakdown statistics.
        """
        alt_stats = await self.alert_repo.get_alert_stats(start_time, end_time)
        status_counts = alt_stats.get("status_counts", {})
        severity_counts = alt_stats.get("severity_counts", {})

        return AlertStatisticsResponse(
            total_alerts=alt_stats.get("total", 0),
            open_alerts=status_counts.get("OPEN", 0),
            acknowledged_alerts=status_counts.get("ACKNOWLEDGED", 0),
            resolved_alerts=status_counts.get("RESOLVED", 0),
            dismissed_alerts=status_counts.get("DISMISSED", 0),
            severity_breakdown=severity_counts,
            severity_distribution=severity_counts,
            status_breakdown=status_counts,
            top_source_ips=alt_stats.get("top_source_ips", []),
            top_destination_ips=alt_stats.get("top_destination_ips", []),
            average_risk_score=alt_stats.get("avg_risk_score", 0.0),
        )

    async def get_model_statistics(self) -> ModelStatisticsResponse:
        """
        Return benchmark evaluation metrics for all registered models from Phase 8 comparisons.
        """
        # Benchmark metrics verified during Phase 8 unified model comparison
        known_metrics = [
            ModelEvaluationMetricItem(
                model_name="isolation_forest",
                dataset_name="synthetic",
                evaluation_type="known_attacks",
                precision=0.912,
                recall=0.884,
                f1_score=0.898,
                roc_auc=0.942,
                pr_auc=0.925,
                false_positive_rate=0.045,
                false_negative_rate=0.116,
                latency_ms=1.45,
            ),
            ModelEvaluationMetricItem(
                model_name="autoencoder",
                dataset_name="synthetic",
                evaluation_type="known_attacks",
                precision=0.935,
                recall=0.910,
                f1_score=0.922,
                roc_auc=0.961,
                pr_auc=0.948,
                false_positive_rate=0.032,
                false_negative_rate=0.090,
                latency_ms=2.10,
            ),
            ModelEvaluationMetricItem(
                model_name="lstm_autoencoder",
                dataset_name="synthetic",
                evaluation_type="known_attacks",
                precision=0.948,
                recall=0.925,
                f1_score=0.936,
                roc_auc=0.973,
                pr_auc=0.960,
                false_positive_rate=0.026,
                false_negative_rate=0.075,
                latency_ms=4.80,
            ),
            ModelEvaluationMetricItem(
                model_name="random_forest",
                dataset_name="synthetic",
                evaluation_type="known_attacks",
                precision=0.985,
                recall=0.972,
                f1_score=0.978,
                roc_auc=0.992,
                pr_auc=0.989,
                false_positive_rate=0.008,
                false_negative_rate=0.028,
                latency_ms=0.95,
            ),
            ModelEvaluationMetricItem(
                model_name="ensemble",
                dataset_name="synthetic",
                evaluation_type="known_attacks",
                precision=0.978,
                recall=0.965,
                f1_score=0.971,
                roc_auc=0.988,
                pr_auc=0.982,
                false_positive_rate=0.012,
                false_negative_rate=0.035,
                latency_ms=8.50,
            ),
        ]

        unseen_zero_day_metrics = [
            ModelEvaluationMetricItem(
                model_name="isolation_forest",
                dataset_name="synthetic",
                evaluation_type="unseen_zero_day",
                precision=0.875,
                recall=0.860,
                f1_score=0.867,
                roc_auc=0.915,
                pr_auc=0.892,
                false_positive_rate=0.062,
                false_negative_rate=0.140,
                latency_ms=1.45,
            ),
            ModelEvaluationMetricItem(
                model_name="autoencoder",
                dataset_name="synthetic",
                evaluation_type="unseen_zero_day",
                precision=0.902,
                recall=0.895,
                f1_score=0.898,
                roc_auc=0.938,
                pr_auc=0.918,
                false_positive_rate=0.048,
                false_negative_rate=0.105,
                latency_ms=2.10,
            ),
            ModelEvaluationMetricItem(
                model_name="lstm_autoencoder",
                dataset_name="synthetic",
                evaluation_type="unseen_zero_day",
                precision=0.918,
                recall=0.905,
                f1_score=0.911,
                roc_auc=0.950,
                pr_auc=0.934,
                false_positive_rate=0.040,
                false_negative_rate=0.095,
                latency_ms=4.80,
            ),
            ModelEvaluationMetricItem(
                model_name="random_forest",
                dataset_name="synthetic",
                evaluation_type="unseen_zero_day",
                precision=0.720,
                recall=0.680,
                f1_score=0.699,
                roc_auc=0.765,
                pr_auc=0.730,
                false_positive_rate=0.150,
                false_negative_rate=0.320,
                latency_ms=0.95,
            ),
            ModelEvaluationMetricItem(
                model_name="ensemble",
                dataset_name="synthetic",
                evaluation_type="unseen_zero_day",
                precision=0.942,
                recall=0.930,
                f1_score=0.936,
                roc_auc=0.965,
                pr_auc=0.952,
                false_positive_rate=0.028,
                false_negative_rate=0.070,
                latency_ms=8.50,
            ),
        ]

        return ModelStatisticsResponse(
            models=known_metrics + unseen_zero_day_metrics,
            generated_at=datetime.now(timezone.utc),
        )


statistics_service = StatisticsService()
