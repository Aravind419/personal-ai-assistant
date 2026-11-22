from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class DatabaseHealth(BaseModel):
    connected: bool = Field(..., description="Whether the PostgreSQL database connection succeeded")
    latency_ms: Optional[float] = Field(None, description="Roundtrip query latency in milliseconds")
    error: Optional[str] = Field(None, description="Connection error message if failed")


class HealthResponse(BaseModel):
    status: str = Field(..., description="Overall service status ('healthy' or 'degraded')")
    app_name: str = Field(..., description="Application name")
    version: str = Field("0.1.0", description="Application version")
    environment: str = Field(..., description="Current environment (development, staging, production)")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Server UTC timestamp")
    database: DatabaseHealth = Field(..., description="PostgreSQL database connectivity check")


class SystemInfoResponse(BaseModel):
    app_name: str
    version: str
    phase: str = "Phase 0: Foundation"
    environment: str
    architecture: Dict[str, str] = Field(
        default_factory=lambda: {
            "frontend": "React + TypeScript + Tailwind CSS (Vite)",
            "backend": "Python + FastAPI",
            "database": "PostgreSQL (pgvector ready)",
            "future_orchestration": "LangGraph (Phase 1+)",
            "future_queue": "Redis + Celery (Phase 2+)",
            "future_provider": "OpenAI API via Provider Abstraction",
        }
    )
    status_summary: Dict[str, Any] = Field(
        default_factory=lambda: {
            "core_api": "active",
            "database_connectivity": "active",
            "ai_agent_orchestration": "disabled_by_design (Phase 0)",
            "memory_storage": "disabled_by_design (Phase 0)",
            "background_workers": "disabled_by_design (Phase 0)",
            "external_integrations": "disabled_by_design (Phase 0)",
        }
    )
