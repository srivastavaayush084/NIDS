from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from backend.app.core.logging import logger
from backend.app.ml.model_manager import model_manager
from backend.app.detection.risk_scorer import RiskScorer
from backend.app.detection.explainer import DetectionExplainer
from backend.app.schemas.traffic import NetworkPacketFeature
from backend.app.schemas.detection import DetectionResult, ModelPrediction, FeatureContribution


class DetectionEngine:
    """Core anomaly detection and multi-model consensus engine."""

    def __init__(self):
        self.risk_scorer = RiskScorer()
        self.explainer = DetectionExplainer()

    async def analyze_flow(self, flow: NetworkPacketFeature, active_models: Optional[List[str]] = None) -> DetectionResult:
        """Run network flow through multi-model detection pipeline."""
        logger.debug(f"Analyzing flow: {flow.src_ip}:{flow.src_port} -> {flow.dst_ip}:{flow.dst_port}")
        
        predictions: Dict[str, ModelPrediction] = {}
        model_scores: Dict[str, float] = {}

        selected_models = active_models or ["isolation_forest", "autoencoder", "lstm", "random_forest"]

        for model_name in selected_models:
            predictions[model_name] = ModelPrediction(
                model_name=model_name,
                is_anomaly=False,
                raw_score=0.0,
                confidence=0.0
            )
            model_scores[model_name] = 0.0

        risk_score = self.risk_scorer.calculate_risk_score(model_scores)
        severity = self.risk_scorer.determine_severity(risk_score)

        return DetectionResult(
            flow_id=f"{flow.src_ip}-{flow.dst_ip}-{flow.dst_port}-{int(datetime.now(timezone.utc).timestamp())}",
            timestamp=datetime.now(timezone.utc),
            is_zero_day_suspect=False,
            risk_score=risk_score,
            severity=severity,
            model_predictions=predictions,
            top_contributing_features=[],
            explanation="System running in Phase 1 Architecture mode (Models pending training)."
        )


detection_engine = DetectionEngine()
