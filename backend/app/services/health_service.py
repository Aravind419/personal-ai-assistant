from datetime import datetime, timezone
from app.core.config import settings
from app.database.connection import check_database_connection
from app.schemas.health import HealthResponse, DatabaseHealth, SystemInfoResponse


class HealthService:
    @staticmethod
    async def get_health_status() -> HealthResponse:
        db_check = await check_database_connection()
        db_health = DatabaseHealth(
            connected=db_check["connected"],
            latency_ms=db_check["latency_ms"],
            error=db_check["error"],
        )

        overall_status = "healthy" if db_health.connected else "degraded"

        return HealthResponse(
            status=overall_status,
            app_name=settings.APP_NAME,
            version="0.1.0",
            environment=settings.APP_ENV,
            timestamp=datetime.now(timezone.utc),
            database=db_health,
        )

    @staticmethod
    def get_system_info() -> SystemInfoResponse:
        return SystemInfoResponse(
            app_name=settings.APP_NAME,
            version="0.1.0",
            phase="Phase 0: Foundation",
            environment=settings.APP_ENV,
        )
