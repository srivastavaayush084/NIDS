import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field


class FeatureContribution(BaseModel):
    """
    Standardized atomic feature attribution record.
    Represents how an individual feature pushed a model's prediction or reconstruction.
    """
    feature_name: str = Field(..., description="Meaningful sanitized feature column name")
    feature_value: Union[float, int, str, None] = Field(None, description="Actual observed feature value in sample")
    contribution: float = Field(..., description="Signed contribution value (positive = pushes toward anomaly)")
    direction: str = Field(..., description="'increases_risk', 'decreases_risk', or 'neutral'")
    absolute_contribution: float = Field(..., ge=0.0, description="Absolute magnitude of contribution")
    rank: int = Field(..., ge=1, description="Relative importance rank (1 = highest impact)")
    raw_feature_name: Optional[str] = Field(None, description="Original raw domain feature name before encoding/scaling")
    reconstructed_value: Optional[float] = Field(None, description="Reconstructed value for Autoencoder models")
    reconstruction_error: Optional[float] = Field(None, description="Squared reconstruction error for Autoencoder models")
    shap_value: Optional[float] = Field(None, description="Raw SHAP value if computed via TreeExplainer / KernelExplainer")
    baseline_value: Optional[float] = Field(None, description="Reference baseline value used for comparison/perturbation")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional feature-specific metadata")


class TimestepContribution(BaseModel):
    """
    Temporal sequence timestep attribution record for sequential models (LSTM).
    Identifies which time offset in a temporal event window exhibited the highest anomaly.
    """
    timestep_index: int = Field(..., ge=0, description="0-indexed position within sliding sequence window")
    timestep_label: str = Field(..., description="Human-readable label, e.g., 't_0', 't_1'")
    reconstruction_error: float = Field(..., ge=0.0, description="Mean squared reconstruction error across features at this step")
    anomaly_score: float = Field(..., ge=0.0, le=100.0, description="Normalized risk score for this specific timestep")
    relative_contribution: float = Field(..., ge=0.0, le=1.0, description="Fraction of total sequence error at this step")
    top_features: List[FeatureContribution] = Field(default_factory=list, description="Top anomalous features at this timestep")
    rank: int = Field(..., ge=1, description="Timestep error rank (1 = most anomalous timestep in sequence)")


class ModelExplanation(BaseModel):
    """
    Standardized explanation output for an individual machine learning model's prediction.
    """
    explanation_id: str = Field(default_factory=lambda: f"exp-{uuid.uuid4().hex[:12]}")
    model_name: str = Field(..., description="Name of the explained model (e.g., 'random_forest', 'autoencoder')")
    model_version: str = Field(default="1.0.0", description="Model version")
    dataset_name: str = Field(default="generic", description="Target dataset name")
    prediction: str = Field(..., description="'normal' or 'attack'")
    is_anomaly: bool = Field(..., description="True if classified as anomalous / attack")
    risk_score: float = Field(..., ge=0.0, le=100.0, description="Normalized risk score (0.0 to 100.0)")
    severity: str = Field(..., description="Threat severity: LOW, MEDIUM, HIGH, CRITICAL")
    decision_threshold: float = Field(..., description="Classification threshold applied")
    explanation_method: str = Field(..., description="Method used: 'shap_tree', 'isolation_forest_perturbation', 'autoencoder_reconstruction', etc.")
    top_k: int = Field(default=10, description="Number of top features requested")
    feature_contributions: List[FeatureContribution] = Field(default_factory=list, description="All top feature contributions ranked by absolute impact")
    top_positive_contributions: List[FeatureContribution] = Field(default_factory=list, description="Features increasing anomaly risk")
    top_negative_contributions: List[FeatureContribution] = Field(default_factory=list, description="Features decreasing anomaly risk (pushing toward normal)")
    timestep_contributions: Optional[List[TimestepContribution]] = Field(None, description="Timestep breakdown for sequential models")
    summary: str = Field(..., description="Dynamically generated human-readable natural language summary")
    limitations: List[str] = Field(default_factory=list, description="Explicit technical and causality limitations of the explanation")
    prediction_latency_ms: float = Field(default=0.0, ge=0.0, description="Inference time in milliseconds")
    explanation_latency_ms: float = Field(default=0.0, ge=0.0, description="Explanation calculation time in milliseconds")
    total_latency_ms: float = Field(default=0.0, ge=0.0, description="Total execution time in milliseconds")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional diagnostic metadata")

    def to_summary_dict(self) -> Dict[str, Any]:
        """Compact summary dictionary for high-level logging and telemetry."""
        return {
            "explanation_id": self.explanation_id,
            "model_name": self.model_name,
            "prediction": self.prediction,
            "risk_score": round(self.risk_score, 2),
            "severity": self.severity,
            "explanation_method": self.explanation_method,
            "top_positive_features": [f"{f.feature_name} (+{f.contribution:.4f})" for f in self.top_positive_contributions[:3]],
            "top_negative_features": [f"{f.feature_name} ({f.contribution:.4f})" for f in self.top_negative_contributions[:3]],
            "summary": self.summary,
            "total_latency_ms": round(self.total_latency_ms, 2),
        }


class EnsembleExplanation(BaseModel):
    """
    Standardized explanation output for the unified Ensemble Detection and Risk Scoring Engine.
    Combines model-level risk contributions, agreement metrics, and feature-level attributions.
    """
    explanation_id: str = Field(default_factory=lambda: f"ens-exp-{uuid.uuid4().hex[:12]}")
    model_name: str = "ensemble"
    model_version: str = "1.0.0"
    dataset_name: str = Field(default="generic", description="Target dataset name")
    prediction: str = Field(..., description="'normal' or 'attack'")
    is_anomaly: bool = Field(..., description="True if composite risk exceeds threshold")
    risk_score: float = Field(..., ge=0.0, le=100.0, description="Composite weighted risk score (0.0 to 100.0)")
    severity: str = Field(..., description="Severity level: LOW, MEDIUM, HIGH, CRITICAL")
    decision_threshold: float = Field(default=50.0, description="Ensemble cutoff threshold")
    reliability_score: float = Field(..., ge=0.0, le=1.0, description="Reliability score based on participating models")
    model_contributions: Dict[str, Dict[str, Any]] = Field(default_factory=dict, description="Per-model risk score, weight, and weighted contribution")
    participating_models: List[str] = Field(default_factory=list, description="List of actively participating models")
    missing_models: List[str] = Field(default_factory=list, description="List of unavailable models")
    agreement: Dict[str, Any] = Field(default_factory=dict, description="Consensus and agreement metrics")
    per_model_explanations: Dict[str, ModelExplanation] = Field(default_factory=dict, description="Individual model explanations where available")
    fused_feature_contributions: List[FeatureContribution] = Field(default_factory=list, description="Cross-model aggregated feature attributions when feature spaces match")
    summary: str = Field(..., description="Dynamically generated human-readable natural language summary")
    limitations: List[str] = Field(default_factory=list, description="Explicit ensemble explanation limitations")
    prediction_latency_ms: float = Field(default=0.0, ge=0.0, description="Ensemble inference latency in milliseconds")
    explanation_latency_ms: float = Field(default=0.0, ge=0.0, description="Explanation calculation latency in milliseconds")
    total_latency_ms: float = Field(default=0.0, ge=0.0, description="Total execution time in milliseconds")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def to_summary_dict(self) -> Dict[str, Any]:
        """Compact summary dictionary for high-level logging."""
        return {
            "explanation_id": self.explanation_id,
            "prediction": self.prediction,
            "risk_score": round(self.risk_score, 2),
            "severity": self.severity,
            "participating_models": self.participating_models,
            "missing_models": self.missing_models,
            "agreement_ratio": self.agreement.get("agreement_ratio", 1.0),
            "summary": self.summary,
            "total_latency_ms": round(self.total_latency_ms, 2),
        }


class ExplanationRequest(BaseModel):
    """
    Standard request payload to generate on-demand explainability for a model or ensemble.
    """
    model_name: str = Field(default="ensemble", description="Target model name: 'random_forest', 'isolation_forest', 'autoencoder', 'lstm_autoencoder', or 'ensemble'")
    dataset_name: str = Field(default="synthetic", description="Target dataset")
    top_k: int = Field(default=10, ge=1, le=50, description="Number of top features to return")
    include_visualizations: bool = Field(default=False, description="Whether to render and save visualization artifacts")
    background_samples: Optional[int] = Field(default=100, description="Number of background samples for perturbation/reference baselines")
