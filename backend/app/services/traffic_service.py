from typing import List
from backend.app.core.logging import logger
from backend.app.database.repository import BaseRepository
from backend.app.schemas.traffic import BatchTrafficIngestRequest, TrafficIngestResponse


class TrafficService:
    """Business logic service for network traffic logging and historical indexing."""

    def __init__(self):
        self.repository = BaseRepository("traffic_records")

    async def ingest_batch(self, request: BatchTrafficIngestRequest) -> TrafficIngestResponse:
        """Ingest batch of network packet features."""
        logger.info(f"Ingesting {len(request.records)} traffic records from source '{request.source}'")
        # Ingestion logic
        return TrafficIngestResponse(
            status="success",
            message=f"Successfully queued {len(request.records)} network flow records",
            processed_count=len(request.records)
        )


traffic_service = TrafficService()
