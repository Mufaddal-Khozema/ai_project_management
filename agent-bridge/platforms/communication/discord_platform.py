"""
platforms/communication/discord_platform.py — Full Discord adapter.
"""
from __future__ import annotations
import logging
from collections import deque
from typing import Any
import discord
from core.base import CommunicationPlatform, IncomingMessage, OutgoingMessage
from core.registry import comm_platform

logger = logging.getLogger("agent_bridge.discord")

_DEFAULT_ROLE_TIERS = {
    "Project Manager": "admin",
    "Developer":       "write",
    "Viewer":          "read",
}

@comm_platform
class DiscordPlatform(CommunicationPlatform):
    platform_id    = "discord"
    display_name   = "Discord"
    required_config_keys = ["bot_token", "trigger_role", "channel_map", "role_permissions"]

    def __init__(self):
        self._config: dict[str, Any] = {}
        self._client: discord.Client | None = None
        self._message_callback = None
        self._ready_callback = None
        self._bot_token: str | None = None
        self._processed_msg_ids: deque = deque(maxlen=200)

    def set_ready_callback(self, callback) -> None:
        """Optional hook invoked once the Discord gateway connection is
        actually established (on_ready fires) — not when start() is called,
        since start() blocks for the connection's entire lifetime and only
        returns on disconnect. Used by DiscordPlatformManager to know when
        it's accurate to report an org's connection as 'connected' rather
        than inferring it from start() returning (which would mean the
        status only ever flips at the very end, on disconnect)."""
        self._ready_callback = callback

    def _create_client(self) -> None:
        intents = discord.Intents.default()
        intents.messages = True
        intents.message_content = True
        intents.members = True
        self._client = discord.Client(intents=intents)
        self._client.event(self.on_ready)
        self._client.event(self.on_message)

    def configure(self, config: dict[str, Any]) -> None:
        self._config = config
        self._org_id = config.get("org_id", "default")
        self._bot_token = config.get("bot_token")
        self._create_client()
        logger.info("Discord platform configured (org=%s)", self._org_id)

    async def start(self) -> None:
        if self._client is None or self._client.is_closed():
            self._create_client()
        await self._client.start(self._config["bot_token"])

    async def stop(self) -> None:
        if self._client:
            await self._client.close()

    async def send_message(self, msg: OutgoingMessage) -> None:
        if not self._client:
            return
        try:
            target = self._client.get_channel(int(msg.channel_id))
            if target is None:
                # Target may be a user snowflake (DM)
                try:
                    user = self._client.get_user(int(msg.channel_id)) or await self._client.fetch_user(int(msg.channel_id))
                    target = user.dm_channel or await user.create_dm()
                except Exception:
                    pass

            if target is None:
                logger.error("Channel or user %s not found", msg.channel_id)
                return
            from core.base import extract_text_content
            content = extract_text_content(msg.content)
            if len(content) <= 2000:
                await target.send(content)
            else:
                # Send in chunks
                for i in range(0, len(content), 1900):
                    await target.send(content[i:i+1900])
        except Exception as e:
            logger.error("send_message failed: %s", e)

    async def send_dm_to_username(self, username: str, content: str, guild_id: str | None = None) -> bool:
        """
        Attempt to find a guild member matching username or display name, and send them a DM.
        Returns True if DM was delivered successfully, False otherwise.
        """
        if not self._client or not username:
            return False
        clean_user = username.lower().strip().lstrip("@")
        target_member = None

        guilds = []
        if guild_id:
            try:
                g = self._client.get_guild(int(guild_id))
                if g:
                    guilds.append(g)
            except Exception:
                pass
        if not guilds:
            guilds = list(self._client.guilds)

        for g in guilds:
            # Check cached members first
            for m in getattr(g, "members", []):
                m_name = m.name.lower()
                m_disp = m.display_name.lower()
                m_glob = getattr(m, "global_name", "") or ""
                m_glob = m_glob.lower()

                # Exact match
                if clean_user in (m_name, m_disp, m_glob):
                    target_member = m
                    break
                # Normalized match (ignoring dashes and underscores)
                norm_clean = clean_user.replace("_", "").replace("-", "").replace(" ", "")
                norm_m_name = m_name.replace("_", "").replace("-", "").replace(" ", "")
                norm_m_disp = m_disp.replace("_", "").replace("-", "").replace(" ", "")
                if norm_clean and norm_clean in (norm_m_name, norm_m_disp):
                    target_member = m
                    break
            if target_member:
                break

            # If not in cache, try query_members
            if hasattr(g, "query_members"):
                try:
                    matches = await g.query_members(query=clean_user, limit=5)
                    if matches:
                        target_member = matches[0]
                        break
                except Exception:
                    pass

        if not target_member:
            logger.warning("Could not find Discord member matching Taiga username '%s'", username)
            return False

        try:
            from core.base import extract_text_content
            text = extract_text_content(content)
            dm_channel = target_member.dm_channel or await target_member.create_dm()
            if len(text) <= 2000:
                await dm_channel.send(text)
            else:
                for i in range(0, len(text), 1900):
                    await dm_channel.send(text[i:i+1900])
            logger.info("Successfully delivered personal DM to @%s (%s)", username, target_member.id)
            return True
        except Exception as e:
            logger.warning("Failed to send personal DM to @%s (%s): %s", username, target_member.id, e)
            return False

    def resolve_project_key(self, server_id: str, channel_id: str) -> str | None:
        channel_map: dict = self._config.get("channel_map", {})
        guild_map = channel_map.get(str(server_id), {})
        hit = guild_map.get(str(channel_id))
        if hit:
            return hit
        # In a DM or unmapped direct interaction, default to the active project if configured
        if not server_id or server_id == "dm":
            all_slugs = [slug for g in channel_map.values() if isinstance(g, dict) for slug in g.values() if slug]
            if all_slugs:
                return all_slugs[0]
        return None

    def get_permission_tier(self, author_roles: list[str]) -> str:
        role_perms: dict = {
            **_DEFAULT_ROLE_TIERS,
            **self._config.get("role_permissions", {}),
        }
        for role in author_roles:
            if role in role_perms:
                return role_perms[role]
        return "none"

    def set_message_callback(self, callback) -> None:
        self._message_callback = callback

    # ── Discord events ───────────────────────────────────────────────

    async def on_ready(self) -> None:
        logger.info("Discord bot online as %s (id=%s)", self._client.user, self._client.user.id)
        print(f"[Agent Bridge] Discord bot ready: {self._client.user} (id={self._client.user.id})")
        if self._ready_callback:
            self._ready_callback()

    async def on_message(self, message: discord.Message) -> None:
        logger.info(
            "Message received in %s/%s from %s: %s",
            getattr(message.guild, "id", "dm"),
            getattr(message.channel, "id", "unknown"),
            getattr(message.author, "display_name", getattr(message.author, "name", "unknown")),
            getattr(message, "content", "")[:120],
        )

        # Ignore bot's own messages and other bots
        if message.author == self._client.user or getattr(message.author, "bot", False):
            logger.info("Ignoring bot message")
            return

        msg_id_str = str(message.id)
        if hasattr(self, "_processed_msg_ids"):
            if msg_id_str in self._processed_msg_ids:
                logger.info("Message %s already processed by this platform, ignoring duplicate event", msg_id_str)
                return
            self._processed_msg_ids.append(msg_id_str)

        guild_id = str(message.guild.id) if message.guild else ""
        channel_id = str(message.channel.id)
        project_key = self.resolve_project_key(guild_id, channel_id)

        # Record all user chat messages in project-mapped channels to durable memory
        if project_key and getattr(self, "_chat_record_callback", None):
            try:
                chat_doc = {
                    "message_id": str(message.id),
                    "platform": self.platform_id,
                    "guild_id": guild_id,
                    "channel_id": channel_id,
                    "channel_name": getattr(message.channel, "name", "unknown"),
                    "project_key": project_key,
                    "org_id": getattr(self, "_org_id", "") or "default",
                    "author_id": str(message.author.id),
                    "author_name": str(getattr(message.author, "display_name", message.author.name)),
                    "author_roles": [r.name for r in getattr(message.author, "roles", [])],
                    "content": message.content,
                    "created_at": message.created_at.isoformat() if getattr(message, "created_at", None) else None,
                    "reply_to_id": str(message.reference.message_id) if getattr(message, "reference", None) and getattr(message.reference, "message_id", None) else None,
                    "attachments": [a.url for a in getattr(message, "attachments", [])],
                }
                self._chat_record_callback(chat_doc)
            except Exception as e:
                logger.warning("Failed to record channel chat message: %s", e)

        bot_mentioned = self._client.user.mentioned_in(message) if self._client.user else False

        # Check if any role assigned to the bot in this guild was mentioned
        guild = getattr(message, "guild", None)
        bot_member = (guild.me if guild else None) or (guild.get_member(self._client.user.id) if (guild and self._client.user) else None)
        bot_roles = getattr(bot_member, "roles", []) if bot_member else []
        bot_role_mentioned = any(r in bot_roles for r in getattr(message, "role_mentions", []))

        # Check configured trigger roles (can be comma-separated, e.g. "CoordinaAI, CoordinaAI")
        trigger_cfg = self._config.get("trigger_role", "CoordinaAI").strip()
        trigger_roles = {t.strip().lower() for t in trigger_cfg.split(",") if t.strip()}
        trigger_roles.add("coordinaai")
        trigger_roles.add("CoordinaAI")
        if self._client.user and self._client.user.name:
            trigger_roles.add(self._client.user.name.lower())
        if bot_member and bot_member.display_name:
            trigger_roles.add(bot_member.display_name.lower())

        author_roles = [r.name.lower() for r in getattr(message.author, "roles", [])]
        mentioned_roles = [r.name.lower() for r in getattr(message, "role_mentions", [])]

        role_triggered = any(r in trigger_roles for r in author_roles)
        role_mentioned = any(r in trigger_roles for r in mentioned_roles) or bot_role_mentioned

        is_dm = message.guild is None
        if not is_dm and not bot_mentioned and not role_triggered and not role_mentioned:
            logger.info(
                "Recorded message (no mention): bot_mentioned=%s role_triggered=%s role_mentioned=%s",
                bot_mentioned,
                role_triggered,
                role_mentioned,
            )
            return

        # Strip all bot/role mentions from the message text
        content = message.content
        for variant in (f"<@{self._client.user.id}>", f"<@!{self._client.user.id}>"):
            content = content.replace(variant, "")
        for role in getattr(message, "role_mentions", []):
            content = content.replace(f"<@&{role.id}>", "")
        content = content.strip()

        if not content:
            await message.channel.send("How can I help? Type a command like `create a task`, `list open tasks`, or `sprint status`.")
            return

        guild_id = str(message.guild.id) if message.guild else ""
        channel_id = str(message.channel.id)
        if message.guild:
            author_roles = [r.name for r in getattr(message.author, "roles", [])]
        else:
            author_roles = []
            for g in self._client.guilds:
                m = g.get_member(message.author.id)
                if m:
                    author_roles.extend([r.name for r in getattr(m, "roles", [])])
            if not author_roles:
                author_roles = ["Developer"]

        incoming = IncomingMessage(
            platform            = self.platform_id,
            platform_message_id = str(message.id),
            channel_id          = channel_id,
            channel_name        = getattr(message.channel, "name", "unknown"),
            server_id           = guild_id,
            author_id           = str(message.author.id),
            author_name         = str(message.author.display_name),
            author_roles        = author_roles,
            content             = content,
            raw_content         = message.content,
            metadata            = {"org_id": getattr(self, "_org_id", "default")},
        )

        if self._message_callback:
            async with message.channel.typing():
                try:
                    reply = await self._message_callback(incoming)
                    await self.send_message(reply)
                except Exception as e:
                    logger.exception("Error handling message")
                    await message.channel.send(f"⚠️ An error occurred: {e}")
