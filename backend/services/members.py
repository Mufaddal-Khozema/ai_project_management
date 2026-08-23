from __future__ import annotations

from typing import Any

import structlog

from litestar.exceptions import HTTPException

from config import settings
from lib import oauth
from lib.crypto import decrypt_token_payload
from repositories import (
    external_identity_repo,
    integration_repo,
    user_repo,
    workspace_member_repo,
    workspace_repo,
)

logger = structlog.get_logger(__name__)


def _resolve_owner(email: str) -> tuple[dict[str, Any], dict[str, Any]]:
    user = user_repo.find_by_email(email)
    if not user:
        logger.warning("user not found for member import", email=email)
        raise HTTPException(status_code=404, detail="User not found")
    workspace = workspace_repo.find_by_user_id(user["id"])
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return user, workspace


def _scope_payload(workspace_id: int, provider: str) -> dict[str, Any]:
    row = integration_repo.find_by_workspace_provider(workspace_id, provider)
    if not row:
        raise HTTPException(status_code=404, detail=f"Integration not connected: {provider}")
    return decrypt_token_payload(row["token_encrypted"])


async def _fetch_scope_members(
    workspace_id: int,
    email: str,
    provider: str,
    scope_id: str,
    *,
    is_project: bool,
) -> list[dict[str, Any]]:
    payload = _scope_payload(workspace_id, provider)
    access_token = payload.get("access_token") or ""

    if provider == "taiga" and is_project:
        return await oauth.list_taiga_project_members(
            access_token, settings.taiga_base_url, scope_id
        )
    if provider == "discord" and not is_project:
        guild_id = await oauth.get_discord_channel_guild(
            access_token, settings.discord_bot_token, scope_id
        )
        if guild_id is None:
            return []
        return await oauth.list_discord_guild_members(
            access_token, settings.discord_bot_token, guild_id
        )
    raise HTTPException(
        status_code=400,
        detail=f"Member scope not supported for provider: {provider}",
    )


def _identity_member(member: dict[str, Any]) -> dict[str, Any]:
    return {
        "email": member.get("email") or None,
        "name": member.get("name") or None,
        "username": member.get("username") or None,
        "avatar": member.get("avatar") or None,
    }


def _link_identity(
    user_id: int,
    provider: str,
    member: dict[str, Any],
) -> None:
    existing = external_identity_repo.find_by_provider_external_id(provider, member["id"])
    if existing:
        return
    external_identity_repo.create(
        user_id=user_id,
        provider=provider,
        external_id=member["id"],
        **_identity_member(member),
    )


def _resolve_or_create_user(
    pm_provider: str,
    comm_provider: str,
    pm_member: dict[str, Any],
    comm_member: dict[str, Any],
) -> int:
    email = pm_member.get("email") or comm_member.get("email") or None

    for provider, member in ((pm_provider, pm_member), (comm_provider, comm_member)):
        existing = external_identity_repo.find_by_provider_external_id(provider, member["id"])
        if existing and existing.get("user_id") is not None:
            return existing["user_id"]

    if email:
        existing_user = user_repo.find_by_email(email)
        if existing_user:
            return existing_user["id"]

    name = pm_member.get("name") or comm_member.get("name") or None
    avatar = pm_member.get("avatar") or comm_member.get("avatar") or None
    user = user_repo.create_pending_user(email=email, name=name, avatar=avatar)
    logger.info(
        "pending user created from onboarding match",
        user_id=user["id"],
        email=email,
        pm_provider=pm_provider,
        comm_provider=comm_provider,
    )
    return user["id"]


async def create_matched_users(
    email: str,
    pm_provider: str,
    comm_provider: str,
    project_id: str,
    channel_id: str,
    matches: list[dict[str, str]],
) -> list[dict[str, Any]]:
    """Create one user per matched (pm, comm) pair, linked to both platforms.

    The authenticated owner's own accounts (identified by the external id stored
    with each connected platform) are matched back to the existing user instead
    of creating a new pending user.
    """
    owner, workspace = _resolve_owner(email)
    owner_user_id = owner["id"]
    workspace_id = workspace["id"]

    pm_payload = _scope_payload(workspace_id, pm_provider)
    comm_payload = _scope_payload(workspace_id, comm_provider)
    pm_owner_external_id = str(pm_payload.get("user_id") or "")
    comm_owner_external_id = str(comm_payload.get("user_id") or "")

    pm_members = await _fetch_scope_members(
        workspace_id, email, pm_provider, project_id, is_project=True
    )
    comm_members = await _fetch_scope_members(
        workspace_id, email, comm_provider, channel_id, is_project=False
    )

    pm_by_id = {m["id"]: m for m in pm_members}
    comm_by_id = {m["id"]: m for m in comm_members}

    created: list[dict[str, Any]] = []
    for match in matches:
        pm_member = pm_by_id.get(match["pm_member_id"])
        comm_member = comm_by_id.get(match["comm_member_id"])
        if pm_member is None or comm_member is None:
            logger.warning(
                "match references unknown member",
                pm_member_id=match.get("pm_member_id"),
                comm_member_id=match.get("comm_member_id"),
            )
            raise HTTPException(status_code=400, detail="Match references a member outside the selected scope")

        is_owner = (
            pm_owner_external_id == str(pm_member["id"])
            or comm_owner_external_id == str(comm_member["id"])
        )
        if is_owner:
            user_id = owner_user_id
            role, status = "owner", "active"
            logger.info("matched member is the workspace owner", user_id=user_id)
        else:
            user_id = _resolve_or_create_user(pm_provider, comm_provider, pm_member, comm_member)
            role, status = "member", "pending"

        _link_identity(user_id, pm_provider, pm_member)
        _link_identity(user_id, comm_provider, comm_member)
        workspace_member_repo.add(workspace_id, user_id, role=role, status=status)

        created.append(
            {
                "user_id": user_id,
                "pm_member_id": pm_member["id"],
                "comm_member_id": comm_member["id"],
            }
        )

    return created