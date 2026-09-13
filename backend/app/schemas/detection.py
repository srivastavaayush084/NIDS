import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field

from backend.app.schemas.traffic import NetworkPacketFeature


# =============================================================================
# Sub-component Models
# =============================================================================

class ModelPredictionItem(BaseModel):
    """Detailed score and prediction breakdown for an individual model."""
    name: str
    prediction: str = Field(..., description="'normal' or 'attack'")
    is_anomaly: bool
    native_score: float
    normalized_score: float
    weight: float
    weighted_contribution: float
    latency_ms: float = 0.0
    is_available: bool = True
    error: Optional[str] = None


class ModelAgreementSummary(BaseModel):
    """Consensus agreement metrics across active detection engines."""
    models_total: int
    models_available: int
    models_anomalous: int
    models_normal: int = 0
    agreement_ratio: float = Field(..., ge=0.0, le=1.0)
    consensus_prediction: str


class XAIExplanationSummary(BaseModel):
    """Attached Explainable AI feature attribution summary."""
    is_available: bool = True
    explanation_id: Optional[str] = None
    method: Optional[str] = "ensemble_risk_attribution"
    summary: str
    top_features: List[Dict[str, Any]] = Field(default_factory=list)
    peak_timestep: Optional[str] = None
    error: Optional[str] = None


class AlertOutcomeSummary(BaseModel):
    """Incident alert generation and deduplication summary."""
    created: bool = False
    alert_id: Optional[str] = None
    deduplicated: bool = False
    occurrence_count: int = 0
    severity: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    reason: Optional[str] = None


# =============================================================================
# Single Detection Schemas
# =============================================================================

class SingleDetectionRequest(BaseModel):
    """Payload for running detection on a single network event flow."""
    features: Dict[str, Any] = Field(..., description="Network flow features (e.g., src_bytes, dst_bytes, count, duration, etc.)")
    dataset_name: Optional[str] = Field(default="synthetic", description="Target dataset/preprocessor pipeline ('synthetic', 'nsl_kdd', 'cicids2017', 'unsw_nb15')")
    generate_xai: Optional[bool] = Field(default=True, description="Whether to compute and attach XAI explanations")
    flow_context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Network connection endpoints (source_ip, destination_ip, ports, protocol)")


class SingleDetectionResponse(BaseModel):
    """Standardized detection result returned for a single network event."""
    detection_id: str
    timestamp: datetime
    dataset_name: str = "synthetic"
    prediction: str = Field(..., description="'normal' or 'attack'")
    is_anomaly: bool
    risk_score: float = Field(..., ge=0.0, le=100.0, description="Composite normalized risk score (0.0 to 100.0)")
    severity: str = Field(..., description="Threat severity tier: LOW, MEDIUM, HIGH, CRITICAL")
    threshold: float = 50.0
    model_agreement: ModelAgreementSummary
    models: List[ModelPredictionItem] = Field(default_factory=list)
    explanation: Optional[XAIExplanationSummary] = None
    alert: Optional[AlertOutcomeSummary] = None
    flow_context: Optional[Dict[str, Any]] = None
    processing_time_ms: float = 0.0


# =============================================================================
# Batch Detection Schemas
# =============================================================================

class BatchDetectionRequest(BaseModel):
    """Payload for batch detection across multiple network flow events."""
    events: List[Dict[str, Any]] = Field(..., min_length=1, max_length=500, description="List of network event feature dictionaries (max 500)")
    dataset_name: Optional[str] = Field(default="synthetic", description="Target dataset/pipeline")
    generate_xai: Optional[bool] = Field(default=False, description="Whether to generate XAI attributions (defaults to False for fast batch processing)")


class BatchDetectionResponse(BaseModel):
    """Batch detection processing summary."""
    total: int
    successful: int
    failed: int
    anomalies: int
    alerts_created: int
    processing_time_ms: float
    results: List[SingleDetectionResponse] = Field(default_factory=list)
    errors: List[Dict[str, Any]] = Field(default_factory=list)


# =============================================================================
# Sequence Detection Schemas
# =============================================================================

class SequenceDetectionRequest(BaseModel):
    """Payload for sequential time-series detection (LSTM Autoencoder)."""
    sequence: List[Dict[str, Any]] = Field(..., min_length=2, max_length=100, description="Consecutive time-ordered event window (max 100)")
    dataset_name: Optional[str] = Field(default="synthetic", description="Target dataset/pipeline")
    generate_xai: Optional[bool] = Field(default=True, description="Whether to generate temporal timestep explanations")
    flow_context: Optional[Dict[str, Any]] = Field(default_factory=dict)


class SequenceDetectionResponse(BaseModel):
    """Sequence-level anomaly detection outcome."""
    detection_id: str
    detection_type: str = "sequence_detection"
    timestamp: datetime
    dataset_name: str = "synthetic"
    prediction: str = Field(..., description="'normal' or 'attack'")
    is_anomaly: bool
    risk_score: float = Field(..., ge=0.0, le=100.0)
    severity: str
    reconstruction_error: float
    threshold: float
    sequence_length: int
    peak_anomalous_timestep: Optional[str] = None
    explanation: Optional[XAIExplanationSummary] = None
    alert: Optional[AlertOutcomeSummary] = None
    processing_time_ms: float = 0.0


# =============================================================================
# Detection History & Filtering Schemas
# =============================================================================

class DetectionFilterParams(BaseModel):
    """Query parameters for searching historical detection results."""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    severity: Optional[str] = None
    prediction: Optional[str] = None
    is_anomaly: Optional[bool] = None
    min_risk_score: Optional[float] = None
    dataset_name: Optional[str] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


# =============================================================================
# Backwards Compatibility Layer (Phases 1-2 schemas)
# =============================================================================

class FeatureContribution(BaseModel):
    feature_name: str
    contribution_score: float
    description: Optional[str] = None


class ModelPrediction(BaseModel):
    model_name: str
    is_anomaly: bool
    raw_score: float
    confidence: float


class DetectionResult(BaseModel):
    flow_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_zero_day_suspect: bool = False
    risk_score: float = Field(..., ge=0.0, le=1.0)
    severity: str = "LOW"
    model_predictions: Dict[str, ModelPrediction] = Field(default_factory=dict)
    top_contributing_features: List[FeatureContribution] = Field(default_factory=list)
    explanation: Optional[str] = None


class DetectionRequest(BaseModel):
    flow: NetworkPacketFeature
    active_models: Optional[List[str]] = Field(
        default=["isolation_forest", "autoencoder", "lstm", "random_forest"]
    )
