from fastapi import APIRouter
from backend.app.api.v1.endpoints import (
    auth,
    users,
    health,
    events,
    detection,
    alerts,
    models,
    statistics,
    traffic,
    database,
    monitoring,
)

api_router = APIRouter()

# Register sub-routers under /api/v1
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users.router, prefix="/users", tags=["User Management"])
api_router.include_router(health.router, tags=["Health"])
api_router.include_router(events.router, prefix="/events", tags=["Events Ingestion"])
api_router.include_router(detection.router, prefix="/detection", tags=["Detection Pipeline"])
api_router.include_router(alerts.router, prefix="/alerts", tags=["Security Alerts"])
api_router.include_router(models.router, prefix="/models", tags=["ML Models Registry"])
api_router.include_router(statistics.router, prefix="/statistics", tags=["System Statistics"])
api_router.include_router(traffic.router, prefix="/traffic", tags=["Traffic Ingestion - Legacy"])
api_router.include_router(monitoring.router, prefix="/monitoring", tags=["Network Monitoring & PCAP Ingestion"])
api_router.include_router(database.router, prefix="/database", tags=["Database Management"])

