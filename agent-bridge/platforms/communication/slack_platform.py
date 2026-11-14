"""
platforms/communication/slack_platform.py — Full Slack Communication Platform adapter.
Supports Slack Web API (chat.postMessage, users.info, auth.test), real-time Slack Socket Mode
(via outbound WebSocket connection using SLACK_APP_TOKEN), and Event API handling
with multi-tenant channel mapping, mention stripping, and RBAC permission tiers.
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import os
import re
import time
from collections import deque
from typing import Any

import aiohttp
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
    required_config_keys = []

    def __init__(self):
        self._config: dict[str, Any] = {}
        self._bot_token: str | None = None
        self._signing_secret: str | None = None
        self._app_token: str | None = None
        self._bot_user_id: str | None = None
        self._org_id: str = "default"
        self._message_callback = None
        self._chat_record_callback = None
        self._processed_msg_ids: deque[str] = deque(maxlen=300)
        self._user_cache: dict[str, dict[str, Any]] = {}
        self._running: bool = False
        self._stop_event: asyncio.Event | None = None
        self._ws_session: aiohttp.ClientSession | None = None

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
            "Slack platform configured (org=%s, bot_user_id=%s, socket_mode=%s)",
            self._org_id,
            self._bot_user_id or "unverified",
            bool(self._app_token),
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

    async def _fetch_wss_url(self, session: aiohttp.ClientSession) -> str | None:
        """Call apps.connections.open using app token to get WebSocket endpoint."""
        if not self._app_token:
            return None
        headers = {
            "Authorization": f"Bearer {self._app_token}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        try:
            async with session.post(
                "https://slack.com/api/apps.connections.open",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                data = await resp.json()
                if data.get("ok"):
                    return data.get("url")
                logger.error("Slack apps.connections.open failed: %s", data.get("error"))
        except Exception as e:
            logger.error("Failed to fetch Slack Socket Mode URL: %s", e)
        return None

    async def _run_socket_mode(self) -> None:
        """Main Socket Mode event loop connecting to Slack gateway."""
        retry_delay = 1
        max_retry_delay = 30

        async with aiohttp.ClientSession() as session:
            self._ws_session = session
            while self._running:
                wss_url = await self._fetch_wss_url(session)
                if not wss_url:
                    logger.warning("Could not obtain Slack WebSocket URL. Retrying in %ds...", retry_delay)
                    await asyncio.sleep(retry_delay)
                    retry_delay = min(retry_delay * 2, max_retry_delay)
                    continue

                retry_delay = 1
                try:
                    logger.info("Connecting to Slack Socket Mode gateway...")
                    async with session.ws_connect(wss_url, heartbeat=20.0) as ws:
                        logger.info("⚡ Slack Socket Mode connected! Listening for mentions & events...")
                        async for msg in ws:
                            if not self._running:
                                break
                            if msg.type == aiohttp.WSMsgType.TEXT:
                                try:
                                    payload = json.loads(msg.data)
                                    envelope_id = payload.get("envelope_id")
                                    # Fast ACK required by Slack Socket Mode protocol (< 3 seconds)
                                    if envelope_id:
                                        await ws.send_str(json.dumps({"envelope_id": envelope_id}))

                                    msg_type = payload.get("type")
                                    if msg_type == "events_api":
                                        event_payload = payload.get("payload", {})
                                        asyncio.create_task(self.handle_event(event_payload))
                                    elif msg_type == "disconnect":
                                        logger.info("Slack sent disconnect frame (server maintenance), reconnecting...")
                                        break
                                except Exception as exc:
                                    logger.error("Error processing Slack Socket Mode message: %s", exc)
                            elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                                logger.warning("Slack Socket Mode connection closed: %s", msg)
                                break
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.warning("Slack Socket Mode error: %s. Reconnecting in %ds...", e, retry_delay)
                    await asyncio.sleep(retry_delay)
                    retry_delay = min(retry_delay * 2, max_retry_delay)

    async def start(self) -> None:
        self._running = True
        self._stop_event = asyncio.Event()

        if self._app_token:
            logger.info("Slack platform starting in Socket Mode (app_token provided)")
            await self._run_socket_mode()
        else:
            logger.warning(
                "Slack app_token (xapp-...) not configured — Socket Mode is disabled. "
                "Running in Webhook listener mode. Set SLACK_APP_TOKEN in .env to enable real-time Socket Mode without webhooks."
            )
            await self._stop_event.wait()

    async def stop(self) -> None:
        self._running = False
        if self._stop_event:
            self._stop_event.set()
        logger.info("Slack platform stopped")

    def set_message_callback(self, callback) -> None:
        self._message_callback = callback

    def set_chat_record_callback(self, callback) -> None:
        self._chat_record_callback = callback

    def resolve_project_key(self, server_id: str, channel_id: str) -> str | None:
        channel_map: dict = self._config.get("channel_map", {})
        # 1. Map could be {team_id: {channel_id: slug}} or {channel_id: slug}
        team_map = channel_map.get(str(server_id))
        if isinstance(team_map, dict):
            hit = team_map.get(str(channel_id))
            if hit:
                return hit

        # 2. Channel match directly
        hit = channel_map.get(str(channel_id))
        if hit and isinstance(hit, str):
            return hit

        # 3. Check inside nested maps for channel_id
        for val in channel_map.values():
            if isinstance(val, dict):
                hit = val.get(str(channel_id))
                if hit:
                    return hit

        # 4. Fallback to first configured slug only if direct message or server not provided
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
        if not self._bot_token:
            return {"id": user_id, "name": user_id}
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
        bot_tok = (
            (msg.metadata or {}).get("bot_token")
            or self._bot_token
            or os.environ.get("SLACK_BOT_TOKEN")
        )
        if not bot_tok:
            logger.error("Slack cannot send message: bot_token is missing")
            return

        content = extract_text_content(msg.content)
        channel = msg.channel_id
        thread_ts = msg.metadata.get("thread_ts") or msg.reply_to_message_id

        # Chunk messages exceeding Slack's recommended 3500-char block limit
        chunks = [content[i : i + 3500] for i in range(0, len(content), 3500)] or [""]

        headers = {
            "Authorization": f"Bearer {bot_tok}",
            "Content-Type": "application/json; charset=utf-8",
        }

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
                    headers=headers,
                    json=payload,
                    timeout=15,
                )
                data = r.json()
                if data.get("ok"):
                    logger.info("Slack message delivered to %s", channel)
                else:
                    logger.error("Slack chat.postMessage failed: %s (channel: %s)", data.get("error"), channel)
            except Exception as e:
                logger.error("Failed to deliver Slack message to %s: %s", channel, e)

    async def handle_event(self, event_payload: dict[str, Any]) -> dict[str, Any] | None:
        """
        Processes an incoming Slack Events API payload (from Socket Mode or Webhook).
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
                "platform": self.platform_id,
                "thread_ts": event.get("thread_ts") or event.get("ts"),
            },
        )

        # Optional raw chat recording for meeting / context stores
        if self._chat_record_callback:
            try:
                self._chat_record_callback({
                    "platform": self.platform_id,
                    "channel_id": str(channel_id),
                    "guild_id": str(team_id),
                    "author_id": str(user_id),
                    "author_name": str(user_name),
                    "content": clean_text,
                    "created_at": time.time(),
                })
            except Exception as e:
                logger.debug("Slack chat recording failed: %s", e)

        if self._message_callback:
            try:
                reply = await self._message_callback(incoming)
                if reply:
                    if not reply.metadata:
                        reply.metadata = {}
                    reply.metadata.setdefault("platform", self.platform_id)
                    reply.metadata.setdefault("thread_ts", event.get("thread_ts") or event.get("ts"))
                    await self.send_message(reply)
            except Exception as e:
                logger.exception("Error processing Slack message callback")
                err_reply = OutgoingMessage(
                    channel_id=channel_id,
                    content=f"⚠️ An error occurred: {e}",
                    metadata={"thread_ts": event.get("ts"), "platform": self.platform_id},
                )
                await self.send_message(err_reply)

        return {"ok": True}
