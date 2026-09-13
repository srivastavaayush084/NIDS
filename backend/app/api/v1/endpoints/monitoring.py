import logging
from typing import Dict, Optional
from fastapi import APIRouter, HTTPException, Query, Depends, status

from backend.app.monitoring.features.feature_mapper import FeatureMapper
from backend.app.monitoring.manager import monitoring_manager
from backend.app.monitoring.schemas import (
    InterfaceListResponse,
    ModelCompatibilityReport,
    MonitoringStartRequest,
    MonitoringStatusResponse,
    MonitoringStopResponse,
    PCAPTestRequest,
    PCAPTestResponse,
)
from backend.app.auth.dependencies import require_analyst_or_admin, require_any_authenticated
from backend.app.models.user import UserDocument

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/start",
    response_model=MonitoringStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Start Real-Time Network Monitoring",
    description="Initiates live interface packet sniffing or streaming PCAP file replay into the ML detection pipeline.",
)
async def start_monitoring(
    request: MonitoringStartRequest,
    current_user: UserDocument = Depends(require_analyst_or_admin),
) -> MonitoringStatusResponse:
    try:
        status_res = await monitoring_manager.start(request)
        return status_res
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to start monitoring session: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start monitoring session: {str(e)}",
        )


@router.post(
    "/stop",
    response_model=MonitoringStopResponse,
    status_code=status.HTTP_200_OK,
    summary="Stop Real-Time Network Monitoring",
    description="Stops active packet capture, flushes in-flight flows, drains the buffer, and returns session telemetry.",
)
async def stop_monitoring(
    current_user: UserDocument = Depends(require_analyst_or_admin),
) -> MonitoringStopResponse:
    try:
        res = await monitoring_manager.stop()
        return res
    except Exception as e:
        logger.error(f"Failed to stop monitoring session: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stop monitoring: {str(e)}",
        )


@router.get(
    "/status",
    response_model=MonitoringStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Network Monitoring Telemetry and Health Status",
    description="Returns real-time packets/sec, flows/sec, buffer utilization, anomaly counts, and model compatibility.",
)
async def get_monitoring_status(
    current_user: UserDocument = Depends(require_any_authenticated),
) -> MonitoringStatusResponse:
    return monitoring_manager.get_status()


@router.post(
    "/test-pcap",
    response_model=PCAPTestResponse,
    status_code=status.HTTP_200_OK,
    summary="Inspect and Replay PCAP File (Isolated Test)",
    description="Synchronously replays a PCAP capture, extracts flows, runs full ensemble detection, and returns an analytical benchmark report.",
)
async def test_pcap_file(
    request: PCAPTestRequest,
    current_user: UserDocument = Depends(require_analyst_or_admin),
) -> PCAPTestResponse:
    try:
        res = await monitoring_manager.test_pcap(request)
        return res
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"PCAP inspection failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"PCAP inspection failed: {str(e)}",
        )


@router.get(
    "/interfaces",
    response_model=InterfaceListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Detected Network Capture Interfaces",
    description="Enumerates available network adapters on the host system along with capture driver readiness.",
)
async def list_network_interfaces(
    current_user: UserDocument = Depends(require_any_authenticated),
) -> InterfaceListResponse:
    return monitoring_manager.get_interfaces()


@router.get(
    "/compatibility",
    response_model=Dict[str, ModelCompatibilityReport],
    status_code=status.HTTP_200_OK,
    summary="Get Model Feature Compatibility Matrix",
    description="Checks whether the monitoring feature extractor meets the feature requirements for all models.",
)
async def get_model_compatibility(
    dataset_name: Optional[str] = Query(default="synthetic", description="Target dataset name"),
    current_user: UserDocument = Depends(require_any_authenticated),
) -> Dict[str, ModelCompatibilityReport]:
    return FeatureMapper.get_all_compatibility(dataset_name or "synthetic")


