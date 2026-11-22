from fastapi import APIRouter, status
from app.schemas.health import HealthResponse, DatabaseHealth
from app.services.health_service import HealthService
from app.database.connection import check_database_connection

router = APIRouter(prefix="/health", tags=["Health & Diagnostics"])


@router.get(
    "",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Application Health Check",
    description="Returns backend uptime, environment, and PostgreSQL database connectivity status.",
)
async def get_health():
    return await HealthService.get_health_status()


@router.get(
    "/db",
    response_model=DatabaseHealth,
    status_code=status.HTTP_200_OK,
    summary="Database Connectivity Check",
    description="Performs an isolated ping test against PostgreSQL to verify connectivity and latency.",
)
async def check_db_health():
    res = await check_database_connection()
    return DatabaseHealth(
        connected=res["connected"],
        latency_ms=res["latency_ms"],
        error=res["error"],
    )
