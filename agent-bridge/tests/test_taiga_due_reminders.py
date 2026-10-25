"""
tests/test_taiga_due_reminders.py
Tests for Taiga due date tracking, extensions, watcher notifications, and the proactive reminder service.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from core.base import OutgoingMessage, ProjectItem
from platforms.pm.taiga_platform import TaigaPlatform
from services.reminder_service import DueDateReminderService
from agent.tools import build_tools


class MockTaigaHTTP:
    def __init__(self):
        self.base_url = "https://api.taiga.io/api/v1"
        self._items = {
            "tasks": [
                {
                    "id": 101,
                    "ref": 10,
                    "subject": "Fix payment auth bug",
                    "description": "Auth token expires too quickly",
                    "due_date": (datetime.now(timezone.utc) + timedelta(days=1)).strftime("%Y-%m-%d"),
                    "due_date_reason": "",
                    "assigned_to": 201,
                    "assigned_to_extra_info": {"username": "john_dev", "full_name_display": "John Dev"},
                    "watchers": [202, 203],
                    "version": 2,
                    "status_extra_info": {"name": "In progress"},
                    "project_extra_info": {"slug": "sample-project"},
                },
                {
                    "id": 102,
                    "ref": 11,
                    "subject": "Legacy task far in future",
                    "description": "Not urgent",
                    "due_date": (datetime.now(timezone.utc) + timedelta(days=20)).strftime("%Y-%m-%d"),
                    "due_date_reason": "",
                    "assigned_to": None,
                    "assigned_to_extra_info": None,
                    "watchers": [],
                    "version": 1,
                    "status_extra_info": {"name": "New"},
                    "project_extra_info": {"slug": "sample-project"},
                },
            ],
            "userstories": [],
            "issues": [],
        }
        self._members = [
            {"id": 201, "username": "john_dev", "full_name": "John Dev", "role": "Developer"},
            {"id": 202, "username": "sarah_pm", "full_name": "Sarah PM", "role": "Product Manager"},
            {"id": 203, "username": "alex_lead", "full_name": "Alex Lead", "role": "Tech Lead"},
        ]

    def get_project_id(self, slug: str) -> str:
        return "999"

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
                    t["version"] = t["version"] + 1
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
        if method == "GET" and path == "/projects/by_slug":
            return {"id": 999}
        return {}


@pytest.fixture
def taiga_pm():
    pm = TaigaPlatform()
    pm._http = MockTaigaHTTP()
    return pm


def test_get_due_items(taiga_pm):
    items = taiga_pm.get_due_items("999", days_ahead=2)
    assert len(items) == 1
    item = items[0]
    assert item["id"] == "101"
    assert item["ref"] == "10"
    assert item["assigned_to"] == "john_dev"
    assert item["watchers"] == [202, 203]


def test_extend_due_date(taiga_pm):
    new_due = "2026-11-01"
    res = taiga_pm.extend_due_date("999", "101", new_due, reason="Waiting for API partner")
    assert res["new_due_date"] == new_due
    assert res["reason"] == "Waiting for API partner"
    assert res["watchers"] == [202, 203]
    assert res["version"] == 3


def test_get_watchers_info(taiga_pm):
    watchers = taiga_pm.get_watchers_info("999", [202, 203, 9999])
    assert len(watchers) == 3
    usernames = [w["username"] for w in watchers]
    assert "sarah_pm" in usernames
    assert "alex_lead" in usernames
    assert "user_9999" in usernames


def test_extend_due_date_tool(taiga_pm):
    tools = build_tools(taiga_pm, project_id="999", tier="write")
    tool_map = {t.name: t for t in tools}
    assert "extend_due_date" in tool_map
    assert "get_upcoming_due_items" in tool_map

    extend_tool = tool_map["extend_due_date"]
    output = extend_tool.invoke({"item_id": "101", "new_due_date": "2026-11-05", "reason": "Client design review delayed"})

    assert "Due Date Extended" in output
    assert "2026-11-05" in output
    assert "Client design review delayed" in output
    assert "@sarah_pm" in output
    assert "@alex_lead" in output


def test_get_upcoming_due_items_tool(taiga_pm):
    tools = build_tools(taiga_pm, project_id="999", tier="read")
    tool_map = {t.name: t for t in tools}
    upcoming_tool = tool_map["get_upcoming_due_items"]

    output = upcoming_tool.invoke({"days_ahead": 3})
    assert "Found 1 item(s) due soon" in output
    assert "#10" in output
    assert "@john_dev" in output


class FakeComm:
    def __init__(self):
        self.sent_messages: list[OutgoingMessage] = []

    async def send_message(self, msg: OutgoingMessage) -> None:
        self.sent_messages.append(msg)


def test_due_date_reminder_service(taiga_pm):
    comm = FakeComm()
    channel_map = {
        "guild_123": {
            "channel_456": "sample-project"
        }
    }

    service = DueDateReminderService(
        comm=comm,
        pm=taiga_pm,
        channel_map=channel_map,
        interval_seconds=60,
        days_ahead=2,
    )

    # First check: pending list should have 1 item
    pending = service.get_pending_reminders()
    assert len(pending) == 1
    guild_id, channel_id, assignee, cache_key, content = pending[0]
    assert channel_id == "channel_456"
    assert assignee == "john_dev"
    assert "999:tasks:101:" in cache_key
    assert "#10" in content
    assert "@john_dev" in content
    assert "TASK DUE SOON" in content or "TASK DUE TODAY" in content

    # Simulate marking as reminded (as check_and_send_reminders does)
    service._mark_reminded(cache_key)

    # Second check: deduplication cache suppresses duplicate reminder
    pending_second = service.get_pending_reminders()
    assert len(pending_second) == 0

