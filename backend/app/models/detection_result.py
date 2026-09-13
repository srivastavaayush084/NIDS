from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, ConfigDict


class DetectionResultDocument(BaseModel):
    """MongoDB document model for model evaluation and zero-day detection outcomes."""
    id: Optional[str] = Field(None, alias="_id")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    network_log_id: Optional[str] = None
    model_name: str = Field(..., description="isolation_forest, autoencoder, lstm, random_forest, ensemble")
    prediction: bool = Field(..., description="True if flagged as anomalous, False otherwise")
    anomaly_score: float = Field(..., ge=0.0, le=1.0, description="Normalized score 0.0 to 1.0")
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    severity: str = Field(default="INFO", description="INFO, LOW, MEDIUM, HIGH, CRITICAL")
    contributing_features: List[Dict[str, Any]] = Field(default_factory=list)
    explanation: Optional[str] = None
    processing_time_ms: Optional[float] = None
    model_version: Optional[str] = "1.0.0"
    raw_details: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(populate_by_name=True)
