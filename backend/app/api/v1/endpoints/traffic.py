from fastapi import APIRouter, Depends
from backend.app.schemas.traffic import BatchTrafficIngestRequest, TrafficIngestResponse
from backend.app.services.traffic_service import traffic_service
from backend.app.auth.dependencies import require_analyst_or_admin
from backend.app.models.user import UserDocument

router = APIRouter()


@router.post("/ingest", response_model=TrafficIngestResponse, summary="Ingest Network Traffic Batch")
async def ingest_traffic(
    request: BatchTrafficIngestRequest,
    current_user: UserDocument = Depends(require_analyst_or_admin),
):
    """Ingest packet logs / network traffic flow records."""
    return await traffic_service.ingest_batch(request)

