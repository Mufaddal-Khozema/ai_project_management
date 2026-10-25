from __future__ import annotations

from datetime import datetime, timezone

import structlog
from litestar.exceptions import HTTPException

from lib import identity_cache
from repositories import (
    external_identity_repo,
    integration_repo,
    payment_repo,
    project_repo,
    user_repo,
    workspace_repo,
)
from schemas.identity import (
    IdentityEntitlements,
    IdentityIntegration,
    IdentityUser,
    IdentityWorkspace,
    ResolveIdentityResponse,
)

logger = structlog.get_logger(__name__)

# Providers a headless caller may resolve. Extended in Phase 2 alongside
# the link flow (discord first — discord-bot and voice both speak Discord).
SUPPORTED_PROVIDERS = frozenset({"discord"})


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


async def resolve_identity(
    provider: str,
    external_id: str,
    guild_id: str | None = None,
    channel_id: str | None = None,
) -> ResolveIdentityResponse:
    """Answer "who is who": map an external id to its app servicing context.

    Raises 400 for unsupported providers, 404 when the external id is not
    linked to any app user or the user has no workspace (bots reply with a
    link hint). Never raises for a missing subscription — it comes back as
    ``has_subscription=False`` so the caller can decide how to gate.

    The resolved response — including the channel's project mapping when
    ``channel_id`` is supplied — is cached per
    ``(provider, external_id, guild_id, channel_id)``.
    """
    normalized = provider.strip().lower()
    if normalized not in SUPPORTED_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Unsupported provider: {provider}")

    cache_key = identity_cache.make_identity_key(
        normalized, external_id, guild_id, channel_id
    )
    cached = await identity_cache.cache_get(cache_key)
    if cached is not None:
        logger.info("identity resolve cache hit", provider=normalized)
        return ResolveIdentityResponse.model_validate(cached)

    link = await external_identity_repo.find_by_provider_external_id(normalized, external_id)
    if link is None or link.user_id is None:
        logger.info("identity resolve unlinked", provider=normalized)
        raise HTTPException(
            status_code=404,
            detail="Identity not linked. Run !link in Discord, then enter the code under Settings → Discord.",
        )

    user = await user_repo.find_by_id(link.user_id)
    if user is None:
        logger.warning("identity resolve link points at missing user", user_id=link.user_id)
        raise HTTPException(status_code=404, detail="Identity not linked.")

    workspace = await workspace_repo.find_by_member_id(user.id)
    if workspace is None:
        logger.info("identity resolve no workspace", user_id=user.id)
        raise HTTPException(status_code=404, detail="Workspace not found")

    project = None
    if channel_id:
        project = await project_repo.find_by_channel(
            workspace.id, "discord", channel_id, guild_id
        )
        if project is None:
            logger.info(
                "identity channel mapping not found",
                workspace_id=workspace.id,
                channel_id=channel_id,
                guild_id=guild_id,
            )
        else:
            logger.info(
                "identity channel mapping found",
                channel_id=channel_id,
                guild_id=guild_id,
                workspace_id=workspace.id,
                project_id=project.project_id,
            )

    integrations = [
        IdentityIntegration(
            provider=row.provider,
            account_name=row.account_name,
            status=row.status,
            token_encrypted=row.token_encrypted,
        )
        for row in await integration_repo.list_by_workspace(workspace.id)
    ]

    # The subscription belongs to the workspace owner — members are covered
    # by the owner's plan, so entitlement is checked against the owner's id.
    subscription = await payment_repo.find_by_user_id(workspace.user_id)
    response = ResolveIdentityResponse(
        linked=True,
        user=IdentityUser(
            uuid=user.uuid,
            email=user.email,
            status=user.status,
            name=user.name,
            avatar=user.avatar,
        ),
        workspace=IdentityWorkspace(
            uuid=workspace.uuid, company_name=workspace.company_name
        ),
        project=project,
        entitlements=IdentityEntitlements(
            has_subscription=subscription is not None,
            onboarding_completed=workspace.onboarding_completed_at is not None,
        ),
        integrations=integrations,
        cached_at=_utc_now(),
    )
    await identity_cache.cache_set(cache_key, response.model_dump(mode="json"))

    logger.info(
        "identity resolved",
        provider=normalized,
        user_id=user.id,
        guild_id=guild_id,
        channel_id=channel_id,
        project_id=project.project_id if project else None,
    )
    return response


async def invalidate_identity(provider: str, external_id: str) -> None:
    """Drop the cached resolve response. Called by link/unlink (Phase 2)."""
    await identity_cache.cache_invalidate(provider.strip().lower(), external_id)
