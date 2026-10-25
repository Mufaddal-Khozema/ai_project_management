from litestar import Router

from .auth import router as auth_router
from .health import router as health_router
from .identity import router as identity_router
from .integrations import router as integrations_router
from .onboarding import router as onboarding_router
from .payments import router as payments_router
from .projects import router as projects_router
from .social import router as social_router
from .users import router as users_router

api_router = Router(
    path="/api",
    route_handlers=[health_router, auth_router, social_router, payments_router, users_router, onboarding_router, integrations_router, projects_router, identity_router],
)
