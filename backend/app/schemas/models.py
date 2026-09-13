from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class ModelMetrics(BaseModel):
    accuracy: Optional[float] = None
    precision: Optional[float] = None
    recall: Optional[float] = None
    f1_score: Optional[float] = None
    roc_auc: Optional[float] = None
    pr_auc: Optional[float] = None
    confusion_matrix: Optional[List[List[int]]] = None


class ModelInfo(BaseModel):
    model_id: str = Field(..., description="Unique model identifier (e.g. isolation_forest, autoencoder)")
    model_name: str = Field(..., description="Canonical model system name")
    display_name: str = Field(..., description="Human-readable model name")
    model_type: str = Field(..., description="Type category (Unsupervised Anomaly, Deep Reconstruction, Sequential, Supervised Baseline, Ensemble)")
    framework: Optional[str] = Field("scikit-learn / PyTorch", description="Underlying ML framework")
    version: str = Field("1.0.0", description="Model semantic version")
    is_trained: bool = Field(False, description="Whether trained weights/artifacts are loaded and active")
    is_active: bool = Field(True, description="Whether the model is currently active in the detection pipeline")
    threshold: Optional[float] = Field(None, description="Calibrated operational anomaly threshold if applicable")
    feature_count: Optional[int] = Field(None, description="Number of expected input features")
    description: Optional[str] = Field(None, description="Detailed functional description of the model")
    dataset_trained_on: Optional[str] = Field(None, description="Dataset used for training")
    metrics: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Evaluation metrics")
    hyperparameters: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Hyperparameters or configuration")
    registered_at: Optional[str] = Field(None, description="Registration timestamp ISO 8601")


class ModelListResponse(BaseModel):
    models: List[ModelInfo] = Field(..., description="List of registered ML models")
    total: int = Field(..., description="Total number of models returned")
    dataset: Optional[str] = Field(None, description="Dataset context filter if applied")
