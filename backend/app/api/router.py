from fastapi import APIRouter
from app.api.routes import health, info

api_router = APIRouter()

# Register routes under /api/v1
api_router.include_router(health.router)
api_router.include_router(info.router)
