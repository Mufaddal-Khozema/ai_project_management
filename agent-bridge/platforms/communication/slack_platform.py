"""
platforms/communication/slack_platform.py — Full Slack Communication Platform adapter.
Supports Slack Web API (chat.postMessage, users.info, auth.test) and Event API handling
with multi-tenant channel mapping, mention stripping, and RBAC permission tiers.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import os
import time
from collections import deque
from typing import Any

import requests

from core.base import CommunicationPlatform, IncomingMessage, OutgoingMessage, extract_text_content
from core.registry import comm_platform

logger = logging.getLogger("agent_bridge.slack")

_DEFAULT_SLACK_ROLES = {
    "admin": "admin",
    "owner": "admin",
    "primary_owner": "admin",
    "Project Manager": "admin",
    "Developer": "write",
    "member": "write",
    "Viewer": "read",
    "guest": "read",
}


@comm_platform
class SlackPlatform(CommunicationPlatform):
    platform_id = "slack"
    display_name = "Slack"
    required_config_keys = ["bot_token"]

    def __init__(self):
        self._config: dict[str, Any] = {}
        self._bot_token: str | None = None
        self._signing_secret: str | None = None
        self._app_token: str | None = None
        self._bot_user_id: str | None = None
        self._org_id: str = "default"
        self._message_callback = None
        self._processed_msg_ids: deque[str] = deque(maxlen=300)
        self._user_cache: dict[str, dict[str, Any]] = {}
        self._running: bool = False

    def configure(self, config: dict[str, Any]) -> None:
        self._config = dict(config)
        self._org_id = config.get("org_id", "default")
        self._bot_token = (
            config.get("bot_token")
            or config.get("token")
            or os.environ.get("SLACK_BOT_TOKEN")
        )
        self._signing_secret = (
            config.get("signing_secret")
            or os.environ.get("SLACK_SIGNING_SECRET")
        )
        self._app_token = (
            config.get("app_token")
            or os.environ.get("SLACK_APP_TOKEN")
        )

        if self._bot_token:
            self._verify_auth()

        logger.info(
            "Slack platform configured (org=%s, bot_user_id=%s)",
            self._org_id,
            self._bot_user_id or "unverified",
        )

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._bot_token}",
            "Content-Type": "application/json; charset=utf-8",
        }

    def _verify_auth(self) -> None:
        """Call auth.test to verify bot token and cache bot's own user_id."""
        try:
            r = requests.post(
                "https://slack.com/api/auth.test",
                headers=self._headers(),
                timeout=10,
            )
            data = r.json()
            if data.get("ok"):
                self._bot_user_id = data.get("user_id")
                logger.info("Slack auth verified: bot_user_id=%s, team=%s", self._bot_user_id, data.get("team"))
            else:
                logger.warning("Slack auth.test rejected token: %s", data.get("error"))
        except Exception as e:
            logger.warning("Failed to connect to Slack auth.test: %s", e)

    def verify_signature(self, timestamp: str, signature: str, body: bytes) -> bool:
        """Verify request signature from Slack Events API."""
        if not self._signing_secret:
            return True
        try:
            # Prevent replay attacks
            if abs(time.time() - float(timestamp)) > 60 * 5:
                return False
            sig_basestring = f"v0:{timestamp}:".encode("utf-8") + body
            computed_hash = "v0=" + hmac.new(
                self._signing_secret.encode("utf-8"),
                sig_basestring,
                hashlib.sha256,
            ).hexdigest()
            return hmac.compare_digest(computed_hash, signature)
        except Exception as e:
            logger.warning("Slack signature verification error: %s", e)
            return False

    async def start(self) -> None:
        self._running = True
        logger.info("Slack platform started (listening for events)")

    async def stop(self) -> None:
        self._running = False
        logger.info("Slack platform stopped")

    def set_message_callback(self, callback) -> None:
        self._message_callback = callback

    def resolve_project_key(self, server_id: str, channel_id: str) -> str | None:
        channel_map: dict = self._config.get("channel_map", {})
        # Map could be {team_id: {channel_id: slug}} or {channel_id: slug}
        team_map = channel_map.get(str(server_id))
        if isinstance(team_map, dict):
            hit = team_map.get(str(channel_id))
            if hit:
                return hit

        hit = channel_map.get(str(channel_id))
        if hit and isinstance(hit, str):
            return hit

        # Fallback to first configured slug if direct message
        if not server_id or server_id == "dm":
            for val in channel_map.values():
                if isinstance(val, str) and val:
                    return val
                if isinstance(val, dict):
                    for slug in val.values():
                        if slug:
                            return slug
        return None

    def get_permission_tier(self, author_roles: list[str]) -> str:
        role_perms = {
            **_DEFAULT_SLACK_ROLES,
            **self._config.get("role_permissions", {}),
        }
        for role in author_roles:
            if role in role_perms:
                return role_perms[role]
            if role.lower() in role_perms:
                return role_perms[role.lower()]
        return "none"

    def get_user_info(self, user_id: str) -> dict[str, Any]:
        """Fetch and cache Slack user info."""
        if user_id in self._user_cache:
            return self._user_cache[user_id]
        try:
            r = requests.get(
                "https://slack.com/api/users.info",
                headers=self._headers(),
                params={"user": user_id},
                timeout=10,
            )
            data = r.json()
            if data.get("ok"):
                user = data.get("user", {})
                self._user_cache[user_id] = user
                return user
        except Exception as e:
            logger.warning("Could not fetch user info for %s: %s", user_id, e)
        return {"id": user_id, "name": user_id}

    async def send_message(self, msg: OutgoingMessage) -> None:
        if not self._bot_token:
            logger.error("Slack cannot send message: bot_token is missing")
            return

        content = extract_text_content(msg.content)
        channel = msg.channel_id
        thread_ts = msg.metadata.get("thread_ts") or msg.reply_to_message_id

        # Chunk messages exceeding Slack's recommended 3500-char block limit
        chunks = [content[i : i + 3500] for i in range(0, len(content), 3500)] or [""]

        for chunk in chunks:
            payload: dict[str, Any] = {
                "channel": channel,
                "text": chunk,
            }
            if thread_ts:
                payload["thread_ts"] = thread_ts

            try:
                r = requests.post(
                    "https://slack.com/api/chat.postMessage",
                    headers=self._headers(),
                    json=payload,
                    timeout=15,
                )
                data = r.json()
                if not data.get("ok"):
                    logger.error("Slack chat.postMessage failed: %s", data.get("error"))
            except Exception as e:
                logger.error("Failed to deliver Slack message to %s: %s", channel, e)

    async def handle_event(self, event_payload: dict[str, Any]) -> dict[str, Any] | None:
        """
        Processes an incoming Slack Events API webhook payload.
        Handles url_verification, app_mention, and message events.
        """
        # 1. URL Verification Challenge
        if event_payload.get("type") == "url_verification":
            return {"challenge": event_payload.get("challenge")}

        if event_payload.get("type") != "event_callback":
            return None

        event = event_payload.get("event", {})
        event_type = event.get("type")

        # Ignore messages from other bots or bot's own messages
        if event.get("bot_id") or (self._bot_user_id and event.get("user") == self._bot_user_id):
            return None
        if event.get("subtype") in ("bot_message", "message_changed", "message_deleted"):
            return None

        # Deduplication
        event_id = event_payload.get("event_id") or f"{event.get('channel')}:{event.get('ts')}"
        if event_id in self._processed_msg_ids:
            return None
        self._processed_msg_ids.append(event_id)

        # We respond to app_mention or direct messages
        is_dm = event.get("channel_type") == "im" or event.get("channel", "").startswith("D")
        is_mention = event_type == "app_mention"

        trigger_role = self._config.get("trigger_role", "CoordinaAI")
        text = event.get("text", "")
        role_triggered = trigger_role.lower() in text.lower()

        if not (is_dm or is_mention or role_triggered):
            return None

        # Clean mentions from text
        clean_text = text
        if self._bot_user_id:
            clean_text = clean_text.replace(f"<@{self._bot_user_id}>", "")
        # Remove any other mention markers
        import re
        clean_text = re.sub(r"<@[A-Z0-9]+>", "", clean_text).strip()

        if not clean_text:
            clean_text = "help"

        user_id = event.get("user", "unknown")
        user_info = self.get_user_info(user_id)
        user_name = (
            user_info.get("profile", {}).get("display_name")
            or user_info.get("real_name")
            or user_info.get("name")
            or user_id
        )

        # Build roles list for RBAC
        roles = []
        if user_info.get("is_primary_owner"):
            roles.append("primary_owner")
            roles.append("admin")
        elif user_info.get("is_owner"):
            roles.append("owner")
            roles.append("admin")
        elif user_info.get("is_admin"):
            roles.append("admin")
        else:
            roles.append("Developer")

        channel_id = event.get("channel", "")
        team_id = event_payload.get("team_id", "")

        incoming = IncomingMessage(
            platform=self.platform_id,
            platform_message_id=str(event.get("ts", "")),
            channel_id=str(channel_id),
            channel_name=str(channel_id),
            server_id=str(team_id),
            author_id=str(user_id),
            author_name=str(user_name),
            author_roles=roles,
            content=clean_text,
            raw_content=text,
            metadata={
                "org_id": self._org_id,
                "thread_ts": event.get("thread_ts") or event.get("ts"),
            },
        )

        if self._message_callback:
            try:
                reply = await self._message_callback(incoming)
                if reply:
                    await self.send_message(reply)
            except Exception as e:
                logger.exception("Error processing Slack message callback")
                err_reply = OutgoingMessage(
                    channel_id=channel_id,
                    content=f"⚠️ An error occurred: {e}",
                    metadata={"thread_ts": event.get("ts")},
                )
                await self.send_message(err_reply)

        return {"ok": True}
