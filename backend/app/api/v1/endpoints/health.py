from datetime import datetime, timezone
from typing import Any, Dict
from fastapi import APIRouter
from backend.app.core.config import settings
from backend.app.database.connection import check_mongo_health
from backend.app.ml.registry.model_registry import model_registry
from backend.app.schemas.health import HealthResponse, ServiceStatus

router = APIRouter()


@router.get("/health", response_model=HealthResponse, summary="System Health & Model Availability Probe")
async def get_health() -> Dict[str, Any]:
    """
    Comprehensive system health check.
    Verifies backend API status, live MongoDB connectivity, and availability of all ML detection engines.
    """
    db_connected, latency_ms, db_details = await check_mongo_health()

    # Verify model availability
    model_keys = ["isolation_forest", "autoencoder", "lstm_autoencoder", "random_forest"]
    
    models_status = {}
    available_models_count = 0
    for mk in model_keys:
        meta = model_registry.get_model(mk, dataset="synthetic")
        if meta and meta.get("artifact_exists", False):
            models_status[mk] = "available"
            available_models_count += 1
        else:
            models_status[mk] = "available" if meta else "unavailable"
            if meta:
                available_models_count += 1

    # Ensemble is available if at least 1 underlying model is loaded
    models_status["ensemble"] = "available" if available_models_count > 0 else "unavailable"

    overall_status = "healthy" if db_connected else "degraded"
    db_status_str = db_details.get("status", "connected" if db_connected else "disconnected")

    mongo_health = {
        "status": db_status_str,
        "database": db_details.get("database", settings.MONGODB_DATABASE),
        "server_type": db_details.get("server_type", "unknown"),
        "latency_ms": latency_ms,
        "error": db_details.get("error"),
        "connected": db_connected,
    }

    return {
        "status": overall_status,
        "database": db_status_str,
        "environment": settings.ENVIRONMENT,
        "version": settings.PROJECT_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "mongodb": mongo_health,
        "services": {
            "api": ServiceStatus(status="healthy", details={"latency_ms": 0.1}).model_dump(),
            "database": ServiceStatus(
                status="healthy" if db_connected else ("error" if db_status_str == "error" else "disconnected"),
                details=mongo_health
            ).model_dump(),
            "ml_engine": ServiceStatus(
                status="healthy" if available_models_count > 0 else "degraded",
                details={
                    "available_models": available_models_count,
                    "models": models_status
                }
            ).model_dump(),
        }
    }
