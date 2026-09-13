import time
from fastapi import APIRouter, HTTPException, Depends, status
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.database.connection import get_database, check_mongo_health
from backend.app.database.collections import ALL_COLLECTIONS
from backend.app.schemas.database import DatabaseTestResponse
from backend.app.auth.dependencies import require_admin
from backend.app.models.user import UserDocument

router = APIRouter()


@router.get("/status", response_model=DatabaseTestResponse, summary="MongoDB Database Connectivity Probe (Admin Only)")
async def get_database_status(
    current_user: UserDocument = Depends(require_admin),
):
    """
    Internal diagnostic endpoint to verify MongoDB connectivity and collection state.
    Does NOT leak connection strings, passwords, or credentials.
    """
    is_healthy, latency_ms, details = await check_mongo_health()
    db = get_database()

    if not is_healthy or db is None:
        return DatabaseTestResponse(
            status="disconnected",
            database_name=settings.MONGODB_DATABASE,
            connected=False,
            latency_ms=None,
            collections=[],
            collection_counts={},
            message="MongoDB is disconnected or unreachable. Backend is operating in degraded mode."
        )

    try:
        # Collect collection names and document counts securely
        existing_collections = await db.list_collection_names()
        counts = {}
        for coll_name in ALL_COLLECTIONS:
            if coll_name in existing_collections:
                counts[coll_name] = await db[coll_name].count_documents({})
            else:
                counts[coll_name] = 0

        return DatabaseTestResponse(
            status="connected",
            database_name=settings.MONGODB_DATABASE,
            connected=True,
            latency_ms=latency_ms,
            collections=existing_collections,
            collection_counts=counts,
            message="MongoDB connection is healthy and responsive."
        )

    except Exception as e:
        logger.error(f"Error querying database metadata: {str(e)}")
        return DatabaseTestResponse(
            status="error",
            database_name=settings.MONGODB_DATABASE,
            connected=False,
            latency_ms=latency_ms,
            collections=[],
            collection_counts={},
            message="MongoDB connection error occurred during status check."
        )
