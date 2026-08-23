from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any

import structlog

from config import settings
from repositories import integration_repo
from services.integrations import _refresh_row

logger = structlog.get_logger(__name__)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


async def refresh_due_tokens(app) -> int:
    refresh_before = _utc_now() + timedelta(minutes=settings.integration_token_refresh_lead_minutes)
    rows = integration_repo.list_refreshable(refresh_before)
    processed = 0
    for row in rows:
        try:
            if await _refresh_row(row, app) is not None:
                processed += 1
        except Exception:
            logger.warning(
                "background token refresh failed",
                provider=row.get("provider"),
                integration_id=row.get("id"),
                workspace_id=row.get("workspace_id"),
            )
    if processed:
        logger.info(
            "background token refresh completed",
            refreshed=processed,
            scanned=len(rows),
        )
    return processed


async def token_refresh_loop(app) -> None:
    interval_seconds = settings.integration_token_refresh_interval_minutes * 60
    while True:
        try:
            await refresh_due_tokens(app)
        except Exception:
            logger.exception("token refresh loop iteration failed")
        await asyncio.sleep(interval_seconds)


def start_background_tasks(app) -> None:
    if not settings.integration_token_refresh_enabled:
        logger.info("integration token refresh disabled")
        return
    asyncio.create_task(token_refresh_loop(app))