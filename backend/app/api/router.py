from fastapi import APIRouter
from app.api.routes import health, info
from app.providers import routes as provider_routes
from app.providers import model_routes
from app.conversations import routes as conversation_routes
from app.memory import routes as memory_routes
from app.tasks import routes as task_routes

api_router = APIRouter()

# Register core diagnostics
api_router.include_router(health.router)
api_router.include_router(info.router)

# Register AI Providers, Model Registry & Policy, Conversations, Semantic Memory, and Background Tasks
api_router.include_router(provider_routes.router)
api_router.include_router(model_routes.router)
api_router.include_router(conversation_routes.router)
api_router.include_router(memory_routes.router)
api_router.include_router(task_routes.router)
