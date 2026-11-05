"""
agent/mcp_client.py — Client integration connecting LangChain agents to mcp-gateway.
Exposes dynamic search_tools and execute_tool to Gemini with transparent identity passing.
"""
from __future__ import annotations
import json
import logging
import os
from typing import Any, Optional
import httpx
from langchain_core.tools import tool

logger = logging.getLogger("agent_bridge.mcp_client")

MCP_GATEWAY_URL = os.environ.get("MCP_GATEWAY_URL", "http://localhost:8005")

class McpGatewayClient:
    def __init__(self, base_url: str = MCP_GATEWAY_URL):
        self.base_url = base_url.rstrip("/")

    def search(self, query: str = "", category: Optional[str] = None) -> dict[str, Any]:
        url = f"{self.base_url}/tools/search"
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(url, json={"query": query, "category": category})
            resp.raise_for_status()
            return resp.json()

    async def asearch(self, query: str = "", category: Optional[str] = None) -> dict[str, Any]:
        url = f"{self.base_url}/tools/search"
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json={"query": query, "category": category})
            resp.raise_for_status()
            return resp.json()

    def execute(
        self,
        tool_type: str,
        tool_name: str,
        parameters: dict[str, Any],
        auth_context: dict[str, Any],
    ) -> dict[str, Any]:
        url = f"{self.base_url}/tools/execute"
        payload = {
            "tool_type": tool_type,
            "tool_name": tool_name,
            "parameters": parameters,
            "auth_context": auth_context,
        }
        with httpx.Client(timeout=25.0) as client:
            resp = client.post(url, json=payload)
            return resp.json()

    async def aexecute(
        self,
        tool_type: str,
        tool_name: str,
        parameters: dict[str, Any],
        auth_context: dict[str, Any],
    ) -> dict[str, Any]:
        url = f"{self.base_url}/tools/execute"
        payload = {
            "tool_type": tool_type,
            "tool_name": tool_name,
            "parameters": parameters,
            "auth_context": auth_context,
        }
        async with httpx.AsyncClient(timeout=25.0) as client:
            resp = await client.post(url, json=payload)
            return resp.json()

def build_mcp_tools(auth_context: dict[str, Any], base_url: str = MCP_GATEWAY_URL) -> list:
    """
    Builds the 2 meta-tools (search_tools and execute_tool) bound with the
    current user's verified identity context.
    """
    client = McpGatewayClient(base_url)

    @tool
    def search_tools(query: str = "", category: str = None) -> str:
        """
        Discovers available tools by keyword or category ('pm', 'meetings', 'discord').
        Use this when unsure which specific tool to invoke for a user request.
        """
        try:
            res = client.search(query=query, category=category)
            return json.dumps(res, indent=2)
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})

    @tool
    def execute_tool(tool_type: str, tool_name: str, parameters: dict = None) -> str:
        """
        Executes an operation through the secure MCP Gateway.
        Common tools & categories:
          - tool_type='meetings':
              - 'meeting_start_standup': Start real-time AI Voice Standup in Discord.
                parameters: {'voice_channel_id': '1489127884319625280', 'topic': 'Daily Standup'}
              - 'meeting_stop_standup': Stop active standup session. parameters: {}
              - 'meeting_check_voice_health': Check voice daemon health. parameters: {}
          - tool_type='pm':
              - 'taiga_list_tasks', 'taiga_create_task', 'taiga_update_task', 'taiga_list_user_stories'
          - tool_type='discord':
              - 'discord_post_summary', 'discord_verify_channel_mapping'
        """
        try:
            res = client.execute(
                tool_type=tool_type,
                tool_name=tool_name,
                parameters=parameters or {},
                auth_context=auth_context,
            )
            return json.dumps(res, indent=2)
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})

    return [search_tools, execute_tool]
