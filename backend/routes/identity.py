from __future__ import annotations

import structlog
from litestar import Request, Router, post
from litestar.exceptions import HTTPException

from lib.service_auth import authenticate_service_key
from schemas.identity import ResolveIdentityRequest, ResolveIdentityResponse
from services import identity as identity_service

logger = structlog.get_logger(__name__)


@post(
    "/identity/resolve",
    sync_to_thread=False,
    exclude_from_auth=True,
    status_code=200,
    operation_id="resolveIdentity",
)
async def resolve_identity_handler(
    request: Request,
    data: ResolveIdentityRequest,
) -> ResolveIdentityResponse:
    """Who-is-who for headless consumers (discord-bot, project-root).

    Auth is a per-service API key (``Authorization: Bearer svc_...``), not
    the user JWT — bots have no user session. 200 carries the servicing
    context, 404 means the Discord/external id is not linked yet.
    """
    key_row = await authenticate_service_key(request)
    try:
        result = await identity_service.resolve_identity(
            provider=data.provider,
            external_id=data.external_id,
            guild_id=data.guild_id,
            channel_id=data.channel_id,
        )
        logger.info(
            "identity resolve served",
            service_name=key_row.get("service_name"),
            provider=data.provider,
        )
        return result
    except HTTPException:
        raise
    except Exception:
        logger.exception("identity resolve failed")
        raise HTTPException(status_code=500, detail="Internal server error")


router = Router(
    path="",
    route_handlers=[resolve_identity_handler],
    tags=["identity"],
)
