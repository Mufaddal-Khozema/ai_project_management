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
from services.scrum_master import sync_ambient_channel

logger = structlog.get_logger(__name__)

SUPPORTED_PM_PROVIDERS = frozenset({"taiga", "jira"})
SUPPORTED_COMM_PROVIDERS = frozenset({"discord", "slack"})


def validate_provider_pair(pm_provider: str, comm_provider: str) -> None:
    if pm_provider not in SUPPORTED_PM_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Unsupported project provider: {pm_provider}")
    if comm_provider not in SUPPORTED_COMM_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Unsupported channel provider: {comm_provider}")


async def _workspace_for_user(email: str) -> dict[str, Any]:
    user = await user_repo.find_by_email(email)
    if not user:
        logger.warning("user not found for project mapping", email=email)
        raise HTTPException(status_code=404, detail="User not found")
    workspace = await workspace_repo.find_by_user_id(user["id"])
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return workspace


async def _workspace_id_for_user(email: str) -> int:
    workspace = await _workspace_for_user(email)
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
    if pm_provider == "taiga":
        projects = await _provider_call(
            pm_provider,
            oauth.list_taiga_projects(
                access_token, settings.taiga_base_url, payload.get("user_id")
            ),
        )
    elif pm_provider == "jira":
        projects = await _provider_call(
            pm_provider,
            oauth.list_jira_projects(access_token),
        )
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported project provider: {pm_provider}")
    project = next(
        (
            p for p in projects
            if str(p.get("id")) == str(project_id)
            or (p.get("slug") and str(p.get("slug")).upper() == str(project_id).upper())
        ),
        None,
    )
    if project is None:
        raise HTTPException(
            status_code=400,
            detail="Project not found or no longer accessible. Refresh and choose another.",
        )
    return project.get("name"), project.get("slug")


async def _resolve_guild(workspace_id: int, comm_provider: str, channel_id: str) -> str | None:
    payload = await _provider_payload(workspace_id, comm_provider)
    access_token = payload.get("access_token") or ""
    if comm_provider == "discord":
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
    elif comm_provider == "slack":
        team_id = await _provider_call(
            comm_provider,
            oauth.get_slack_channel_team(access_token, channel_id),
        )
        return team_id
    return None


async def save_mapping(
    workspace_id: int,
    pm_provider: str,
    project_id: str,
    comm_provider: str,
    channel_id: str,
    active: bool = True,
    voice_channel_id: str | None = None,
    ambient_enabled: bool = False,
    org_id: str | None = None,
) -> dict[str, Any]:
    """Validate a channel → project pair against the connected providers and store it."""
    validate_provider_pair(pm_provider, comm_provider)

    project_name, project_slug = await _resolve_project(
        workspace_id, pm_provider, project_id
    )
    guild_id = await _resolve_guild(workspace_id, comm_provider, channel_id)

    # Voice is currently exclusive to Discord (Slack voice is disabled until Zoom integration)
    effective_voice_channel_id = voice_channel_id if comm_provider == "discord" else None
    effective_ambient_enabled = ambient_enabled if (comm_provider == "discord" and effective_voice_channel_id) else False

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
        voice_channel_id=effective_voice_channel_id,
        ambient_enabled=effective_ambient_enabled,
    )
    logger.info(
        "project channel mapping saved",
        workspace_id=workspace_id,
        project_id=project_id,
        channel_id=channel_id,
        guild_id=guild_id,
        voice_channel_id=effective_voice_channel_id,
        ambient_enabled=effective_ambient_enabled,
    )

    if org_id and comm_provider == "discord":
        await sync_ambient_channel(
            org_id=org_id,
            guild_id=guild_id,
            channel_id=effective_voice_channel_id,
            enabled=effective_ambient_enabled,
        )

    return row


async def upsert_mapping(
    email: str, data: UpsertProjectRequest
) -> dict[str, Any]:
    workspace = await _workspace_for_user(email)
    workspace_id = workspace["id"]
    org_id = str(workspace.get("uuid") or workspace_id)
    return await save_mapping(
        workspace_id=workspace_id,
        pm_provider=data.pm_provider,
        project_id=data.project_id,
        comm_provider=data.comm_provider,
        channel_id=data.channel_id,
        active=data.active,
        voice_channel_id=data.voice_channel_id,
        ambient_enabled=data.ambient_enabled,
        org_id=org_id,
    )


async def list_mappings(email: str) -> list[dict[str, Any]]:
    workspace_id = await _workspace_id_for_user(email)
    return await project_repo.list_by_workspace(workspace_id)


async def delete_mapping(email: str, uuid: str) -> None:
    workspace = await _workspace_for_user(email)
    workspace_id = workspace["id"]
    existing = await project_repo.find_by_uuid(workspace_id, uuid)
    deleted = await project_repo.delete_by_uuid(workspace_id, uuid)
    if not deleted:
        raise HTTPException(status_code=404, detail="Mapping not found")
    if existing and existing.get("voice_channel_id") and existing.get("ambient_enabled"):
        org_id = str(workspace.get("uuid") or workspace_id)
        await sync_ambient_channel(
            org_id=org_id,
            guild_id=existing.get("guild_id"),
            channel_id=existing.get("voice_channel_id"),
            enabled=False,
        )
    logger.info("project channel mapping deleted", workspace_id=workspace_id, uuid=uuid)
