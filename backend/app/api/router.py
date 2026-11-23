from fastapi import APIRouter
from app.api.routes import health, info
from app.providers import routes as provider_routes
from app.providers import model_routes
from app.conversations import routes as conversation_routes
from app.memory import routes as memory_routes
from app.tasks import routes as task_routes
from app.voice import routes as voice_routes
from app.tools.routes import tools_router, approvals_router
from app.automations.routes import router as automations_router
from app.integrations.routes import router as integrations_router
from app.notifications.routes import router as notifications_router
from app.briefings.routes import router as briefings_router

api_router = APIRouter()

# Register core diagnostics
api_router.include_router(health.router)
api_router.include_router(info.router)

# Register AI Providers, Model Registry & Policy, Conversations, Semantic Memory, Background Tasks, Voice, Tools, Approvals
api_router.include_router(provider_routes.router)
api_router.include_router(model_routes.router)
api_router.include_router(conversation_routes.router)
api_router.include_router(memory_routes.router)
api_router.include_router(task_routes.router)
api_router.include_router(voice_routes.router)
api_router.include_router(tools_router)
api_router.include_router(approvals_router)

# Register Phase 4 Automations, Integrations, Notifications, Briefings
api_router.include_router(automations_router)
api_router.include_router(integrations_router)
api_router.include_router(notifications_router)
api_router.include_router(briefings_router)


