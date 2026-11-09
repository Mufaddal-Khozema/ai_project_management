"""
tests/test_slack_platform.py — Unit tests for SlackPlatform adapter.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import time
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from core.base import IncomingMessage, OutgoingMessage
from core.registry import PlatformRegistry
import platforms.communication.slack_platform  # noqa: triggers registration
from platforms.communication.slack_platform import SlackPlatform


def _run(coro):
    try:
        coro.send(None)
    except StopIteration as e:
        return e.value
    raise RuntimeError("Coroutine did not complete synchronously")


class TestSlackPlatformRegistration:
    def test_registered_in_registry(self):
        assert "slack" in PlatformRegistry.list_comm()
        cls = PlatformRegistry.get_comm("slack")
        assert cls is SlackPlatform


class TestSlackPlatformCore:
    @pytest.fixture
    def slack(self):
        p = SlackPlatform()
        with patch("platforms.communication.slack_platform.requests.post") as mock_post:
            mock_post.return_value.json.return_value = {
                "ok": True,
                "user_id": "U_BOT_123",
                "team": "Engineering Team",
            }
            p.configure({
                "bot_token": "xoxb-mock-token-12345",
                "signing_secret": "my_test_secret_xyz",
                "channel_map": {
                    "T100": {"C_PROJ": "alpha-project"},
                    "C_DIRECT": "beta-project",
                },
                "role_permissions": {
                    "Tech Lead": "admin",
                },
            })
        return p

    def test_auth_verified(self, slack):
        assert slack._bot_user_id == "U_BOT_123"

    def test_permission_tiers(self, slack):
        assert slack.get_permission_tier(["admin"]) == "admin"
        assert slack.get_permission_tier(["primary_owner"]) == "admin"
        assert slack.get_permission_tier(["Tech Lead"]) == "admin"
        assert slack.get_permission_tier(["Developer"]) == "write"
        assert slack.get_permission_tier(["Viewer"]) == "read"
        assert slack.get_permission_tier(["UnknownRole"]) == "none"

    def test_resolve_project_key(self, slack):
        assert slack.resolve_project_key("T100", "C_PROJ") == "alpha-project"
        assert slack.resolve_project_key("", "C_DIRECT") == "beta-project"
        assert slack.resolve_project_key("T999", "C_UNKNOWN") is None

    def test_verify_signature(self, slack):
        body = b'{"type": "event_callback"}'
        timestamp = str(int(time.time()))
        sig_basestring = f"v0:{timestamp}:".encode("utf-8") + body
        computed_hash = "v0=" + hmac.new(
            b"my_test_secret_xyz",
            sig_basestring,
            hashlib.sha256,
        ).hexdigest()

        assert slack.verify_signature(timestamp, computed_hash, body) is True
        assert slack.verify_signature(timestamp, "v0=invalid_sig", body) is False

    def test_send_message(self, slack):
        msg = OutgoingMessage(
            channel_id="C_PROJ",
            content="Task created successfully ✅",
            metadata={"thread_ts": "1234567890.123"},
        )
        with patch("platforms.communication.slack_platform.requests.post") as mock_post:
            mock_post.return_value.json.return_value = {"ok": True}
            _run(slack.send_message(msg))

            assert mock_post.called
            called_args, called_kwargs = mock_post.call_args
            payload = called_kwargs.get("json", {})
            assert payload["channel"] == "C_PROJ"
            assert payload["text"] == "Task created successfully ✅"
            assert payload["thread_ts"] == "1234567890.123"

    def test_handle_event_app_mention(self, slack):
        callback_called = []

        async def mock_callback(incoming):
            callback_called.append(incoming)
            return OutgoingMessage(channel_id="C_PROJ", content="Reply from CoordinaAI")

        slack.set_message_callback(mock_callback)

        payload = {
            "type": "event_callback",
            "team_id": "T100",
            "event_id": "Ev_123",
            "event": {
                "type": "app_mention",
                "user": "U_USER_456",
                "channel": "C_PROJ",
                "text": "<@U_BOT_123> list open sprint tasks",
                "ts": "1670000000.0001",
            },
        }

        with patch("platforms.communication.slack_platform.requests.get") as mock_get, \
             patch("platforms.communication.slack_platform.requests.post") as mock_post:
            mock_get.return_value.json.return_value = {
                "ok": True,
                "user": {
                    "id": "U_USER_456",
                    "name": "johndoe",
                    "real_name": "John Doe",
                    "is_admin": True,
                },
            }
            mock_post.return_value.json.return_value = {"ok": True}

            res = _run(slack.handle_event(payload))
            assert res == {"ok": True}

            assert len(callback_called) == 1
            incoming: IncomingMessage = callback_called[0]
            assert incoming.platform == "slack"
            assert incoming.content == "list open sprint tasks"
            assert incoming.author_name == "John Doe"
            assert "admin" in incoming.author_roles

    def test_handle_event_url_verification(self, slack):
        payload = {
            "type": "url_verification",
            "challenge": "challenge_token_xyz_987",
        }
        res = _run(slack.handle_event(payload))
        assert res == {"challenge": "challenge_token_xyz_987"}
