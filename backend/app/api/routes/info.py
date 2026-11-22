from fastapi import APIRouter, status
from app.schemas.health import SystemInfoResponse
from app.services.health_service import HealthService

router = APIRouter(prefix="/info", tags=["System Information"])


@router.get(
    "",
    response_model=SystemInfoResponse,
    status_code=status.HTTP_200_OK,
    summary="System and Architecture Metadata",
    description="Returns metadata about the architectural foundation and active Phase 0 capabilities.",
)
async def get_system_info():
    return HealthService.get_system_info()
