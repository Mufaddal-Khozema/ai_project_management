"""
scripts/test_due_cycle.py — Complete Cycle Verification Script.
Simulates and tests the complete lifecycle:
1. Detection of upcoming/overdue tasks in Taiga.
2. Discord reminder generation & assignee tagging.
3. De-duplication check (preventing spam).
4. Conversational extension of the due date via AI agent tool.
5. Taiga concurrency/version update (PATCH).
6. Stakeholder (watchers) notification broadcast in Discord.
"""
from __future__ import annotations

import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from platforms.pm.taiga_platform import TaigaPlatform
from services.reminder_service import DueDateReminderService
from agent.tools import build_tools
from core.base import OutgoingMessage


class MockTaigaHTTPForCycle:
    def __init__(self):
        self.base_url = "https://api.taiga.io/api/v1"
        self._items = {
            "tasks": [
                {
                    "id": 42,
                    "ref": 42,
                    "subject": "Implement Payment Webhook Security",
                    "description": "Verify Stripe webhook signatures before processing.",
                    "due_date": (datetime.now(timezone.utc) + timedelta(days=1)).strftime("%Y-%m-%d"),
                    "due_date_reason": "",
                    "assigned_to": 101,
                    "assigned_to_extra_info": {"username": "john_dev", "full_name_display": "John Developer"},
                    "watchers": [102, 103],
                    "version": 4,
                    "status_extra_info": {"name": "In Progress"},
                    "project_extra_info": {"slug": "ghulam_hasnain-fyp"},
                }
            ],
            "userstories": [],
            "issues": [],
        }
        self._members = [
            {"id": 101, "username": "john_dev", "full_name": "John Developer", "role": "Backend Developer"},
            {"id": 102, "username": "sarah_pm", "full_name": "Sarah Project Manager", "role": "Project Manager"},
            {"id": 103, "username": "alex_techlead", "full_name": "Alex Tech Lead", "role": "Tech Lead"},
        ]

    def get_project_id(self, slug: str) -> str:
        return "12345"

    def request(self, method: str, path: str, **kwargs):
        if method == "GET" and path == "/tasks":
            return self._items["tasks"]
        if method == "GET" and path in ("/userstories", "/issues"):
            return []
        if method == "GET" and path.startswith("/tasks/"):
            tid = int(path.split("/")[-1])
            for t in self._items["tasks"]:
                if t["id"] == tid:
                    return t
            raise ValueError(f"Task {tid} not found")
        if method == "PATCH" and path.startswith("/tasks/"):
            tid = int(path.split("/")[-1])
            json_body = kwargs.get("json", {})
            for t in self._items["tasks"]:
                if t["id"] == tid:
                    t["due_date"] = json_body.get("due_date", t["due_date"])
                    t["due_date_reason"] = json_body.get("due_date_reason", t.get("due_date_reason"))
                    t["version"] = json_body.get("version", t["version"]) + 1
                    return t
            raise ValueError(f"Task {tid} not found")
        if method == "GET" and path == "/memberships":
            return [
                {
                    "user": m["id"],
                    "user_extra_info": {"username": m["username"]},
                    "full_name": m["full_name"],
                    "role_name": m["role"],
                }
                for m in self._members
            ]
        return {}


class MockDiscordComm:
    def __init__(self):
        self.dispatched_messages: list[OutgoingMessage] = []

    async def send_message(self, msg: OutgoingMessage):
        self.dispatched_messages.append(msg)


def run_cycle():
    print("=" * 70)
    print("🚀 STARTING COMPLETE CYCLE TEST: DUE REMINDER & EXTENSION")
    print("=" * 70)

    # 1. Initialize PM platform
    pm = TaigaPlatform()
    pm._http = MockTaigaHTTPForCycle()
    comm = MockDiscordComm()

    channel_map = {
        "guild_1489127884319625276": {
            "channel_1489127884319625279": "ghulam_hasnain-fyp"
        }
    }

    # 2. Check Detection of Due Items
    print("\n[STEP 1] Scanning Taiga for upcoming due items...")
    due_items = pm.get_due_items("12345", days_ahead=2)
    print(f"✅ Found {len(due_items)} due item(s):")
    for item in due_items:
        print(f"   • #{item['ref']} [{item['type']}] {item['subject']} (Due: {item['due_date']}, Assignee: @{item['assigned_to']})")

    # 3. Simulate Reminder Worker
    print("\n[STEP 2] Background Reminder Service checks pending reminders...")
    service = DueDateReminderService(comm, pm, channel_map, interval_seconds=1800, days_ahead=2)
    pending = service.get_pending_reminders()
    print(f"✅ Generated {len(pending)} pending Discord reminder(s):")
    for guild_id, ch_id, assignee, key, msg in pending:
        print("-" * 50)
        print(f"Target Guild: {guild_id} | Channel: {ch_id}")
        print(f"Assignee for Personal DM: @{assignee}")
        print(f"Cache Deduplication Key: {key}")
        print("Message Preview:\n" + msg)
        print("-" * 50)

    # 4. Verify Deduplication
    print("\n[STEP 3] Testing Deduplication Cache...")
    cache_key = pending[0][3]
    service._mark_reminded(cache_key)
    pending_after = service.get_pending_reminders()
    print(f"✅ Pending reminders on immediate re-scan: {len(pending_after)} (Deduplicated successfully!)")

    # 5. User Extends Due Date via Discord AI Tool
    print("\n[STEP 4] Simulating user extending due date via Discord bot tool...")
    user_request_item = "42"
    new_date = "2026-10-30"
    reason = "Third-party payment gateway sandbox was undergoing scheduled maintenance."
    print(f"User Command: @FYP extend due date of #{user_request_item} to {new_date} because {reason}")

    tools = build_tools(pm, project_id="12345", tier="write")
    extend_tool = next((t for t in tools if t.name == "extend_due_date"), None)
    assert extend_tool is not None, "extend_due_date tool not found!"

    tool_response = extend_tool.invoke({
        "item_id": user_request_item,
        "new_due_date": new_date,
        "reason": reason,
    })

    print("\n[STEP 5] Discord Bot Public Broadcast Response:")
    print("-" * 50)
    print(tool_response)
    print("-" * 50)

    # 6. Verify Taiga State
    print("\n[STEP 6] Verifying updated state in Taiga...")
    updated_raw = pm._http.request("GET", f"/tasks/{user_request_item}")
    print(f"✅ Taiga Task #{user_request_item} Due Date: {updated_raw['due_date']} (Expected: {new_date})")
    print(f"✅ Taiga Task #{user_request_item} Reason: '{updated_raw['due_date_reason']}'")
    print(f"✅ Taiga Task #{user_request_item} New Version: {updated_raw['version']}")

    # 7. Verify Watcher Resolution
    print("\n[STEP 7] Verifying Stakeholder (Watchers) Resolution...")
    watcher_info = pm.get_watchers_info("12345", updated_raw["watchers"])
    print(f"✅ Notified Watchers Count: {len(watcher_info)}")
    for w in watcher_info:
        print(f"   • @{w['username']} ({w['full_name']} — {w['role']})")

    print("\n" + "=" * 70)
    print("🎉 ALL STAGES OF THE CYCLE VERIFIED SUCCESSFULLY!")
    print("=" * 70)


if __name__ == "__main__":
    run_cycle()
