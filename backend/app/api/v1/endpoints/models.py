from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query, Depends, status
from backend.app.ml.model_manager import model_manager
from backend.app.ml.registry.model_registry import model_registry
from backend.app.schemas.models import ModelListResponse, ModelInfo
from backend.app.core.logging import logger
from backend.app.auth.dependencies import require_any_authenticated
from backend.app.models.user import UserDocument

router = APIRouter()

MODEL_CATALOG = {
    "isolation_forest": {
        "model_id": "isolation_forest",
        "model_name": "isolation_forest",
        "display_name": "Isolation Forest",
        "model_type": "Unsupervised Anomaly Detection",
        "framework": "scikit-learn",
        "description": "Tree-based unsupervised anomaly detection isolating unusual points via random feature partitioning.",
    },
    "autoencoder": {
        "model_id": "autoencoder",
        "model_name": "autoencoder",
        "display_name": "Deep Autoencoder",
        "model_type": "Deep Learning / Reconstruction Anomaly Detection",
        "framework": "PyTorch",
        "description": "Multi-layer deep autoencoder network learning non-linear normal traffic manifolds via reconstruction loss.",
    },
    "lstm_autoencoder": {
        "model_id": "lstm_autoencoder",
        "model_name": "lstm_autoencoder",
        "display_name": "LSTM Temporal Autoencoder",
        "model_type": "Sequential Deep Learning / Temporal Reconstruction",
        "framework": "PyTorch",
        "description": "Recurrent LSTM sequence autoencoder capturing temporal event correlations and multi-step attack patterns.",
    },
    "random_forest": {
        "model_id": "random_forest",
        "model_name": "random_forest",
        "display_name": "Random Forest Classifier",
        "model_type": "Supervised Baseline Classifier",
        "framework": "scikit-learn",
        "description": "Ensemble of decision trees trained on labeled traffic data serving as a supervised benchmark baseline.",
    },
    "ensemble": {
        "model_id": "ensemble",
        "model_name": "ensemble",
        "display_name": "Unified Ensemble Detection & Risk Engine",
        "model_type": "Multi-Model Ensemble",
        "framework": "ZeroDayAI Core Engine",
        "description": "Unified meta-detection engine synthesizing unsupervised point anomalies, deep reconstruction, sequence analysis, and supervised classifiers into a calibrated risk score (0-100).",
    }
}


def _build_model_info(model_key: str, dataset: Optional[str] = None) -> Optional[ModelInfo]:
    """Helper to build safe ModelInfo metadata for a model key."""
    norm_key = model_key.lower().strip()
    if norm_key == "lstm":
        norm_key = "lstm_autoencoder"

    if norm_key not in MODEL_CATALOG:
        # Check if there is an entry in the registry
        reg_entry = model_registry.get_model(norm_key, dataset=dataset, active_only=False)
        if not reg_entry:
            return None
        catalog_info = {
            "model_id": norm_key,
            "model_name": reg_entry.get("model_name", norm_key),
            "display_name": reg_entry.get("model_name", norm_key).replace("_", " ").title(),
            "model_type": reg_entry.get("model_type", "Machine Learning Model"),
            "framework": "Custom / Machine Learning",
            "description": f"Registered ML model {norm_key}",
        }
    else:
        catalog_info = MODEL_CATALOG[norm_key]

    # Look up registry metadata
    reg_meta = model_registry.get_model(norm_key, dataset=dataset, active_only=False)
    if not reg_meta and norm_key == "lstm_autoencoder":
        reg_meta = model_registry.get_model("lstm", dataset=dataset, active_only=False)

    # Cross-reference with in-memory model manager status
    status_dict = model_manager.get_model_status(dataset=dataset)
    mgr_key = "lstm" if norm_key == "lstm_autoencoder" else norm_key
    mgr_status = status_dict.get(mgr_key, {})

    is_trained = False
    if norm_key == "ensemble":
        is_trained = any(v.get("is_trained", False) for v in status_dict.values())
    elif mgr_status:
        is_trained = bool(mgr_status.get("is_trained", False))
    elif reg_meta:
        is_trained = True

    # Get threshold and safe hyperparameters
    threshold: Optional[float] = None
    feature_count: Optional[int] = None
    if reg_meta:
        feature_count = reg_meta.get("feature_count")
        threshold = (reg_meta.get("metrics") or {}).get("threshold")
    
    # Check active status
    is_active = True
    if reg_meta:
        is_active = reg_meta.get("is_active", True)

    version = (reg_meta.get("version") if reg_meta else None) or (mgr_status.get("version") if mgr_status else None) or "1.0.0"
    reg_at = reg_meta.get("registered_at") if reg_meta else None
    dataset_name = reg_meta.get("dataset") if reg_meta else (dataset or "synthetic")
    
    # Safe metrics (omit raw paths)
    raw_metrics = reg_meta.get("metrics", {}) if reg_meta else {}
    safe_metrics = {k: v for k, v in raw_metrics.items() if not str(k).endswith("path") and not str(k).endswith("file")}

    # Safe hyperparameters
    raw_params = reg_meta.get("hyperparameters", {}) if reg_meta else {}
    safe_params = {k: v for k, v in raw_params.items() if not str(k).endswith("path")}

    return ModelInfo(
        model_id=catalog_info["model_id"],
        model_name=catalog_info["model_name"],
        display_name=catalog_info["display_name"],
        model_type=catalog_info["model_type"],
        framework=catalog_info["framework"],
        version=version,
        is_trained=is_trained,
        is_active=is_active,
        threshold=float(threshold) if threshold is not None else None,
        feature_count=feature_count,
        description=catalog_info["description"],
        dataset_trained_on=dataset_name,
        metrics=safe_metrics,
        hyperparameters=safe_params,
        registered_at=reg_at,
    )


@router.get("", response_model=ModelListResponse, summary="List Registered AI/ML Models")
async def list_models(
    dataset: Optional[str] = Query(None, description="Optional dataset filter (e.g. synthetic, cicids2017)"),
    current_user: UserDocument = Depends(require_any_authenticated),
):
    """
    Retrieve operational metadata, architecture types, training status, and safe metrics
    for all detection models registered in the ZeroDayAI platform.
    """
    logger.info(f"Listing registered ML models (dataset={dataset})")
    model_list: List[ModelInfo] = []

    for model_key in MODEL_CATALOG:
        info = _build_model_info(model_key, dataset=dataset)
        if info:
            model_list.append(info)

    return ModelListResponse(
        models=model_list,
        total=len(model_list),
        dataset=dataset
    )


@router.get("/{model_name}", response_model=ModelInfo, summary="Get Model Details")
async def get_model_detail(
    model_name: str,
    dataset: Optional[str] = Query(None, description="Optional dataset filter"),
    current_user: UserDocument = Depends(require_any_authenticated),
):
    """
    Retrieve comprehensive metadata, configuration, calibrated thresholds,
    and performance metrics for a specific machine learning model.
    """
    norm_key = model_name.lower().strip()
    logger.info(f"Fetching model details for: {norm_key} (dataset={dataset})")
    
    info = _build_model_info(norm_key, dataset=dataset)
    if not info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model '{model_name}' not found in registry. Available models: {', '.join(MODEL_CATALOG.keys())}"
        )
    return info
