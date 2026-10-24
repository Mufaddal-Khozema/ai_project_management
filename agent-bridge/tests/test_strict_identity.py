from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch
import pytest

def _ensure_mock_langchain():
    if "langchain_core" not in sys.modules:
        lc = MagicMock()
        lc_tools = MagicMock()

        def mock_tool_decorator(func=None, *args, **kwargs):
            if func is not None:
                func.invoke = lambda x: func(**x) if isinstance(x, dict) else func()
                func.name = func.__name__
                return func

            def wrapper(f):
                f.invoke = lambda x: f(**x) if isinstance(x, dict) else f()
                f.name = f.__name__
                return f
            return wrapper

        lc_tools.tool = mock_tool_decorator
        class BaseMessage:
            def __init__(self, content="", **kwargs):
                self.content = content
                for k, v in kwargs.items():
                    setattr(self, k, v)
        class HumanMessage(BaseMessage):
            type = "human"
        class AIMessage(BaseMessage):
            type = "ai"
        class SystemMessage(BaseMessage):
            type = "system"
        class ToolMessage(BaseMessage):
            type = "tool"

        lc_messages = MagicMock()
        lc_messages.BaseMessage = BaseMessage
        lc_messages.HumanMessage = HumanMessage
        lc_messages.AIMessage = AIMessage
        lc_messages.SystemMessage = SystemMessage
        lc_messages.ToolMessage = ToolMessage

        sys.modules["langchain_core"] = lc
        sys.modules["langchain_core.tools"] = lc_tools
        sys.modules["langchain_core.messages"] = lc_messages

    if "langchain_google_genai" not in sys.modules:
        lgg = MagicMock()
        sys.modules["langchain_google_genai"] = lgg


_ensure_mock_langchain()

from core.base import IncomingMessage, OutgoingMessage
from core.identity_client import IdentityClient, IdentityResult
from agent.agent import AgentBridge


@pytest.fixture
def mock_platforms():
    comm = MagicMock()
    comm.resolve_project_key.return_value = "test-project"
    comm.get_permission_tier.return_value = "admin"

    pm = MagicMock()
    pm.get_project_context.return_value = MagicMock(members=[])
    pm._config = {}

    return comm, pm


@pytest.fixture
def incoming_message():
    return IncomingMessage(
        platform="discord",
        platform_message_id="msg-101",
        channel_id="chan-202",
        channel_name="general",
        server_id="guild-303",
        author_id="user-404",
        author_name="Alice",
        author_roles=["Developer"],
        content="Create a task for database migration",
        raw_content="<@CoordinaAI> Create a task for database migration",
    )


@pytest.mark.asyncio
async def test_strict_identity_blocks_when_client_missing(mock_platforms, incoming_message):
    comm, pm = mock_platforms
    with patch("agent.agent.ChatGoogleGenerativeAI"), patch("agent.agent.IntentRouter") as mock_router:
        bridge = AgentBridge(
            comm_platform=comm,
            pm_platform=pm,
            gemini_api_key="mock_key",
            identity_client=None,
            strict_identity=True,
        )

        res = await bridge.handle(incoming_message)

        assert isinstance(res, OutgoingMessage)
        assert "🔒 **Workspace Identity Required**" in res.content
        # Confirm LLM classifier was NEVER called (0 tokens consumed)
        assert not mock_router.return_value.classify.called


@pytest.mark.asyncio
async def test_strict_identity_blocks_when_backend_service_fails(mock_platforms, incoming_message):
    comm, pm = mock_platforms
    mock_id_client = MagicMock(spec=IdentityClient)
    mock_id_client.is_configured.return_value = True
    mock_id_client.resolve_discord_identity.side_effect = RuntimeError("Backend Litestar service timed out")

    with patch("agent.agent.ChatGoogleGenerativeAI"), patch("agent.agent.IntentRouter") as mock_router:
        bridge = AgentBridge(
            comm_platform=comm,
            pm_platform=pm,
            gemini_api_key="mock_key",
            identity_client=mock_id_client,
            strict_identity=True,
        )

        res = await bridge.handle(incoming_message)

        assert isinstance(res, OutgoingMessage)
        assert "⚠️ **Identity Service Temporarily Unavailable**" in res.content
        assert not mock_router.return_value.classify.called


@pytest.mark.asyncio
async def test_strict_identity_blocks_when_unlinked(mock_platforms, incoming_message):
    comm, pm = mock_platforms
    mock_id_client = MagicMock(spec=IdentityClient)
    mock_id_client.is_configured.return_value = True
    mock_id_client.resolve_discord_identity.return_value = IdentityResult(linked=False)

    with patch("agent.agent.ChatGoogleGenerativeAI"), patch("agent.agent.IntentRouter") as mock_router:
        bridge = AgentBridge(
            comm_platform=comm,
            pm_platform=pm,
            gemini_api_key="mock_key",
            identity_client=mock_id_client,
            strict_identity=True,
        )

        res = await bridge.handle(incoming_message)

        assert isinstance(res, OutgoingMessage)
        assert "⚠️ **Identity Not Linked**" in res.content
        assert not mock_router.return_value.classify.called


@pytest.mark.asyncio
async def test_strict_identity_blocks_when_unsubscribed(mock_platforms, incoming_message):
    comm, pm = mock_platforms
    mock_id_client = MagicMock(spec=IdentityClient)
    mock_id_client.is_configured.return_value = True
    mock_id_client.resolve_discord_identity.return_value = IdentityResult(
        linked=True,
        entitlements={"has_subscription": False},
        workspace={"company_name": "ACME Corp"},
    )

    with patch("agent.agent.ChatGoogleGenerativeAI"), patch("agent.agent.IntentRouter") as mock_router:
        bridge = AgentBridge(
            comm_platform=comm,
            pm_platform=pm,
            gemini_api_key="mock_key",
            identity_client=mock_id_client,
            strict_identity=True,
        )

        res = await bridge.handle(incoming_message)

        assert isinstance(res, OutgoingMessage)
        assert "⚠️ **Active Subscription Required**" in res.content
        assert not mock_router.return_value.classify.called


@pytest.mark.asyncio
async def test_lenient_identity_falls_back_when_strict_disabled(mock_platforms, incoming_message):
    comm, pm = mock_platforms
    mock_id_client = MagicMock(spec=IdentityClient)
    mock_id_client.is_configured.return_value = True
    mock_id_client.resolve_discord_identity.side_effect = RuntimeError("Backend down")

    with patch("agent.agent.ChatGoogleGenerativeAI"), patch("agent.agent.IntentRouter") as mock_router, patch("agent.agent._run_agent_loop") as mock_agent_loop:
        mock_router.return_value.classify.return_value = {
            "intent": "create", "resource": "task", "needs_write": True, "confidence": 0.9,
        }
        mock_agent_loop.return_value = ("Task created successfully", [])

        bridge = AgentBridge(
            comm_platform=comm,
            pm_platform=pm,
            gemini_api_key="mock_key",
            identity_client=mock_id_client,
            strict_identity=False,  # Explicitly disabled
        )

        res = await bridge.handle(incoming_message)

        # In lenient mode, it fell back to local routing
        assert mock_router.return_value.classify.called
        assert res.content == "Task created successfully"


async def asyncio_mock_result(text):
    return text, []
