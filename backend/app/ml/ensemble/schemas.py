from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ModelContribution(BaseModel):
    """Container for an individual model's prediction and scoring contribution to the ensemble."""
    model_name: str
    prediction: str = Field(..., description="'normal' or 'attack'")
    is_anomaly: bool
    native_score: float
    normalized_score: float = Field(..., ge=0.0, le=100.0, description="Normalized risk score (0.0 - 100.0)")
    configured_weight: float = Field(..., ge=0.0, description="Pre-configured static weight")
    effective_weight: float = Field(..., ge=0.0, le=1.0, description="Renormalized weight among available models")
    decision_threshold: float
    latency_ms: float = 0.0
    is_available: bool = True
    error: Optional[str] = None


class ModelAgreement(BaseModel):
    """Consensus and agreement metrics across participating ensemble models."""
    models_total: int
    models_available: int
    models_anomalous: int
    models_normal: int
    agreement_ratio: float = Field(..., ge=0.0, le=1.0, description="Fraction of available models agreeing on majority class")
    disagreement_ratio: float = Field(..., ge=0.0, le=1.0, description="1.0 - agreement_ratio")
    consensus_prediction: str = Field(..., description="Majority prediction across participating models")


class LatencyBreakdown(BaseModel):
    """Detailed microsecond/millisecond execution time breakdown per model and ensemble layer."""
    isolation_forest_ms: float = 0.0
    autoencoder_ms: float = 0.0
    lstm_autoencoder_ms: float = 0.0
    random_forest_ms: float = 0.0
    ensemble_aggregation_ms: float = 0.0
    total_ms: float = 0.0


class EnsemblePrediction(BaseModel):
    """Unified standardized detection output produced by the Ensemble Detection and Risk Scoring Engine."""
    model_name: str = "ensemble"
    model_version: str = "1.0.0"
    prediction: str = Field(..., description="'normal' or 'attack'")
    is_anomaly: bool
    risk_score: float = Field(..., ge=0.0, le=100.0, description="Composite weighted risk score (0.0 to 100.0)")
    severity: str = Field(..., description="Severity level: LOW, MEDIUM, HIGH, CRITICAL")
    decision_threshold: float = Field(default=50.0, description="Ensemble classification cutoff threshold")
    reliability_score: float = Field(..., ge=0.0, le=1.0, description="Heuristic reliability indicator based on model availability and consensus")
    agreement: ModelAgreement
    contributions: Dict[str, ModelContribution] = Field(default_factory=dict)
    participating_models: List[str] = Field(default_factory=list)
    missing_models: List[str] = Field(default_factory=list)
    latency: LatencyBreakdown
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def to_summary_dict(self) -> Dict[str, Any]:
        """Compact summary dictionary suitable for logging and high-level telemetry."""
        return {
            "prediction": self.prediction,
            "is_anomaly": self.is_anomaly,
            "risk_score": round(self.risk_score, 2),
            "severity": self.severity,
            "agreement_ratio": round(self.agreement.agreement_ratio, 3),
            "participating_models": self.participating_models,
            "missing_models": self.missing_models,
            "reliability_score": round(self.reliability_score, 3),
            "total_latency_ms": round(self.latency.total_ms, 3),
        }
