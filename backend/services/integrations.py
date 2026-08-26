from __future__ import annotations

import secrets
import time
from datetime import datetime, timezone
from typing import Any

import httpx
import structlog

from litestar.connection.request import Request
from litestar.exceptions import HTTPException

from config import settings
from lib import oauth
from lib.crypto import decrypt_token_payload, encrypt_token_payload
from lib.events import Events
from lib.oauth import OAuth2Token
from lib.tables import IntegrationStatus
from repositories import integration_repo, user_repo, workspace_repo

logger = structlog.get_logger(__name__)

_oauth_states: dict[str, dict[str, Any]] = {}
_STATE_TTL = 600


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _clean_states() -> None:
    now = time.time()
    expired = [s for s, d in _oauth_states.items() if now - d["ts"] > _STATE_TTL]
    for s in expired:
        _oauth_states.pop(s, None)


def store_oauth_state(provider: str, workspace_id: int, redirect_source: str) -> str:
    _clean_states()
    state = secrets.token_urlsafe(32)
    _oauth_states[state] = {
        "provider": provider,
        "workspace_id": workspace_id,
        "redirect_source": redirect_source,
        "ts": time.time(),
    }
    return state


def consume_oauth_state(state: str, provider: str) -> dict[str, Any] | None:
    stored = _oauth_states.pop(state, None)
    if not stored or stored["provider"] != provider:
        return None
    if time.time() - stored["ts"] > _STATE_TTL:
        return None
    return stored


def _resolve_workspace_id(email: str) -> int | None:
    user = user_repo.find_by_email(email)
    if not user:
        logger.warning("user not found for integration", email=email)
        raise HTTPException(status_code=404, detail="User not found")
    workspace = workspace_repo.find_by_user_id(user["id"])
    return workspace["id"] if workspace else None


def _effective_status(row: dict[str, Any]) -> str:
    status = row.get("status")
    if status == IntegrationStatus.connected.value:
        expires_at = row.get("expires_at")
        if expires_at is not None and expires_at < _utc_now():
            return IntegrationStatus.expired.value
    return status


def _normalize_expiry(expires_at: Any) -> datetime | None:
    if expires_at is None:
        return None
    if isinstance(expires_at, datetime):
        return expires_at.replace(tzinfo=None) if expires_at.tzinfo else expires_at
    try:
        return datetime.fromtimestamp(int(expires_at), tz=timezone.utc).replace(tzinfo=None)
    except (ValueError, OverflowError, TypeError):
        return None


def _scopes_string(token: OAuth2Token) -> str | None:
    scopes = token.get("scope")
    if not scopes:
        return None
    if isinstance(scopes, (list, tuple)):
        return " ".join(str(s) for s in scopes)
    return str(scopes)


def _build_token_payload(provider: str, token: OAuth2Token) -> dict[str, Any]:
    return {
        "access_token": token.get("access_token", ""),
        "refresh_token": token.get("refresh_token"),
        "expires_at": token.get("expires_at"),
        "instance_url": token.get("instance_url"),
        "account_name": token.get("account_name"),
        "user_id": token.get("user_id"),
        "scopes": token.get("scope"),
    }


def _as_utc(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    return value


def _to_response(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "uuid": row["uuid"],
        "provider": row["provider"],
        "account_name": row.get("account_name"),
        "status": _effective_status(row),
        "expires_at": _as_utc(row.get("expires_at")),
        "last_synced_at": _as_utc(row.get("last_synced_at")),
        "created_on": _as_utc(row["created_on"]),
        "updated_on": _as_utc(row["updated_on"]),
    }


def _upsert_row(
    workspace_id: int,
    provider: str,
    token_encrypted: str,
    account_name: str | None,
    scopes: str | None,
    status: str,
    expires_at: datetime | None,
) -> dict[str, Any]:
    existing = integration_repo.find_by_workspace_provider(workspace_id, provider)
    if existing:
        return integration_repo.update_token(
            existing["id"],
            token_encrypted,
            account_name,
            expires_at,
            status,
            existing.get("last_synced_at"),
        )
    return integration_repo.create(
        workspace_id, provider, token_encrypted, account_name, scopes, status, expires_at
    )


def _callback_redirect(provider: str, status: str, source: str) -> str:
    return (
        f"{settings.frontend_url}/integrations/callback"
        f"?provider={provider}&status={status}&source={source}"
    )


def list_integrations(email: str) -> list[dict[str, Any]]:
    workspace_id = _resolve_workspace_id(email)
    if workspace_id is None:
        return []
    rows = integration_repo.list_by_workspace(workspace_id)
    return [_to_response(row) for row in rows]


async def initiate_auth(
    email: str, provider: str, redirect_source: str, company_name: str | None = None
) -> dict[str, str]:
    if provider not in oauth.INTEGRATION_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Unsupported provider: {provider}")
    if not oauth.is_provider_configured(provider):
        raise HTTPException(status_code=400, detail=f"Provider not configured: {provider}")

    user = user_repo.find_by_email(email)
    if not user:
        logger.warning("user not found for integration connect", email=email)
        raise HTTPException(status_code=404, detail="User not found")

    workspace = workspace_repo.find_by_user_id(user["id"])
    if not workspace:
        workspace = workspace_repo.create(user["id"], {"company_name": company_name or "My Workspace"})
        logger.info(
            "workspace auto-created during integration connect",
            user_id=user["id"],
            provider=provider,
        )

    redirect_uri = f"{settings.app_url}/api/integrations/oauth/{provider}/callback"
    state = store_oauth_state(provider, workspace["id"], redirect_source)
    authorization_url = await oauth.get_authorization_url(provider, redirect_uri, state)
    return {"authorization_url": authorization_url}


async def handle_callback(provider: str, code: str, state: str, request: Request) -> str:
    stored = consume_oauth_state(state, provider)
    if not stored:
        logger.warning("oauth state invalid or stale", provider=provider)
        return _callback_redirect(provider, "error", "settings")

    redirect_source = stored["redirect_source"]
    workspace_id = stored["workspace_id"]

    try:
        redirect_uri = f"{settings.app_url}/api/integrations/oauth/{provider}/callback"
        token = await oauth.get_access_token(provider, code, redirect_uri)
    except Exception:
        logger.exception("oauth token exchange failed", provider=provider)
        return _callback_redirect(provider, "error", redirect_source)

    payload = _build_token_payload(provider, token)
    if provider == "discord" and not payload.get("user_id"):
        try:
            self_info = await oauth.get_discord_self(payload.get("access_token", ""))
            payload["user_id"] = str(self_info.get("id") or "")
        except Exception:
            logger.warning("could not resolve discord owner id", workspace_id=workspace_id)
    token_encrypted = encrypt_token_payload(payload)
    account_name = payload.get("account_name")
    scopes = _scopes_string(token)
    expires_at = _normalize_expiry(payload.get("expires_at"))
    _upsert_row(
        workspace_id,
        provider,
        token_encrypted,
        account_name,
        scopes,
        IntegrationStatus.connected.value,
        expires_at,
    )
    request.app.emit(Events.INTEGRATION_CONNECTED, provider=provider, workspace_id=workspace_id)
    logger.info("integration connected", provider=provider, workspace_id=workspace_id)
    return _callback_redirect(provider, "connected", redirect_source)


async def connect_taiga(email: str, username: str, password: str, request: Request) -> dict[str, Any]:
    user = user_repo.find_by_email(email)
    if not user:
        logger.warning("user not found for taiga connect", email=email)
        raise HTTPException(status_code=404, detail="User not found")

    workspace = workspace_repo.find_by_user_id(user["id"])
    if not workspace:
        workspace = workspace_repo.create(user["id"], {"company_name": "My Workspace"})

    try:
        token = await oauth.taiga_authenticate(username, password)
    except oauth.TaigaAuthError:
        logger.warning("taiga auth rejected", username=username)
        raise HTTPException(status_code=400, detail="Invalid Taiga credentials")
    except Exception:
        logger.exception("taiga auth request failed", username=username)
        raise HTTPException(status_code=502, detail="Could not reach Taiga")

    payload = _build_token_payload("taiga", token)
    token_encrypted = encrypt_token_payload(payload)
    account_name = payload.get("account_name")
    scopes = _scopes_string(token)
    expires_at = _normalize_expiry(payload.get("expires_at"))
    row = _upsert_row(
        workspace["id"],
        "taiga",
        token_encrypted,
        account_name,
        scopes,
        IntegrationStatus.connected.value,
        expires_at,
    )
    request.app.emit(Events.INTEGRATION_CONNECTED, provider="taiga", workspace_id=workspace["id"])
    logger.info("taiga connected", workspace_id=workspace["id"])
    return _to_response(row)


async def disconnect(email: str, provider: str, request: Request) -> None:
    workspace_id = _resolve_workspace_id(email)
    if workspace_id is None:
        raise HTTPException(status_code=404, detail="Integration not connected")

    row = integration_repo.find_by_workspace_provider(workspace_id, provider)
    if not row:
        raise HTTPException(status_code=404, detail="Integration not connected")

    try:
        payload = decrypt_token_payload(row["token_encrypted"])
        await oauth.revoke_access_token(provider, payload.get("access_token", ""))
    except Exception:
        logger.warning("token revocation failed", provider=provider, workspace_id=workspace_id)

    integration_repo.delete_by_workspace_provider(workspace_id, provider)
    request.app.emit(Events.INTEGRATION_DISCONNECTED, provider=provider, workspace_id=workspace_id)
    logger.info("integration disconnected", provider=provider, workspace_id=workspace_id)


async def _refresh_row(row: dict[str, Any], app) -> dict[str, Any] | None:
    integration_id = row["id"]
    provider = row["provider"]
    workspace_id = row["workspace_id"]

    payload = decrypt_token_payload(row["token_encrypted"])
    refresh_token = payload.get("refresh_token")
    if not refresh_token:
        return None

    try:
        new_token = await oauth.refresh_access_token(provider, refresh_token)
    except Exception:
        logger.warning("token refresh failed", provider=provider, workspace_id=workspace_id)
        updated = integration_repo.update_status(integration_id, IntegrationStatus.expired.value)
        app.emit(
            Events.INTEGRATION_TOKEN_REFRESHED,
            provider=provider,
            workspace_id=workspace_id,
            status=IntegrationStatus.expired.value,
        )
        return _to_response(updated)

    new_payload = _build_token_payload(provider, new_token)
    if not new_payload.get("refresh_token"):
        new_payload["refresh_token"] = refresh_token
    if not new_payload.get("user_id"):
        new_payload["user_id"] = payload.get("user_id")

    token_encrypted = encrypt_token_payload(new_payload)
    account_name = new_payload.get("account_name") or row.get("account_name")
    scopes = _scopes_string(new_token) or row.get("scopes")
    expires_at = _normalize_expiry(new_payload.get("expires_at"))
    updated = integration_repo.update_token(
        integration_id,
        token_encrypted,
        account_name,
        expires_at,
        IntegrationStatus.connected.value,
        row.get("last_synced_at"),
    )
    app.emit(
        Events.INTEGRATION_TOKEN_REFRESHED,
        provider=provider,
        workspace_id=workspace_id,
        status=IntegrationStatus.connected.value,
    )
    logger.info("integration token refreshed", provider=provider, workspace_id=workspace_id)

    return _to_response(updated)


async def refresh_integration(email: str, provider: str, request: Request) -> dict[str, Any]:
    workspace_id = _resolve_workspace_id(email)
    if workspace_id is None:
        raise HTTPException(status_code=404, detail="Integration not found")

    row = integration_repo.find_by_workspace_provider(workspace_id, provider)
    if not row:
        raise HTTPException(status_code=404, detail="Integration not found")

    result = await _refresh_row(row, request.app)
    if result is None:
        raise HTTPException(status_code=400, detail="Provider has no refresh token")
    return result


_MEMBER_PROVIDERS = frozenset({"taiga", "discord"})

_SCOPE_PROVIDERS = {
    "projects": frozenset({"taiga"}),
    "channels": frozenset({"discord"}),
}


def _scope_credentials(email: str, provider: str) -> tuple[dict[str, Any], dict[str, Any]]:
    workspace_id = _resolve_workspace_id(email)
    if workspace_id is None:
        raise HTTPException(status_code=404, detail="Integration not connected")
    row = integration_repo.find_by_workspace_provider(workspace_id, provider)
    if not row:
        raise HTTPException(status_code=404, detail="Integration not connected")
    return row, decrypt_token_payload(row["token_encrypted"])


async def _provider_call(provider: str, coro: Any) -> Any:
    try:
        return await coro
    except httpx.HTTPError as exc:
        logger.warning("integration provider call failed", provider=provider, error=str(exc))
        raise HTTPException(
            status_code=502,
            detail=f"Could not reach {provider}. Please try again later.",
        ) from exc


async def list_projects(email: str, provider: str) -> dict[str, Any]:
    if provider not in _SCOPE_PROVIDERS["projects"]:
        raise HTTPException(status_code=400, detail=f"Projects not supported for provider: {provider}")
    row, payload = _scope_credentials(email, provider)
    access_token = payload.get("access_token") or ""
    if provider == "taiga":
        scopes = await _provider_call(
            provider,
            oauth.list_taiga_projects(access_token, settings.taiga_base_url, payload.get("user_id")),
        )
    else:
        raise HTTPException(status_code=400, detail=f"Projects not supported for provider: {provider}")
    return {"provider": provider, "account_name": row.get("account_name"), "scopes": scopes}


async def list_project_members(email: str, provider: str, project_id: str) -> dict[str, Any]:
    if provider not in _SCOPE_PROVIDERS["projects"]:
        raise HTTPException(status_code=400, detail=f"Projects not supported for provider: {provider}")
    row, payload = _scope_credentials(email, provider)
    access_token = payload.get("access_token") or ""
    if provider == "taiga":
        members = await _provider_call(
            provider,
            oauth.list_taiga_project_members(access_token, settings.taiga_base_url, project_id),
        )
    else:
        raise HTTPException(status_code=400, detail=f"Projects not supported for provider: {provider}")
    return {"provider": provider, "account_name": row.get("account_name"), "members": members}


async def list_channels(email: str, provider: str) -> dict[str, Any]:
    if provider not in _SCOPE_PROVIDERS["channels"]:
        raise HTTPException(status_code=400, detail=f"Channels not supported for provider: {provider}")
    row, payload = _scope_credentials(email, provider)
    access_token = payload.get("access_token") or ""
    if provider == "discord":
        channels = await _provider_call(
            provider,
            oauth.list_discord_channels(access_token, settings.discord_bot_token),
        )
        scopes = [
            {
                "id": channel["id"],
                "name": channel["name"],
                "parent_id": channel["guild_id"],
            }
            for channel in channels
        ]
    else:
        raise HTTPException(status_code=400, detail=f"Channels not supported for provider: {provider}")
    return {"provider": provider, "account_name": row.get("account_name"), "scopes": scopes}


async def list_channel_members(email: str, provider: str, channel_id: str) -> dict[str, Any]:
    if provider not in _SCOPE_PROVIDERS["channels"]:
        raise HTTPException(status_code=400, detail=f"Channels not supported for provider: {provider}")
    row, payload = _scope_credentials(email, provider)
    access_token = payload.get("access_token") or ""
    if provider == "discord":
        guild_id = await _provider_call(
            provider,
            oauth.get_discord_channel_guild(
                access_token, settings.discord_bot_token, channel_id
            ),
        )
        if guild_id is None:
            raise HTTPException(status_code=404, detail="Channel not found or inaccessible")
        members = await _provider_call(
            provider,
            oauth.list_discord_guild_members(
                access_token, settings.discord_bot_token, guild_id
            ),
        )
    else:
        raise HTTPException(status_code=400, detail=f"Channels not supported for provider: {provider}")
    return {"provider": provider, "account_name": row.get("account_name"), "members": members}


async def list_members(email: str, provider: str) -> dict[str, Any]:
    if provider not in _MEMBER_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Member sync not supported for provider: {provider}")

    workspace_id = _resolve_workspace_id(email)
    if workspace_id is None:
        raise HTTPException(status_code=404, detail="Integration not found")

    row = integration_repo.find_by_workspace_provider(workspace_id, provider)
    if not row:
        raise HTTPException(status_code=404, detail="Integration not connected")

    payload = decrypt_token_payload(row["token_encrypted"])
    access_token = payload.get("access_token") or ""

    if provider == "taiga":
        members = await oauth.list_taiga_members(
            access_token, settings.taiga_base_url, payload.get("user_id")
        )
    elif provider == "discord":
        members = await oauth.list_discord_members(access_token, settings.discord_bot_token)
    else:
        raise HTTPException(status_code=400, detail=f"Member sync not supported for provider: {provider}")

    return {
        "provider": provider,
        "account_name": row.get("account_name"),
        "members": members,
    }
