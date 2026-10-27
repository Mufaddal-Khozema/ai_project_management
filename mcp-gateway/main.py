from __future__ import annotations
import logging
from typing import Any
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from core.config import settings
from core.registry import ToolRegistry
from core.guardrails import GuardrailEngine, GuardrailViolation
from core.fallback import FallbackEngine
from plugins.pm_taiga import TaigaPlugin
from plugins.meeting_ops import MeetingOpsPlugin
from plugins.discord_ops import DiscordOpsPlugin

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("mcp_gateway")

# 1. Initialize FastAPI Application
app = FastAPI(
    title="Universal Project MCP Gateway",
    version="1.0.0",
    description="Centralized MCP & Tool Orchestration Gateway with Multi-Tier Guardrails and Fuzzy Fallback",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Register Built-in Plugins
ToolRegistry.register_plugin("pm", TaigaPlugin())
ToolRegistry.register_plugin("meetings", MeetingOpsPlugin())
ToolRegistry.register_plugin("discord", DiscordOpsPlugin())

# 3. Request / Response Schemas
class SearchRequest(BaseModel):
    query: str = Field(default="", description="Search term for tool name or description")
    category: str | None = Field(default=None, description="Optional category filter (e.g. 'pm', 'meetings')")

class ExecutePayload(BaseModel):
    tool_type: str = Field(description="Category of tool: 'pm', 'meetings', 'discord'")
    tool_name: str = Field(description="Exact tool name, e.g. 'taiga_create_task'")
    parameters: dict[str, Any] = Field(default_factory=dict, description="Arguments for the tool")
    auth_context: dict[str, Any] = Field(
        default_factory=dict,
        description="Auth & identity context (user_role, org_id, external_id, etc.)"
    )

# 4. Core Endpoints
@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "mcp-gateway",
        "categories": ToolRegistry.get_categories(),
        "total_tools": ToolRegistry.count(),
    }

@app.post("/tools/search")
def search_tools_endpoint(req: SearchRequest):
    """Discovers available tools by keyword and category."""
    results = ToolRegistry.search(query=req.query, category=req.category)
    return {"status": "success", "results": results}


@app.post("/tools/execute")
async def execute_tool_endpoint(payload: ExecutePayload):
    category = payload.tool_type.lower().strip()
    tool_name = payload.tool_name.lower().strip()
    auth = payload.auth_context

    # Step 1: Category Check
    plugin = ToolRegistry.get_plugin(category)
    if not plugin:
        return FallbackEngine.handle_unsupported_tool(
            category=category,
            tool_name=tool_name,
            available_tools=[],
            auth=auth,
        )

    # Step 2: Tool Existence Check & Fallback
    supported_tools = ToolRegistry.get_tools_for_category(category)
    if tool_name not in supported_tools:
        return FallbackEngine.handle_unsupported_tool(
            category=category,
            tool_name=tool_name,
            available_tools=supported_tools,
            auth=auth,
        )

    # Step 3: Multi-Tier Guardrails
    try:
        GuardrailEngine.verify_request(tool_name, payload.parameters, auth)
    except GuardrailViolation as gv:
        logger.warning("Guardrail violation on '%s': %s", tool_name, gv.message)
        return {
            "status": "forbidden",
            "error_code": gv.code,
            "message": gv.message,
            "tool_name": tool_name,
        }



    # Step 4: Execute the Tool Action
    try:
        raw_result = await ToolRegistry.execute(
            category=category,
            tool_name=tool_name,
            params=payload.parameters,
            auth=auth,
        )
        # Step 5: Sanitize Output via DLP Guardrail
        clean_result = GuardrailEngine.sanitize_output(raw_result)
        return {
            "status": "success",
            "tool_name": tool_name,
            "category": category,
            "result": clean_result,
        }
    except Exception as e:
        logger.exception("Execution error in tool '%s': %s", tool_name, e)
        return {
            "status": "error",
            "error_code": "EXECUTION_FAILURE",
            "message": str(e),
            "tool_name": tool_name,
        }

# Optional FastMCP Mount for standard MCP SSE
try:
    try:
        from mcp.server.mcpserver import MCPServer as FastMCP
    except ImportError:
        from mcp.server.fastmcp import FastMCP

    mcp_server = FastMCP("Universal-Project-MCP")

    @mcp_server.tool()
    async def search_tools(query: str = "", category: str = None) -> dict:
        return ToolRegistry.search(query=query, category=category)

    @mcp_server.tool()
    async def execute_tool(tool_type: str, tool_name: str, parameters: dict = None, auth_context: dict = None) -> dict:
        req = ExecutePayload(
            tool_type=tool_type,
            tool_name=tool_name,
            parameters=parameters or {},
            auth_context=auth_context or {},
        )
        return await execute_tool_endpoint(req)

    if hasattr(mcp_server, "sse_app"):
        app.mount("/sse", mcp_server.sse_app())

    logger.info("FastMCP/MCPServer initialized and tools registered for SSE transport.")
except ImportError:
    logger.info("mcp package not installed in current environment; running in high-performance REST mode.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.HOST, port=settings.PORT, reload=True)
