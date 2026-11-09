"""
tests/test_multi_platform.py — Tests for MultiCommPlatform composite adapter.
"""
from __future__ import annotations

from typing import Any
from unittest.mock import patch

from core.base import CommunicationPlatform, OutgoingMessage
from core.registry import PlatformRegistry
import platforms.communication.multi_platform
from platforms.communication.multi_platform import MultiCommPlatform


class DummyPlatform(CommunicationPlatform):
    def __init__(self, pid: str, name: str, slug: str | None = None, tier: str = "none"):
        self.platform_id = pid
        self.display_name = name
        self._slug = slug
        self._tier = tier
        self.sent_messages: list[OutgoingMessage] = []
        self.started = False
        self.stopped = False
        self.callback = None

    def configure(self, config: dict[str, Any]) -> None:
        pass

    def set_message_callback(self, callback) -> None:
        self.callback = callback

    def resolve_project_key(self, server_id: str, channel_id: str) -> str | None:
        return self._slug

    def get_permission_tier(self, author_roles: list[str]) -> str:
        return self._tier

    async def send_message(self, msg: OutgoingMessage) -> None:
        self.sent_messages.append(msg)

    async def start(self) -> None:
        self.started = True

    async def stop(self) -> None:
        self.stopped = True


def _run(coro):
    """Step a synchronous coroutine to completion without an OS event loop."""
    for _ in range(100):
        try:
            coro.send(None)
        except StopIteration as e:
            return e.value
    raise RuntimeError("Coroutine did not complete synchronously within 100 steps")


class TestMultiCommPlatform:
    def test_registered_in_registry(self):
        assert "multi" in PlatformRegistry.list_comm()
        assert PlatformRegistry.get_comm("multi") is MultiCommPlatform

    def test_delegates_to_subplatforms(self):
        p1 = DummyPlatform("discord", "Discord", slug=None, tier="none")
        p2 = DummyPlatform("slack", "Slack", slug="slack-proj", tier="admin")

        multi = MultiCommPlatform([p1, p2])

        assert multi.resolve_project_key("T100", "C100") == "slack-proj"
        assert multi.get_permission_tier(["admin"]) == "admin"

        cb = lambda x: x  # noqa: E731
        multi.set_message_callback(cb)
        assert p1.callback is cb
        assert p2.callback is cb

    def test_send_message_routes_by_platform(self):
        p1 = DummyPlatform("discord", "Discord")
        p2 = DummyPlatform("slack", "Slack")
        multi = MultiCommPlatform([p1, p2])

        slack_msg = OutgoingMessage(
            channel_id="C_SLACK",
            content="Hello Slack",
            metadata={"platform": "slack"},
        )
        _run(multi.send_message(slack_msg))
        assert len(p2.sent_messages) == 1
        assert len(p1.sent_messages) == 0

        discord_msg = OutgoingMessage(
            channel_id="C_DISCORD",
            content="Hello Discord",
            metadata={"platform": "discord"},
        )
        _run(multi.send_message(discord_msg))
        assert len(p1.sent_messages) == 1

    def test_start_and_stop_gathers_all(self):
        p1 = DummyPlatform("discord", "Discord")
        p2 = DummyPlatform("slack", "Slack")
        multi = MultiCommPlatform([p1, p2])

        async def fake_gather(*args, **kwargs):
            return []

        with patch("asyncio.gather", side_effect=fake_gather) as mock_gather:
            _run(multi.start())
            assert mock_gather.called

        with patch("asyncio.gather", side_effect=fake_gather) as mock_gather:
            _run(multi.stop())
            assert mock_gather.called
