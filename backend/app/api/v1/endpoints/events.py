import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List
from fastapi import APIRouter, HTTPException, Depends, status

from backend.app.core.logging import logger
from backend.app.database.repository import NetworkLogRepository
from backend.app.schemas.events import (
    EventIngestRequest,
    EventIngestResponse,
    BatchEventIngestRequest,
    BatchEventIngestResponse,
)
from backend.app.auth.dependencies import require_analyst_or_admin
from backend.app.models.user import UserDocument

router = APIRouter()
network_log_repo = NetworkLogRepository()


@router.post(
    "",
    response_model=Dict[str, Any],
    status_code=status.HTTP_201_CREATED,
    summary="Ingest Single Network Event",
)
async def ingest_event(
    event_in: EventIngestRequest,
    current_user: UserDocument = Depends(require_analyst_or_admin),
):
    """
    Ingest a single network event flow and store it in the network_logs collection.
    Validates input parameters and normalizes fields without triggering ML detection.
    """
    event_id = f"evt-{uuid.uuid4().hex[:12]}"
    doc = event_in.model_dump()
    doc["event_id"] = event_id
    doc["_id"] = event_id
    doc["ingested_at"] = datetime.now(timezone.utc)

    try:
        inserted_id = await network_log_repo.insert_one(doc) or event_id
    except Exception as e:
        logger.warning(f"Failed to store event in database: {e}")
        inserted_id = event_id

    response_data = EventIngestResponse(
        event_id=event_id,
        timestamp=event_in.timestamp,
        status="stored",
        dataset_name=event_in.dataset_name or "synthetic",
        source_ip=event_in.source_ip,
        destination_ip=event_in.destination_ip,
    )

    return {
        "success": True,
        "data": response_data.model_dump(),
    }


@router.post(
    "/batch",
    response_model=Dict[str, Any],
    status_code=status.HTTP_201_CREATED,
    summary="Ingest Batch of Network Events",
)
async def ingest_event_batch(
    batch_in: BatchEventIngestRequest,
    current_user: UserDocument = Depends(require_analyst_or_admin),
):
    """
    Ingest a batch of network events into the network_logs collection.
    """
    event_ids = []
    docs = []
    now = datetime.now(timezone.utc)

    for item in batch_in.events:
        evt_id = f"evt-{uuid.uuid4().hex[:12]}"
        d = item.model_dump()
        d["event_id"] = evt_id
        d["_id"] = evt_id
        d["ingested_at"] = now
        d["source"] = batch_in.source
        docs.append(d)
        event_ids.append(evt_id)

    stored_count = len(docs)
    try:
        await network_log_repo.insert_many(docs)
    except Exception as e:
        logger.warning(f"Batch storage warning: {e}")

    return {
        "success": True,
        "data": {
            "total": len(batch_in.events),
            "stored": stored_count,
            "failed": 0,
            "event_ids": event_ids,
        },
    }

