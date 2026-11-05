from core.fallback import FallbackEngine

def test_fuzzy_fallback_did_you_mean():
    available_tools = [
        "taiga_list_tasks",
        "taiga_create_task",
        "taiga_update_task",
        "taiga_delete_task",
        "taiga_get_milestones"
    ]
    auth = {"org_id": "test_org", "external_id": "discord_123"}

    # Simulate an LLM misspelling or hallucinating a tool name
    resp = FallbackEngine.handle_unsupported_tool(
        category="pm",
        tool_name="create_task",
        available_tools=available_tools,
        auth=auth
    )

    assert resp["status"] == "error"
    assert resp["error_code"] == "TOOL_NOT_SUPPORTED"
    assert resp["requested_tool"] == "create_task"
    assert "taiga_create_task" in resp["did_you_mean"]
    assert "instructions_for_llm" in resp

def test_fallback_no_match():
    available_tools = ["taiga_list_tasks", "taiga_create_task"]
    auth = {"org_id": "test_org", "external_id": "discord_123"}

    resp = FallbackEngine.handle_unsupported_tool(
        category="pm",
        tool_name="zzzz_nonexistent_tool_12345",
        available_tools=available_tools,
        auth=auth
    )
    assert resp["status"] == "error"
    assert resp["did_you_mean"] == [] or resp["did_you_mean"] is None

