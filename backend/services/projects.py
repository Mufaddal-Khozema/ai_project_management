from __future__ import annotations

from typing import Any

import httpx
import structlog

from litestar.exceptions import HTTPException

from config import settings
from lib import oauth
from lib.crypto import decrypt_token_payload
from repositories import (
    integration_repo,
    project_repo,
    user_repo,
    workspace_repo,
)
from schemas.project import UpsertProjectRequest

logger = structlog.get_logger(__name__)

SUPPORTED_PM_PROVIDERS = frozenset({"taiga"})
SUPPORTED_COMM_PROVIDERS = frozenset({"discord"})


def validate_provider_pair(pm_provider: str, comm_provider: str) -> None:
    if pm_provider not in SUPPORTED_PM_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Unsupported project provider: {pm_provider}")
    if comm_provider not in SUPPORTED_COMM_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Unsupported channel provider: {comm_provider}")
    if (pm_provider, comm_provider) != ("taiga", "discord"):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported provider pair: {pm_provider} + {comm_provider}",
        )


async def _workspace_id_for_user(email: str) -> int:
    user = await user_repo.find_by_email(email)
    if not user:
        logger.warning("user not found for project mapping", email=email)
        raise HTTPException(status_code=404, detail="User not found")
    workspace = await workspace_repo.find_by_user_id(user["id"])
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return workspace["id"]


async def _provider_payload(workspace_id: int, provider: str) -> dict[str, Any]:
    row = await integration_repo.find_by_workspace_provider(workspace_id, provider)
    if not row:
        raise HTTPException(status_code=404, detail=f"Integration not connected: {provider}")
    return decrypt_token_payload(row["token_encrypted"])


async def _provider_call(provider: str, coro: Any) -> Any:
    try:
        return await coro
    except httpx.HTTPError as exc:
        logger.warning("project mapping provider call failed", provider=provider, error=str(exc))
        raise HTTPException(
            status_code=502,
            detail=f"Could not reach {provider}. Please try again later.",
        ) from exc


async def _resolve_project(
    workspace_id: int, pm_provider: str, project_id: str
) -> tuple[str | None, str | None]:
    payload = await _provider_payload(workspace_id, pm_provider)
    access_token = payload.get("access_token") or ""
    projects = await _provider_call(
        pm_provider,
        oauth.list_taiga_projects(
            access_token, settings.taiga_base_url, payload.get("user_id")
        ),
    )
    project = next((p for p in projects if str(p.get("id")) == str(project_id)), None)
    if project is None:
        raise HTTPException(
            status_code=400,
            detail="Project not found or no longer accessible. Refresh and choose another.",
        )
    return project.get("name"), project.get("slug")


async def _resolve_guild(workspace_id: int, comm_provider: str, channel_id: str) -> str | None:
    payload = await _provider_payload(workspace_id, comm_provider)
    access_token = payload.get("access_token") or ""
    guild_id = await _provider_call(
        comm_provider,
        oauth.get_discord_channel_guild(
            access_token, settings.discord_bot_token, channel_id
        ),
    )
    if guild_id is None:
        raise HTTPException(
            status_code=400,
            detail="Channel not found or no longer accessible. Refresh and choose another.",
        )
    return guild_id


async def save_mapping(
    workspace_id: int,
    pm_provider: str,
    project_id: str,
    comm_provider: str,
    channel_id: str,
    active: bool = True,
) -> dict[str, Any]:
    """Validate a channel → project pair against the connected providers and store it."""
    validate_provider_pair(pm_provider, comm_provider)

    project_name, project_slug = await _resolve_project(
        workspace_id, pm_provider, project_id
    )
    guild_id = await _resolve_guild(workspace_id, comm_provider, channel_id)

    row = await project_repo.upsert(
        workspace_id=workspace_id,
        pm_provider=pm_provider,
        project_id=project_id,
        project_name=project_name,
        project_slug=project_slug,
        comm_provider=comm_provider,
        channel_id=channel_id,
        guild_id=guild_id,
        active=active,
    )
    logger.info(
        "project channel mapping saved",
        workspace_id=workspace_id,
        project_id=project_id,
        channel_id=channel_id,
        guild_id=guild_id,
    )
    return row


async def upsert_mapping(
    email: str, data: UpsertProjectRequest
) -> dict[str, Any]:
    workspace_id = await _workspace_id_for_user(email)
    return await save_mapping(
        workspace_id=workspace_id,
        pm_provider=data.pm_provider,
        project_id=data.project_id,
        comm_provider=data.comm_provider,
        channel_id=data.channel_id,
        active=data.active,
    )


async def list_mappings(email: str) -> list[dict[str, Any]]:
    workspace_id = await _workspace_id_for_user(email)
    return await project_repo.list_by_workspace(workspace_id)


async def delete_mapping(email: str, uuid: str) -> None:
    workspace_id = await _workspace_id_for_user(email)
    deleted = await project_repo.delete_by_uuid(workspace_id, uuid)
    if not deleted:
        raise HTTPException(status_code=404, detail="Mapping not found")
    logger.info("project channel mapping deleted", workspace_id=workspace_id, uuid=uuid)
