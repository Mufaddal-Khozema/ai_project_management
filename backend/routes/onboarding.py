from __future__ import annotations

import structlog

from litestar import Request, Router, post
from litestar.exceptions import HTTPException
from litestar.response import Response

from schemas.workspace import OnboardingRequest, WorkspaceResponse
from services import onboarding as onboarding_service

logger = structlog.get_logger(__name__)


@post("/onboarding")
async def submit_onboarding(
    data: OnboardingRequest,
    request: Request,
) -> Response[WorkspaceResponse]:
    try:
        email = request.user.sub
        row, created = await onboarding_service.submit_onboarding(email, data)
        return Response(
            content=WorkspaceResponse(**row),
            status_code=201 if created else 200,
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception("onboarding submit failed")
        raise HTTPException(status_code=500, detail="Internal server error")


router = Router(
    path="",
    route_handlers=[submit_onboarding],
    tags=["onboarding"],
)
