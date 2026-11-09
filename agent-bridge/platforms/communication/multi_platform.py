"""
platforms/communication/multi_platform.py — Composite Communication Platform adapter.
Enables Agent Bridge to listen and respond across multiple communication platforms
simultaneously (e.g. Discord and Slack running concurrently in the same process).
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from core.base import CommunicationPlatform, OutgoingMessage
from core.registry import comm_platform

logger = logging.getLogger("agent_bridge.multi_comm")


@comm_platform
class MultiCommPlatform(CommunicationPlatform):
    platform_id = "multi"
    display_name = "MultiPlatform (Discord & Slack)"
    required_config_keys = []

    def __init__(self, platforms: list[CommunicationPlatform] | None = None):
        self._platforms: list[CommunicationPlatform] = list(platforms or [])
        self._message_callback = None
        self._chat_record_callback = None

    @property
    def platforms(self) -> list[CommunicationPlatform]:
        return self._platforms

    def add_platform(self, platform: CommunicationPlatform) -> None:
        if platform not in self._platforms:
            self._platforms.append(platform)
            if self._message_callback:
                platform.set_message_callback(self._message_callback)
            if self._chat_record_callback and hasattr(platform, "set_chat_record_callback"):
                platform.set_chat_record_callback(self._chat_record_callback)

    def configure(self, config: dict[str, Any]) -> None:
        for p in self._platforms:
            p.configure(config)

    def set_message_callback(self, callback) -> None:
        self._message_callback = callback
        for p in self._platforms:
            p.set_message_callback(callback)

    def set_chat_record_callback(self, callback) -> None:
        self._chat_record_callback = callback
        for p in self._platforms:
            if hasattr(p, "set_chat_record_callback"):
                p.set_chat_record_callback(callback)

    def resolve_project_key(self, server_id: str, channel_id: str) -> str | None:
        for p in self._platforms:
            slug = p.resolve_project_key(server_id, channel_id)
            if slug:
                return slug
        return None

    def get_permission_tier(self, author_roles: list[str]) -> str:
        for p in self._platforms:
            tier = p.get_permission_tier(author_roles)
            if tier != "none":
                return tier
        return "none"

    async def send_message(self, msg: OutgoingMessage) -> None:
        target_platform = (msg.metadata or {}).get("platform")
        sent = False
        for p in self._platforms:
            if not target_platform or p.platform_id == target_platform:
                await p.send_message(msg)
                sent = True
        if not sent and self._platforms:
            await self._platforms[0].send_message(msg)

    async def start(self) -> None:
        if not self._platforms:
            logger.warning("MultiCommPlatform started with no active platforms")
            return
        names = [p.display_name for p in self._platforms]
        logger.info("Starting MultiCommPlatform with %d platform(s): %s", len(self._platforms), names)
        await asyncio.gather(*(p.start() for p in self._platforms))

    async def stop(self) -> None:
        logger.info("Stopping MultiCommPlatform...")
        await asyncio.gather(*(p.stop() for p in self._platforms), return_exceptions=True)
