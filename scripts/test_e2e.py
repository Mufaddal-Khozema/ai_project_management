"""
scripts/test_e2e.py — Comprehensive End-to-End Test Suite for MCP Gateway and AI Agent Stack.
Supports live HTTP socket (localhost:8005) or in-process direct endpoint dispatch.
"""
from __future__ import annotations
import json
import os
import sys
import time

os.environ["TESTING"] = "true"
import httpx


# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Add mcp-gateway to sys.path
MCP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "mcp-gateway"))
if MCP_DIR not in sys.path:
    sys.path.insert(0, MCP_DIR)

MCP_URL = "http://localhost:8005"
BACKEND_URL = "http://localhost:8000"
VOICE_URL = "http://localhost:3001"

def print_header(title: str):
    print(f"\n{'='*65}")
    print(f">> {title}")
    print(f"{'='*65}")

def print_pass(step: str, detail: str = ""):
    print(f"  [PASS] {step} {f'({detail})' if detail else ''}")

def print_fail(step: str, err: str = ""):
    print(f"  [FAIL] {step} - {err}")

class MockResponse:
    def __init__(self, status_code: int, data: dict):
        self.status_code = status_code
        self._data = data
        self.text = json.dumps(data)

    def json(self):
        return self._data

class DirectGatewayClient:
    """Dispatches directly to route handlers without requiring socket port binding."""
    def __init__(self):
        import main
        self.main = main

    def get(self, path: str):
        if path == "/health":
            data = self.main.health_check()
            return MockResponse(200, data)
        return MockResponse(404, {"error": "Not found"})

    def post(self, path: str, json: dict = None):
        json = json or {}
        if path == "/tools/search":
            req = self.main.SearchRequest(**json)
            data = self.main.search_tools_endpoint(req)
            return MockResponse(200, data)
        elif path == "/tools/execute":
            payload = self.main.ExecutePayload(**json)
            coro = self.main.execute_tool_endpoint(payload)
            try:
                coro.send(None)
            except StopIteration as e:
                return MockResponse(200, e.value)
            raise RuntimeError("Tool execution did not complete synchronously")
        return MockResponse(404, {"error": "Not found"})

def get_client():
    """Tries real HTTP socket first; if unavailable, uses DirectGatewayClient."""
    try:
        resp = httpx.get(f"{MCP_URL}/health", timeout=0.8)
        if resp.status_code == 200:
            return httpx.Client(base_url=MCP_URL, timeout=10.0), "Live HTTP Socket (localhost:8005)"
    except Exception:
        pass

    return DirectGatewayClient(), "Direct In-Process Dispatcher"

def run_e2e():
    total_passed = 0
    total_failed = 0

    print_header("STAGE 1: Service Health Checks")
    client, mode = get_client()
    print(f"  [MODE] Running via {mode}")

    # 1. MCP Gateway Health
    try:
        resp = client.get("/health")
        if resp.status_code == 200 and resp.json().get("status") == "healthy":
            data = resp.json()
            print_pass("mcp-gateway health check", f"{data.get('total_tools')} tools across {data.get('categories')}")
            total_passed += 1
        else:
            print_fail("mcp-gateway health check failed", resp.text)
            total_failed += 1
    except Exception as e:
        print_fail("mcp-gateway health check exception", str(e))
        total_failed += 1

    # 2. Litestar Backend Health (probe if live)
    try:
        b_resp = httpx.get(f"{BACKEND_URL}/api/health", timeout=0.8)
        if b_resp.status_code == 200:
            print_pass("Litestar Backend health check", "Port 8000 OK")
            total_passed += 1
        else:
            print("  [INFO] Litestar Backend (port 8000) not active (optional for tool logic tests)")
    except Exception:
        print("  [INFO] Litestar Backend (port 8000) not active (optional for tool logic tests)")

    # 3. Voice Bot Backend Health (probe if live)
    try:
        v_resp = httpx.get(f"{VOICE_URL}/health", timeout=0.8)
        if v_resp.status_code == 200:
            print_pass("Scrum Master AI Voice service health check", "Port 3001 OK")
            total_passed += 1
        else:
            print("  [INFO] Voice service (port 3001) not active (optional for tool logic tests)")
    except Exception:
        print("  [INFO] Voice service (port 3001) not active (optional for tool logic tests)")

    print_header("STAGE 2: Dynamic Tool Discovery (Search Tools)")
    # Test tool search for PM
    resp = client.post("/tools/search", json={"query": "task", "category": "pm"})
    if resp.status_code == 200 and "taiga_create_task" in resp.json().get("results", {}).get("pm", {}):
        print_pass("Dynamic tool discovery query='task'", "Found taiga_create_task in 'pm'")
        total_passed += 1
    else:
        print_fail("Dynamic tool discovery", resp.text)
        total_failed += 1

    # Test tool search for Meetings
    resp = client.post("/tools/search", json={"query": "standup", "category": "meetings"})
    if resp.status_code == 200 and "meeting_start_standup" in resp.json().get("results", {}).get("meetings", {}):
        print_pass("Meeting tool discovery query='standup'", "Found meeting_start_standup in 'meetings'")
        total_passed += 1
    else:
        print_fail("Meeting tool discovery", resp.text)
        total_failed += 1

    print_header("STAGE 3: Multi-Tier GuardRails Verification")
    # Test RBAC Block: Read role trying to execute create
    resp = client.post("/tools/execute", json={
        "tool_type": "pm",
        "tool_name": "taiga_create_task",
        "parameters": {"subject": "Blocked Task"},
        "auth_context": {"user_role": "read", "entitlements": {"has_subscription": True}}
    })
    res_data = resp.json()
    if res_data.get("status") == "forbidden" and res_data.get("error_code") == "GUARDRAIL_RBAC_WRITE_REQUIRED":
        print_pass("RBAC Guard: 'read' role successfully blocked from write mutation")
        total_passed += 1
    else:
        print_fail("RBAC Guard failed to block read role", resp.text)
        total_failed += 1

    # Test Destructive Gate: Write role trying to delete
    resp = client.post("/tools/execute", json={
        "tool_type": "pm",
        "tool_name": "taiga_delete_task",
        "parameters": {"task_id": 999},
        "auth_context": {"user_role": "write", "entitlements": {"has_subscription": True}}
    })
    res_data = resp.json()
    if res_data.get("status") == "forbidden" and res_data.get("error_code") == "GUARDRAIL_RBAC_ADMIN_REQUIRED":
        print_pass("Destructive Action Guard: 'write' role successfully blocked from deleting task")
        total_passed += 1
    else:
        print_fail("Destructive Action Guard failed to block non-admin", resp.text)
        total_failed += 1

    print_header("STAGE 4: Fuzzy Fallback & LLM Self-Healing")
    # Simulate LLM hallucinating 'create_ticket' instead of 'taiga_create_task'
    resp = client.post("/tools/execute", json={
        "tool_type": "pm",
        "tool_name": "create_ticket",
        "parameters": {"title": "Fix navbar"},
        "auth_context": {"user_role": "write", "org_id": "test_org", "external_id": "discord_user_1"}
    })
    res_data = resp.json()
    suggestions = res_data.get("did_you_mean") or []
    if res_data.get("status") == "error" and res_data.get("error_code") == "TOOL_NOT_SUPPORTED" and "taiga_create_task" in suggestions:
        print_pass("Fuzzy Matcher: 'create_ticket' triggered did_you_mean suggestions", f"Suggestions: {suggestions}")
        total_passed += 1
    else:
        print_fail("Fuzzy fallback did not provide expected suggestions", resp.text)
        total_failed += 1

    print(f"\n{'='*65}")
    print(f">> E2E TEST SUMMARY: {total_passed} PASSED | {total_failed} FAILED")
    print(f"{'='*65}\n")
    if total_failed == 0:
        print("[SUCCESS] All End-to-End MCP Pipeline Stages are Healthy and Verified!\n")
    else:
        sys.exit(1)

if __name__ == "__main__":
    run_e2e()
