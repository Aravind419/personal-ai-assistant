import pytest
from httpx import AsyncClient
from fastapi import APIRouter
from app.main import app
from app.core.exceptions import AppException, ResourceNotFoundException

# Add an error router to verify exception handling behavior
error_test_router = APIRouter(prefix="/test-errors")


@error_test_router.get("/custom-error")
async def trigger_custom_error():
    raise AppException("Custom operation failed", status_code=400, details={"field": "test"})


@error_test_router.get("/not-found")
async def trigger_not_found():
    raise ResourceNotFoundException("Test item not found")


# Register error router
app.include_router(error_test_router)


@pytest.mark.asyncio
async def test_app_exception_handler(async_client: AsyncClient):
    response = await async_client.get("/test-errors/custom-error")
    assert response.status_code == 400
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "AppException"
    assert data["error"]["message"] == "Custom operation failed"
    assert data["error"]["details"] == {"field": "test"}


@pytest.mark.asyncio
async def test_resource_not_found_handler(async_client: AsyncClient):
    response = await async_client.get("/test-errors/not-found")
    assert response.status_code == 404
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "ResourceNotFoundException"
    assert data["error"]["message"] == "Test item not found"
