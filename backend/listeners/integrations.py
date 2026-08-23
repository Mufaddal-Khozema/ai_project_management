from __future__ import annotations

import structlog

from litestar.events import listener

from lib.events import Events

logger = structlog.get_logger(__name__)


@listener(Events.INTEGRATION_CONNECTED)
async def on_integration_connected(provider: str, workspace_id: int) -> None:
    logger.info("integration connected", provider=provider, workspace_id=workspace_id)


@listener(Events.INTEGRATION_DISCONNECTED)
async def on_integration_disconnected(provider: str, workspace_id: int) -> None:
    logger.info("integration disconnected", provider=provider, workspace_id=workspace_id)


@listener(Events.INTEGRATION_TOKEN_REFRESHED)
async def on_integration_token_refreshed(provider: str, workspace_id: int, status: str) -> None:
    logger.info(
        "integration token refreshed",
        provider=provider,
        workspace_id=workspace_id,
        status=status,
    )