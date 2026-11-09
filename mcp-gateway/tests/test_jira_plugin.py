"""
tests/test_jira_plugin.py — Unit tests for Jira MCP Plugin & Gateway routing.
"""
from __future__ import annotations

import os
os.environ["TESTING"] = "true"

from unittest.mock import AsyncMock, MagicMock, patch
import httpx
import pytest

import main  # noqa: registers all built-in plugins (jira, taiga, discord, meetings)
from core.guardrails import GuardrailEngine, GuardrailViolation
from core.registry import ToolRegistry
from plugins.pm_jira import JiraPlugin


def _run(coro):
    """Run a coroutine to completion when awaited mocks return synchronously."""
    try:
        coro.send(None)
    except StopIteration as e:
        return e.value
    raise RuntimeError("Coroutine did not complete synchronously")


@pytest.fixture
def jira_plugin():
    return JiraPlugin()


def test_supported_tools(jira_plugin):
    tools = jira_plugin.get_supported_tools()
    assert "jira_list_issues" in tools
    assert "jira_create_issue" in tools
    assert "jira_update_issue" in tools
    assert "jira_transition_issue" in tools
    assert "jira_delete_issue" in tools
    assert "jira_get_sprints" in tools
    assert "jira_search_issues" in tools


def test_guardrail_rbac_rules_on_jira_tools():
    read_auth = {"user_role": "read", "entitlements": {"has_subscription": True}}
    write_auth = {"user_role": "write", "entitlements": {"has_subscription": True}}
    admin_auth = {"user_role": "admin", "entitlements": {"has_subscription": True}}

    # 1. Read role can read but cannot create or transition
    GuardrailEngine.verify_request("jira_list_issues", {"project_key": "PROJ"}, read_auth)
    with pytest.raises(GuardrailViolation) as exc:
        GuardrailEngine.verify_request("jira_create_issue", {"project_key": "PROJ", "summary": "Test"}, read_auth)
    assert exc.value.code == "GUARDRAIL_RBAC_WRITE_REQUIRED"

    with pytest.raises(GuardrailViolation) as exc:
        GuardrailEngine.verify_request("jira_transition_issue", {"issue_key": "PROJ-1", "status": "Done"}, read_auth)
    assert exc.value.code == "GUARDRAIL_RBAC_WRITE_REQUIRED"

    # 2. Write role can create/transition but cannot delete
    GuardrailEngine.verify_request("jira_create_issue", {"project_key": "PROJ", "summary": "Test"}, write_auth)
    GuardrailEngine.verify_request("jira_transition_issue", {"issue_key": "PROJ-1", "status": "Done"}, write_auth)
    with pytest.raises(GuardrailViolation) as exc:
        GuardrailEngine.verify_request("jira_delete_issue", {"issue_key": "PROJ-1"}, write_auth)
    assert exc.value.code == "GUARDRAIL_RBAC_ADMIN_REQUIRED"

    # 3. Admin role can delete
    GuardrailEngine.verify_request("jira_delete_issue", {"issue_key": "PROJ-1"}, admin_auth)


def test_execute_jira_create_issue(jira_plugin):
    auth = {
        "jira_url": "https://testorg.atlassian.net",
        "jira_token": "mock_jwt_token",
        "user_role": "write",
        "external_id": "usr_999",
    }
    params = {
        "project_key": "PROJ",
        "summary": "Implement OAuth SSO",
        "description": "Details here",
        "issue_type": "Task",
    }

    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 201
    mock_resp.json.return_value = {"id": "10042", "key": "PROJ-42"}

    mock_client = MagicMock()
    mock_client.post = AsyncMock(return_value=mock_resp)

    with patch("plugins.pm_jira.httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__.return_value = mock_client
        res = _run(jira_plugin.execute("jira_create_issue", params, auth))

        assert res["success"] is True
        assert res["key"] == "PROJ-42"
        assert res["summary"] == "Implement OAuth SSO"


def test_execute_jira_transition_issue(jira_plugin):
    auth = {
        "jira_url": "https://testorg.atlassian.net",
        "jira_token": "mock_jwt_token",
        "user_role": "write",
    }
    params = {
        "issue_key": "PROJ-42",
        "status": "done",
    }

    mock_get_resp = MagicMock(spec=httpx.Response)
    mock_get_resp.status_code = 200
    mock_get_resp.json.return_value = {
        "transitions": [
            {"id": "21", "name": "In Progress"},
            {"id": "31", "name": "Done"},
        ]
    }
    mock_post_resp = MagicMock(spec=httpx.Response)
    mock_post_resp.status_code = 204

    mock_client = MagicMock()
    mock_client.get = AsyncMock(return_value=mock_get_resp)
    mock_client.post = AsyncMock(return_value=mock_post_resp)

    with patch("plugins.pm_jira.httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__.return_value = mock_client
        res = _run(jira_plugin.execute("jira_transition_issue", params, auth))
        assert res["success"] is True
        assert res["status"] == "Done"


def test_execute_jira_delete_issue(jira_plugin):
    auth = {
        "jira_url": "https://testorg.atlassian.net",
        "jira_token": "mock_jwt_token",
        "user_role": "admin",
    }
    params = {"issue_key": "PROJ-42"}

    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 204

    mock_client = MagicMock()
    mock_client.delete = AsyncMock(return_value=mock_resp)

    with patch("plugins.pm_jira.httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__.return_value = mock_client
        res = _run(jira_plugin.execute("jira_delete_issue", params, auth))
        assert res["success"] is True
        assert "PROJ-42 permanently deleted" in res["message"]


def test_tool_registry_routing():
    plugin = ToolRegistry.get_plugin("pm", "jira_create_issue")
    assert isinstance(plugin, JiraPlugin)

    search_res = ToolRegistry.search(query="jira_create")
    assert "jira" in search_res
    assert "jira_create_issue" in search_res["jira"]
