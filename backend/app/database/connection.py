import time
from typing import Dict, Any
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from sqlalchemy import text
from app.core.config import settings
from app.core.logging import logger

def get_engine_url() -> str:
    url = settings.DATABASE_URL
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgresql://") and not url.startswith("postgresql+"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url

# Create global async engine
engine: AsyncEngine = create_async_engine(
    get_engine_url(),
    echo=False,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

async def check_database_connection(timeout_seconds: float = 3.0) -> Dict[str, Any]:
    """
    Performs a live connectivity check against the configured PostgreSQL database.
    Executes 'SELECT 1' and measures latency.
    """
    start_time = time.perf_counter()
    try:
        async with engine.connect() as conn:
            # Enforce execution
            result = await conn.execute(text("SELECT 1"))
            row = result.scalar()
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            if row == 1:
                return {
                    "connected": True,
                    "latency_ms": latency_ms,
                    "error": None,
                }
            return {
                "connected": False,
                "latency_ms": latency_ms,
                "error": "Unexpected query result",
            }
    except Exception as exc:
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        logger.warning(f"Database health check failed ({latency_ms}ms): {str(exc)}")
        return {
            "connected": False,
            "latency_ms": latency_ms,
            "error": str(exc),
        }
