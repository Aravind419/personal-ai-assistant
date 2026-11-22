from fastapi import APIRouter
from app.api.routes import health, info
from app.providers import routes as provider_routes
from app.conversations import routes as conversation_routes

api_router = APIRouter()

# Register core diagnostics
api_router.include_router(health.router)
api_router.include_router(info.router)

# Register AI Providers & Conversations
api_router.include_router(provider_routes.router)
api_router.include_router(conversation_routes.router)
