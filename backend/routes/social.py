from __future__ import annotations

import secrets
import time
from datetime import timedelta
from typing import Any

import structlog

from litestar import Request, Router, get
from litestar.exceptions import HTTPException
from litestar.response import Redirect

from config import settings
from lib.auth import jwt_auth, set_refresh_cookie
from lib.oauth import get_access_token, get_authorization_url, get_user_info
from repositories import user_repo

logger = structlog.get_logger(__name__)

_oauth_states: dict[str, dict[str, Any]] = {}
_STATE_TTL = 600


def _clean_states() -> None:
    now = time.time()
    expired = [s for s, d in _oauth_states.items() if now - d["ts"] > _STATE_TTL]
    for s in expired:
        _oauth_states.pop(s, None)


@get("/auth/{provider:str}/login", sync_to_thread=False)
async def social_login(provider: str) -> Redirect:
    _clean_states()
    if provider not in ("google", "github"):
        raise HTTPException(status_code=400, detail=f"Unsupported provider: {provider}")
    state = secrets.token_urlsafe(32)
    _oauth_states[state] = {"provider": provider, "ts": time.time()}
    redirect_uri = f"{settings.app_url}/api/auth/{provider}/callback"
    auth_url = await get_authorization_url(provider, redirect_uri, state)
    return Redirect(auth_url)


@get("/auth/{provider:str}/callback", sync_to_thread=False)
async def social_callback(provider: str, request: Request) -> Redirect:
    params = request.query_params
    code = params.get("code")
    state = params.get("state")
    error = params.get("error")

    if error or not code or not state:
        logger.warning("oauth callback error", provider=provider, error=error)
        return Redirect(f"{settings.frontend_url}/signup?error=oauth_failed")

    stored = _oauth_states.pop(state, None)
    if not stored or stored["provider"] != provider:
        logger.warning("oauth state mismatch", provider=provider)
        return Redirect(f"{settings.frontend_url}/signup?error=oauth_failed")

    try:
        redirect_uri = f"{settings.app_url}/api/auth/{provider}/callback"
        token = await get_access_token(provider, code, redirect_uri)
        user_info = await get_user_info(provider, token)

        email = user_info["email"]
        name = user_info.get("name", "")
        sub = user_info["sub"]

        user = user_repo.find_by_email(email)
        if user:
            user_repo.update_social_login(user["id"], provider, sub, name, current_status=user["status"])
        else:
            user_repo.create_social_user(email, name, provider, sub)

        jwt_token = jwt_auth.create_token(
            identifier=email,
            token_expiration=timedelta(minutes=settings.jwt_expire_minutes),
        )

        response = Redirect(f"{settings.frontend_url}/signup?token={jwt_token}&provider={provider}")
        set_refresh_cookie(response, email)
        logger.info("social login successful", provider=provider, email=email)
        return response

    except HTTPException:
        raise
    except Exception:
        logger.exception("social callback failed", provider=provider)
        return Redirect(f"{settings.frontend_url}/signup?error=oauth_failed")


router = Router(
    path="",
    route_handlers=[social_login, social_callback],
    tags=["auth"],
)
