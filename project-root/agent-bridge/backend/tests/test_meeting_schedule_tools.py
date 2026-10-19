"""
tests/test_meeting_schedule_tools.py — Unit tests for scheduling and voice operations via agent tools.
"""
from __future__ import annotations

import sys
import unittest
from unittest.mock import MagicMock


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
        lc_messages = MagicMock()
        sys.modules["langchain_core"] = lc
        sys.modules["langchain_core.tools"] = lc_tools
        sys.modules["langchain_core.messages"] = lc_messages

    if "langchain_google_genai" not in sys.modules:
        lgg = MagicMock()
        sys.modules["langchain_google_genai"] = lgg


_ensure_mock_langchain()


class TestScheduledMeetingStoreAndTools(unittest.TestCase):
    def test_dual_memory_store_create_and_list_schedule(self):
        from agent.agent import DualMemoryStore

        mock_redis = MagicMock()
        mock_mongo = MagicMock()
        mock_mongo.scheduled_meetings.insert_one.return_value.inserted_id = "sched-123"

        sample_docs = [
            {
                "_id": "sched-123",
                "orgId": "org-1",
                "title": "Engineering Standup",
                "recurrence": "weekdays",
                "time": "10:00",
                "timezone": "America/New_York",
                "channelName": "standup-voice",
                "channelId": "v-1",
                "enabled": True,
                "lastStatus": "idle",
            }
        ]
        mock_mongo.scheduled_meetings.find.return_value.sort.return_value = sample_docs

        store = DualMemoryStore(redis_client=mock_redis, mongo_db=mock_mongo)

        # 1. Create
        created = store.create_scheduled_meeting({
            "title": "Engineering Standup",
            "recurrence": "weekdays",
            "time": "10:00",
            "timezone": "America/New_York",
            "channelName": "standup-voice",
            "channelId": "v-1",
            "guildId": "g-1",
        }, org_id="org-1")

        self.assertIsNotNone(created)
        self.assertEqual(created["id"], "sched-123")
        mock_mongo.scheduled_meetings.insert_one.assert_called_once()

        # 2. List
        listed = store.list_scheduled_meetings(org_id="org-1", guild_id="g-1")
        self.assertEqual(len(listed), 1)
        self.assertEqual(listed[0]["title"], "Engineering Standup")
        self.assertEqual(listed[0]["time"], "10:00")

    def test_dual_memory_store_delete_schedule(self):
        from agent.agent import DualMemoryStore

        mock_redis = MagicMock()
        mock_mongo = MagicMock()
        mock_mongo.scheduled_meetings.delete_one.return_value.deleted_count = 1

        store = DualMemoryStore(redis_client=mock_redis, mongo_db=mock_mongo)
        deleted = store.delete_scheduled_meeting("507f1f77bcf86cd799439011", org_id="org-1")
        self.assertTrue(deleted)

    def test_schedule_meeting_tool(self):
        from agent.tools import build_tools

        mock_pm = MagicMock()
        mock_memory = MagicMock()
        mock_memory.create_scheduled_meeting.return_value = {
            "id": "sched-999",
            "title": "Daily Standup",
            "recurrence": "weekdays",
            "time": "09:30",
            "timezone": "UTC",
        }

        tools = build_tools(
            mock_pm,
            "proj-123",
            tier="write",
            memory_store=mock_memory,
            project_key="proj-key",
            guild_id="guild-101",
            channel_id="ch-202",
            channel_name="general-voice",
            org_id="org-test",
        )

        schedule_tool = next((t for t in tools if getattr(t, "name", None) == "schedule_meeting"), None)
        self.assertIsNotNone(schedule_tool)

        res = schedule_tool.invoke({
            "title": "Daily Standup",
            "recurrence": "weekdays",
            "time": "09:30",
            "timezone": "UTC",
            "channel_name_or_id": "general-voice",
        })

        self.assertIn("Scheduled Meeting Created", res)
        self.assertIn("sched-999", res)
        mock_memory.create_scheduled_meeting.assert_called_once()

    def test_list_scheduled_meetings_tool(self):
        from agent.tools import build_tools

        mock_pm = MagicMock()
        mock_memory = MagicMock()
        mock_memory.list_scheduled_meetings.return_value = [
            {
                "id": "s-1",
                "title": "Morning Sync",
                "recurrence": "daily",
                "time": "10:00",
                "timezone": "UTC",
                "channelName": "voice-room",
                "enabled": True,
            }
        ]

        tools = build_tools(
            mock_pm,
            "proj-123",
            tier="read",
            memory_store=mock_memory,
            project_key="proj-key",
            guild_id="guild-101",
            org_id="org-test",
        )

        list_tool = next((t for t in tools if getattr(t, "name", None) == "list_scheduled_meetings"), None)
        self.assertIsNotNone(list_tool)

        res = list_tool.invoke({})
        self.assertIn("Morning Sync", res)
        self.assertIn("10:00", res)

    def test_start_and_stop_voice_meeting_tools(self):
        from agent.tools import build_tools

        mock_pm = MagicMock()
        mock_memory = MagicMock()
        mock_memory.start_voice_meeting.return_value = {"started": True}
        mock_memory.stop_voice_meeting.return_value = {"stopped": True}

        tools = build_tools(
            mock_pm,
            "proj-123",
            tier="write",
            memory_store=mock_memory,
            project_key="proj-key",
            guild_id="guild-101",
            channel_id="ch-202",
            channel_name="standup-voice",
            org_id="org-test",
        )

        start_tool = next((t for t in tools if getattr(t, "name", None) == "start_voice_meeting"), None)
        stop_tool = next((t for t in tools if getattr(t, "name", None) == "stop_voice_meeting"), None)
        self.assertIsNotNone(start_tool)
        self.assertIsNotNone(stop_tool)

        res_start = start_tool.invoke({"channel_name_or_id": "standup-voice", "duration_minutes": 20})
        self.assertIn("Voice Meeting Started", res_start)

        res_stop = stop_tool.invoke({})
        self.assertIn("Voice Meeting Stopped", res_stop)


if __name__ == "__main__":
    unittest.main()
