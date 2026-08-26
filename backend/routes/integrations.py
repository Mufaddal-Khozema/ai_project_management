from __future__ import annotations

import structlog

from litestar import Request, Router, get, post
from litestar.exceptions import HTTPException
from litestar.response import Redirect

from lib import oauth
from schemas.integration import (
    DisconnectResponse,
    InitiateAuthRequest,
    InitiateAuthResponse,
    IntegrationMembersResponse,
    IntegrationResponse,
    IntegrationScopesResponse,
    IntegrationsListResponse,
    TaigaConnectRequest,
)
from services import integrations as integration_service

logger = structlog.get_logger(__name__)


def _validate_provider(provider: str) -> None:
    if provider not in oauth.INTEGRATION_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Unsupported provider: {provider}")


@get("/integrations", sync_to_thread=False)
async def list_integrations(request: Request) -> IntegrationsListResponse:
    email = request.user.sub
    items = integration_service.list_integrations(email)
    return IntegrationsListResponse(
        integrations=[IntegrationResponse(**item) for item in items]
    )


@post("/integrations/{provider:str}/auth", status_code=200, sync_to_thread=False)
async def initiate_auth(
    provider: str,
    data: InitiateAuthRequest,
    request: Request,
) -> InitiateAuthResponse:
    _validate_provider(provider)
    email = request.user.sub
    result = await integration_service.initiate_auth(
        email, provider, data.redirect_source, data.company_name
    )
    return InitiateAuthResponse(**result)


@get(
    "/integrations/oauth/{provider:str}/callback",
    sync_to_thread=False,
    exclude_from_auth=True,
)
async def oauth_callback(provider: str, request: Request) -> Redirect:
    _validate_provider(provider)
    params = request.query_params
    code = params.get("code")
    state = params.get("state")
    error = params.get("error")

    if error or not code or not state:
        logger.warning("integration oauth callback error", provider=provider, error=error)
        return Redirect(integration_service._callback_redirect(provider, "error", "settings"))

    redirect_url = await integration_service.handle_callback(provider, code, state, request)
    return Redirect(redirect_url)


@post("/integrations/taiga/connect", status_code=200, sync_to_thread=False)
async def connect_taiga(data: TaigaConnectRequest, request: Request) -> IntegrationResponse:
    email = request.user.sub
    row = await integration_service.connect_taiga(email, data.username, data.password, request)
    return IntegrationResponse(**row)


@post("/integrations/{provider:str}/disconnect", status_code=200, sync_to_thread=False)
async def disconnect(provider: str, request: Request) -> DisconnectResponse:
    _validate_provider(provider)
    email = request.user.sub
    await integration_service.disconnect(email, provider, request)
    return DisconnectResponse(message="disconnected")


@post("/integrations/{provider:str}/refresh", status_code=200, sync_to_thread=False)
async def refresh(provider: str, request: Request) -> IntegrationResponse:
    _validate_provider(provider)
    email = request.user.sub
    row = await integration_service.refresh_integration(email, provider, request)
    return IntegrationResponse(**row)


@get("/integrations/{provider:str}/members", sync_to_thread=False)
async def list_members(provider: str, request: Request) -> IntegrationMembersResponse:
    _validate_provider(provider)
    email = request.user.sub
    result = await integration_service.list_members(email, provider)
    return IntegrationMembersResponse(**result)


@get("/integrations/{provider:str}/projects", sync_to_thread=False)
async def list_projects(provider: str, request: Request) -> IntegrationScopesResponse:
    _validate_provider(provider)
    email = request.user.sub
    result = await integration_service.list_projects(email, provider)
    return IntegrationScopesResponse(**result)


@get("/integrations/{provider:str}/projects/{project_id:str}/members", sync_to_thread=False)
async def list_project_members(provider: str, project_id: str, request: Request) -> IntegrationMembersResponse:
    _validate_provider(provider)
    email = request.user.sub
    result = await integration_service.list_project_members(email, provider, project_id)
    return IntegrationMembersResponse(**result)


@get("/integrations/{provider:str}/channels", sync_to_thread=False)
async def list_channels(provider: str, request: Request) -> IntegrationScopesResponse:
    _validate_provider(provider)
    email = request.user.sub
    result = await integration_service.list_channels(email, provider)
    return IntegrationScopesResponse(**result)


@get("/integrations/{provider:str}/channels/{channel_id:str}/members", sync_to_thread=False)
async def list_channel_members(provider: str, channel_id: str, request: Request) -> IntegrationMembersResponse:
    _validate_provider(provider)
    email = request.user.sub
    result = await integration_service.list_channel_members(email, provider, channel_id)
    return IntegrationMembersResponse(**result)


router = Router(
    path="",
    route_handlers=[
        list_integrations,
        initiate_auth,
        oauth_callback,
        connect_taiga,
        disconnect,
        refresh,
        list_members,
        list_projects,
        list_project_members,
        list_channels,
        list_channel_members,
    ],
    tags=["integrations"],
)