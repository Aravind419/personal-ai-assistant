import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_root_endpoint(async_client: AsyncClient):
    response = await async_client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert "version" in data
    assert data["phase"] == "Phase 0: Foundation"
    assert data["docs"] == "/api/v1/docs"
    assert data["health"] == "/api/v1/health"


@pytest.mark.asyncio
async def test_health_check_endpoint(async_client: AsyncClient):
    response = await async_client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] in ["healthy", "degraded"]
    assert "app_name" in data
    assert "environment" in data
    assert "timestamp" in data
    assert "database" in data
    assert isinstance(data["database"]["connected"], bool)


@pytest.mark.asyncio
async def test_database_health_endpoint(async_client: AsyncClient):
    response = await async_client.get("/api/v1/health/db")
    assert response.status_code == 200
    data = response.json()
    assert "connected" in data
    assert isinstance(data["connected"], bool)


@pytest.mark.asyncio
async def test_info_endpoint(async_client: AsyncClient):
    response = await async_client.get("/api/v1/info")
    assert response.status_code == 200
    data = response.json()
    assert data["phase"] == "Phase 0: Foundation"
    assert "architecture" in data
    assert data["architecture"]["backend"] == "Python + FastAPI"
    assert data["architecture"]["database"] == "PostgreSQL (pgvector ready)"
    assert "status_summary" in data
    assert data["status_summary"]["core_api"] == "active"
    assert data["status_summary"]["ai_agent_orchestration"] == "disabled_by_design (Phase 0)"
