from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError

from app.core.config import settings
from app.core.logging import setup_logging, logger
from app.core.exceptions import (
    AppException,
    app_exception_handler,
    validation_exception_handler,
    generic_exception_handler,
)
from app.database.connection import check_database_connection
from app.api.router import api_router

# Setup application logging
setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup configuration verification and graceful shutdown.
    """
    logger.info(f"Starting {settings.APP_NAME} in '{settings.APP_ENV}' mode")
    logger.info(f"API Prefix: {settings.API_V1_STR}")
    logger.info(f"Configured CORS origins: {settings.CORS_ORIGINS}")
    logger.info(f"Database target: {settings.sanitized_database_url}")

    # Initial database connectivity check during startup
    db_status = await check_database_connection()
    if db_status["connected"]:
        logger.info(f"Database connection verified successfully (latency: {db_status['latency_ms']}ms)")
    else:
        logger.warning(
            f"Database connectivity check failed on startup ({db_status['error']}). "
            "The backend will run; database features will be available once PostgreSQL is running."
        )

    # Register Integration Providers and Tools
    try:
        from app.integrations.base import IntegrationRegistry
        from app.integrations.tools import register_integration_tools
        from app.briefings.service import GenerateMorningBriefingTool
        from app.tools.base import ToolRegistry

        IntegrationRegistry._ensure_defaults()
        register_integration_tools()
        ToolRegistry.register(GenerateMorningBriefingTool())
        logger.info("Initialized Phase 4 integrations, providers, and briefing tools.")
    except Exception as exc:
        logger.warning(f"Could not register Phase 4 integration tools on startup: {exc}")

    yield

    logger.info(f"Shutting down {settings.APP_NAME}...")


def create_application() -> FastAPI:
    """FastAPI application factory."""
    application = FastAPI(
        title=settings.APP_NAME,
        version="0.1.0",
        description=(
            "Phase 0 Engineering Foundation for Personal AI Agent. "
            "Provides core API shell, health checks, database connectivity, and configuration management."
        ),
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        docs_url=f"{settings.API_V1_STR}/docs",
        redoc_url=f"{settings.API_V1_STR}/redoc",
        lifespan=lifespan,
    )

    # Configure CORS
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    # Register Centralized Exception Handlers
    application.add_exception_handler(AppException, app_exception_handler)
    application.add_exception_handler(RequestValidationError, validation_exception_handler)
    application.add_exception_handler(Exception, generic_exception_handler)

    # Root route redirect/info
    @application.get("/", tags=["Root"])
    async def root():
        return {
            "name": settings.APP_NAME,
            "version": "0.1.0",
            "phase": "Phase 0: Foundation",
            "docs": f"{settings.API_V1_STR}/docs",
            "health": f"{settings.API_V1_STR}/health",
        }

    # Root health probe alias
    @application.get("/health", tags=["Root"])
    async def root_health():
        from app.services.health_service import HealthService
        return await HealthService.get_health_status()

    # Mount API routers
    application.include_router(api_router, prefix=settings.API_V1_STR)

    return application


app = create_application()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.BACKEND_HOST,
        port=settings.BACKEND_PORT,
        reload=settings.DEBUG,
    )
