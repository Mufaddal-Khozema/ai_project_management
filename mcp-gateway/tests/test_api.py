import asyncio
from main import (
    health_check,
    search_tools_endpoint,
    execute_tool_endpoint,
    SearchRequest,
    ExecutePayload,
)

def _run(coro):
    try:
        coro.send(None)
    except StopIteration as e:
        return e.value
    raise RuntimeError("Coroutine did not complete synchronously")

def test_health_check():
    data = health_check()
    assert data["status"] == "healthy"
    assert "pm" in data["categories"]
    assert "meetings" in data["categories"]
    assert data["total_tools"] > 0

def test_search_tools():
    req = SearchRequest(query="task")
    data = search_tools_endpoint(req)
    assert data["status"] == "success"
    assert "pm" in data["results"]
    assert "taiga_create_task" in data["results"]["pm"]

def test_execute_unsupported_tool_fuzzy():
    payload = ExecutePayload(
        tool_type="pm",
        tool_name="make_task",
        parameters={},
        auth_context={"user_role": "write"}
    )
    data = _run(execute_tool_endpoint(payload))
    assert data["status"] == "error"
    assert data["error_code"] == "TOOL_NOT_SUPPORTED"
    assert "did_you_mean" in data

def test_execute_destructive_guardrail_block():
    payload = ExecutePayload(
        tool_type="pm",
        tool_name="taiga_delete_task",
        parameters={"task_id": 99},
        auth_context={"user_role": "write", "entitlements": {"has_subscription": True}}
    )
    data = _run(execute_tool_endpoint(payload))
    assert data["status"] == "forbidden"
    assert data["error_code"] == "GUARDRAIL_RBAC_ADMIN_REQUIRED"






