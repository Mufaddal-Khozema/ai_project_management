from __future__ import annotations
import logging
from typing import Any
import httpx
from plugins.base import BasePlugin
from core.config import settings

logger = logging.getLogger("mcp_gateway.plugins.meetings")

class MeetingOpsPlugin(BasePlugin):
    @property
    def category(self) -> str:
        return "meetings"

    def get_supported_tools(self) -> dict[str, dict[str, Any]]:
        return {
            "meeting_start_standup": {
                "description": "Start an on-demand real-time AI Voice Standup in a Discord voice channel.",
                "parameters": {
                    "guild_id": "str (Discord Guild/Server Snowflake)",
                    "voice_channel_id": "str (Target Discord Voice Channel ID)",
                    "topic": "str (Optional meeting topic or sprint name)"
                }
            },
            "meeting_stop_standup": {
                "description": "End an ongoing Voice Standup session and trigger summary compilation.",
                "parameters": {
                    "guild_id": "str (Discord Guild/Server Snowflake)"
                }
            },
            "meeting_check_voice_health": {
                "description": "Check the health and active status of the Voice Scrum Master daemon.",
                "parameters": {}
            }
        }

    async def execute(
        self,
        tool_name: str,
        params: dict[str, Any],
        auth: dict[str, Any],
    ) -> dict[str, Any]:
        voice_url = settings.VOICE_SERVICE_URL.rstrip("/")

        async with httpx.AsyncClient(timeout=15.0) as client:
            if tool_name == "meeting_start_standup":
                url = f"{voice_url}/integrations/discord/meetings/start"
                payload = {
                    "guild_id": params.get("guild_id") or auth.get("guild_id"),
                    "voice_channel_id": params.get("voice_channel_id"),
                    "topic": params.get("topic", "Daily Standup"),
                    "initiated_by": auth.get("external_id", "unknown"),
                }
                resp = await client.post(url, json=payload)
                if resp.status_code in (200, 201):
                    return {"success": True, "message": "Voice Scrum Master successfully joined voice channel."}
                else:
                    return {"success": False, "status_code": resp.status_code, "error": resp.text}

            elif tool_name == "meeting_stop_standup":
                url = f"{voice_url}/integrations/discord/meetings/stop"
                payload = {"guild_id": params.get("guild_id") or auth.get("guild_id")}
                resp = await client.post(url, json=payload)
                return {"success": resp.status_code == 200, "message": "Standup terminated."}

            elif tool_name == "meeting_check_voice_health":
                url = f"{voice_url}/health"
                resp = await client.get(url)
                return {"healthy": resp.status_code == 200, "data": resp.json() if resp.status_code == 200 else resp.text}

            else:
                raise NotImplementedError(f"Tool '{tool_name}' not implemented in MeetingOpsPlugin")
