from __future__ import annotations

from datetime import datetime, timezone

import structlog
from litestar.exceptions import HTTPException

from lib import identity_cache
from repositories import (
    external_identity_repo,
    integration_repo,
    payment_repo,
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


def resolve_identity(
    provider: str,
    external_id: str,
    guild_id: str | None = None,
    channel_id: str | None = None,
) -> ResolveIdentityResponse:
    """Answer "who is who": map an external id to its app servicing context.

    Raises 400 for unsupported providers, 404 when the external id is not
    linked to any app user (bots reply with a link hint). Never raises for
    a missing workspace or subscription — those come back as
    ``workspace=None`` / ``has_subscription=False`` so the caller can decide
    how to gate. ``guild_id``/``channel_id`` are accepted for the later
    multi-workspace disambiguation and logged, but not used for lookup yet.
    """
    normalized = provider.strip().lower()
    if normalized not in SUPPORTED_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Unsupported provider: {provider}")

    cache_key = identity_cache.make_identity_key(normalized, external_id)
    cached = identity_cache.cache_get(cache_key)
    if cached is not None:
        logger.info("identity resolve cache hit", provider=normalized)
        return ResolveIdentityResponse.model_validate(cached)

    link = external_identity_repo.find_by_provider_external_id(normalized, external_id)
    if link is None or link.get("user_id") is None:
        logger.info("identity resolve unlinked", provider=normalized)
        raise HTTPException(
            status_code=404,
            detail="Identity not linked. Run !link in Discord, then enter the code under Settings → Discord.",
        )

    user = user_repo.find_by_id(link["user_id"])
    if user is None:
        logger.warning("identity resolve link points at missing user", user_id=link["user_id"])
        raise HTTPException(status_code=404, detail="Identity not linked.")

    workspace = workspace_repo.find_by_member_id(user.id)

    integrations = (
        [
            IdentityIntegration(
                provider=row.get("provider"),
                account_name=row.get("account_name"),
                status=row.get("status"),
                token_encrypted=row.get("token_encrypted"),
            )
            for row in integration_repo.list_by_workspace(workspace["id"])
        ]
        if workspace is not None
        else []
    )

    # The subscription belongs to the workspace owner — members are covered
    # by the owner's plan, so entitlement is checked against the owner's id.
    owner_id = workspace["user_id"] if workspace is not None else None
    subscription = payment_repo.find_by_user_id(owner_id) if owner_id is not None else None
    response = ResolveIdentityResponse(
        linked=True,
        user=IdentityUser(
            uuid=user.uuid,
            email=user.email,
            status=user.status,
            name=user.name,
            avatar=user.avatar,
        ),
        workspace=(
            None
            if workspace is None
            else IdentityWorkspace(
                uuid=workspace["uuid"], company_name=workspace.get("company_name")
            )
        ),
        entitlements=IdentityEntitlements(
            has_subscription=subscription is not None,
            onboarding_completed=workspace is not None
            and workspace.get("onboarding_completed_at") is not None,
        ),
        integrations=integrations,
        cached_at=_utc_now(),
    )

    identity_cache.cache_set(cache_key, response.model_dump(mode="json"))

    logger.info(
        "identity resolved",
        provider=normalized,
        user_id=user.id,
        guild_id=guild_id,
        channel_id=channel_id,
    )
    return response


def invalidate_identity(provider: str, external_id: str) -> None:
    """Drop the cached resolve response. Called by link/unlink (Phase 2)."""
    identity_cache.cache_invalidate(provider.strip().lower(), external_id)
