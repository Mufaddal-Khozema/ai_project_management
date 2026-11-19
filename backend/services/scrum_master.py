from __future__ import annotations

from typing import Any
import httpx
import structlog

from config import settings

logger = structlog.get_logger(__name__)


async def sync_ambient_channel(
    org_id: str,
    guild_id: str | None,
    channel_id: str | None,
    enabled: bool,
) -> None:
    """Sync ambient channel configuration with scrum-master-ai.

    Fails gracefully without breaking project persistence if scrum-master-ai is unreachable.
    """
    if not guild_id or not channel_id:
        return

    base_url = settings.scrum_master_url.rstrip("/")
    url = f"{base_url}/integrations/ambient/channels"
    headers: dict[str, str] = {
        "x-org-id": str(org_id),
        "Content-Type": "application/json",
    }
    if settings.internal_service_key:
        headers["x-internal-key"] = settings.internal_service_key
        headers["Authorization"] = f"Bearer {settings.internal_service_key}"

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                channels: list[dict[str, Any]] = resp.json()
                existing = next(
                    (
                        c
                        for c in channels
                        if str(c.get("guildId")) == str(guild_id)
                        and str(c.get("channelId")) == str(channel_id)
                    ),
                    None,
                )
                if existing:
                    existing_id = existing.get("id")
                    if existing.get("enabled") != enabled and existing_id:
                        if enabled:
                            await client.patch(
                                f"{url}/{existing_id}",
                                json={"enabled": True},
                                headers=headers,
                            )
                        else:
                            await client.delete(f"{url}/{existing_id}", headers=headers)
                    return

            if enabled:
                await client.post(
                    url,
                    json={
                        "guildId": str(guild_id),
                        "channelId": str(channel_id),
                        "enabled": True,
                    },
                    headers=headers,
                )
    except Exception as exc:
        logger.warning(
            "ambient channel sync with scrum-master-ai failed gracefully",
            org_id=org_id,
            guild_id=guild_id,
            channel_id=channel_id,
            enabled=enabled,
            error=str(exc),
        )
