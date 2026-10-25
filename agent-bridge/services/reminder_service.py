"""
services/reminder_service.py — Proactive due-date reminder service for Taiga.
Periodically scans active project channels, detects items approaching due date,
and posts Discord bot reminders tagging assignees (with de-duplication).
"""
from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Any

from core.base import CommunicationPlatform, OutgoingMessage, ProjectManagementPlatform

logger = logging.getLogger("agent_bridge.reminders")


class DueDateReminderService:
    def __init__(
        self,
        comm: CommunicationPlatform,
        pm: ProjectManagementPlatform,
        channel_map: dict | None = None,
        redis_client: Any = None,
        interval_seconds: int = 1800,
        days_ahead: int = 2,
    ):
        self.comm = comm
        self.pm = pm
        self.channel_map = channel_map or {}
        self.redis_client = redis_client
        self.interval_seconds = interval_seconds
        self.days_ahead = days_ahead
        self._running = False
        self._in_memory_cache: dict[str, float] = {}

    def _get_active_channel_map(self) -> dict:
        """Resolve channel map from instance or communication platform config."""
        if self.channel_map:
            return self.channel_map
        if hasattr(self.comm, "_config"):
            return self.comm._config.get("channel_map", {})
        return {}

    def _is_recently_reminded(self, key: str) -> bool:
        if self.redis_client:
            try:
                val = self.redis_client.get(key)
                if val:
                    return True
            except Exception as e:
                logger.warning("Redis check failed in DueDateReminderService: %s", e)
        # Fallback to in-memory cache
        expiry = self._in_memory_cache.get(key)
        return bool(expiry and expiry > time.time())

    def _mark_reminded(self, key: str, ttl_seconds: int = 86400) -> None:
        if self.redis_client:
            try:
                self.redis_client.setex(key, ttl_seconds, "1")
                return
            except Exception as e:
                logger.warning("Redis setex failed in DueDateReminderService: %s", e)
        # Fallback to in-memory cache
        self._in_memory_cache[key] = time.time() + ttl_seconds

    def get_pending_reminders(self) -> list[tuple[str, str, str, str, str]]:
        """
        Inspect all mapped channels and due items, returning tuples of
        (guild_id, channel_id, assignee, cache_key, message_content) for reminders not yet sent.
        """
        pending = []
        channel_map = self._get_active_channel_map()
        now_date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        for guild_id, channels in channel_map.items():
            if not isinstance(channels, dict):
                continue
            for channel_id, project_slug in channels.items():
                if not project_slug:
                    continue
                try:
                    project_id = self.pm.get_project_id(str(project_slug))
                    if not project_id:
                        continue

                    due_items = self.pm.get_due_items(str(project_id), days_ahead=self.days_ahead)
                    if not due_items:
                        continue

                    for item in due_items:
                        item_id = str(item.get("id", ""))
                        due_date = str(item.get("due_date", ""))
                        item_type = str(item.get("type", "item"))
                        ref = str(item.get("ref", item_id))
                        subject = item.get("subject", "")
                        assignee = item.get("assigned_to") or "unassigned"

                        cache_key = f"taiga_due_remind:{project_id}:{item_type}:{item_id}:{due_date}"
                        if self._is_recently_reminded(cache_key):
                            continue

                        # Determine urgency
                        if due_date < now_date_str:
                            urgency_header = "⚠️ **OVERDUE TASK REMINDER**"
                            due_text = f"was due on **{due_date}**"
                        elif due_date == now_date_str:
                            urgency_header = "⏰ **TASK DUE TODAY**"
                            due_text = f"is due **today ({due_date})**"
                        else:
                            urgency_header = "⏰ **TASK DUE SOON**"
                            due_text = f"is due on **{due_date}**"

                        assignee_tag = f"@{assignee}" if assignee != "unassigned" else "*Unassigned*"

                        msg_content = (
                            f"{urgency_header}\n"
                            f"**#{ref} [{item_type.capitalize()}]** {subject}\n"
                            f"👤 **Assignee**: {assignee_tag}\n"
                            f"📅 **Deadline**: {due_text}\n\n"
                            f"💡 *Need more time? Reply with:* `@FYP extend due date of #{ref} to YYYY-MM-DD because <reason>`\n"
                            f"*(Note: Extending due date will notify all watchers/stakeholders)*"
                        )

                        pending.append((str(guild_id), str(channel_id), assignee, cache_key, msg_content))

                except Exception as e:
                    logger.error("Error processing reminders for channel %s (%s): %s", channel_id, project_slug, e)

        return pending

    async def check_and_send_reminders(self) -> int:
        import os
        pending = self.get_pending_reminders()
        reminders_sent = 0
        delivery_mode = os.environ.get("DUE_REMINDER_DELIVERY", "dm").lower()

        for guild_id, channel_id, assignee, cache_key, msg_content in pending:
            dm_delivered = False
            try:
                # 1. Attempt personal DM if assignee is assigned
                if delivery_mode in ("dm", "direct", "personal", "both") and assignee and assignee != "unassigned":
                    if hasattr(self.comm, "send_dm_to_username"):
                        dm_delivered = await self.comm.send_dm_to_username(assignee, msg_content, guild_id=guild_id)

                # 2. If delivery mode is channel, or both, or DM delivery failed/unassigned:
                if delivery_mode in ("channel", "both") or not dm_delivered:
                    res = self.comm.send_message(OutgoingMessage(
                        channel_id=channel_id,
                        content=msg_content,
                    ))
                    if asyncio.iscoroutine(res) or hasattr(res, "__await__"):
                        await res
                    if not dm_delivered and assignee and assignee != "unassigned":
                        logger.info("Sent reminder for %s to channel %s (fallback from DM)", cache_key, channel_id)
                    else:
                        logger.info("Sent reminder for %s to channel %s", cache_key, channel_id)

                self._mark_reminded(cache_key, ttl_seconds=86400)
                reminders_sent += 1
            except Exception as e:
                logger.error("Error sending reminder for %s: %s", cache_key, e)

        return reminders_sent

    async def run(self) -> None:
        self._running = True
        logger.info(
            "DueDateReminderService started (interval=%ds, days_ahead=%d)",
            self.interval_seconds,
            self.days_ahead,
        )
        # Give bot connection a few seconds to stabilize before first run
        await asyncio.sleep(5)
        while self._running:
            try:
                sent = await self.check_and_send_reminders()
                if sent > 0:
                    logger.info("DueDateReminderService dispatched %d reminder(s)", sent)
            except Exception as e:
                logger.exception("Unexpected error in DueDateReminderService: %s", e)
            await asyncio.sleep(self.interval_seconds)

    def stop(self) -> None:
        self._running = False
