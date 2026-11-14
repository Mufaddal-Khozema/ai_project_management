"""
tests/test_dynamic_platform.py — Unit tests for DynamicPMPlatform adapter and dynamic binding.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch
import pytest

from core.base import ProjectContext, ProjectItem
from core.registry import PlatformRegistry
import platforms.pm.taiga_platform  # noqa: triggers self-registration
import platforms.pm.jira_platform   # noqa: triggers self-registration
import platforms.pm.dynamic_platform  # noqa: triggers self-registration
from platforms.pm.dynamic_platform import DynamicPMPlatform
from platforms.pm.jira_platform import JiraPlatform
from platforms.pm.taiga_platform import TaigaPlatform
from services.reminder_service import DueDateReminderService


class TestDynamicPMPlatformRegistration:
    def test_registered_in_registry(self):
        assert "dynamic" in PlatformRegistry.list_pm()
        cls = PlatformRegistry.get_pm("dynamic")
        assert cls is DynamicPMPlatform


class TestDynamicPMPlatformBinding:
    def test_default_provider_taiga(self):
        dyn = DynamicPMPlatform(default_provider="taiga")
        assert dyn._active_provider == "taiga"
        assert isinstance(dyn.active_pm, TaigaPlatform)

    def test_bind_jira_provider(self):
        dyn = DynamicPMPlatform(default_provider="taiga")
        jira_cfg = {
            "instance_url": "https://example.atlassian.net",
            "token": "test-token",
            "user_email": "user@example.com",
        }
        inst = dyn.bind_provider("jira", jira_cfg)
        assert isinstance(inst, JiraPlatform)
        assert dyn._active_provider == "jira"
        assert dyn.active_pm is inst
        assert inst._http is not None
        assert inst._http.base_url == "https://example.atlassian.net"
        assert inst._http.token == "test-token"

    def test_instance_caching_and_switching(self):
        dyn = DynamicPMPlatform(default_provider="taiga")
        taiga_inst = dyn.bind_provider("taiga")
        jira_inst = dyn.bind_provider("jira", {
            "instance_url": "https://test.atlassian.net",
            "token": "tok1",
        })

        assert dyn.active_pm is jira_inst
        # Switch back to taiga
        switched = dyn.bind_provider("taiga")
        assert switched is taiga_inst
        assert dyn.active_pm is taiga_inst

    def test_unknown_provider_fallback(self):
        dyn = DynamicPMPlatform(default_provider="taiga")
        inst = dyn.bind_provider("unknown_platform_xyz")
        assert dyn._active_provider == "taiga"
        assert isinstance(inst, TaigaPlatform)


class TestDynamicPMPlatformDelegation:
    def test_delegates_to_active_pm(self):
        dyn = DynamicPMPlatform()
        mock_pm = MagicMock()
        mock_item = ProjectItem(
            platform="jira",
            item_id="101",
            item_type="task",
            subject="Test ticket",
            description="",
            status="Open",
            assignee=None,
            tags=[],
            url=None,
        )
        mock_pm.create_item.return_value = mock_item
        mock_pm.get_due_items.return_value = [{"id": "101", "ref": "JIR-1", "due_date": "2026-11-20"}]
        mock_pm.display_name = "Mocked Jira"

        dyn._instances["mock"] = mock_pm
        dyn._active_provider = "mock"

        item = dyn.create_item("PROJ", "task", "Test ticket")
        assert item.item_id == "101"
        mock_pm.create_item.assert_called_once_with(
            project_id="PROJ",
            item_type="task",
            subject="Test ticket",
            description="",
            assigned_to=None,
            tags=None,
        )

        due = dyn.get_due_items("PROJ", days_ahead=3)
        assert len(due) == 1
        mock_pm.get_due_items.assert_called_once_with("PROJ", days_ahead=3)


class TestDueDateReminderDynamicResolution:
    def test_jira_channel_reminders_resolved_dynamically(self):
        mock_comm = MagicMock()
        mock_comm.platform_id = "discord"

        dyn_pm = DynamicPMPlatform(default_provider="taiga")

        mock_id_client = MagicMock()
        mock_id_client.is_configured.return_value = True

        mock_id_res = MagicMock()
        mock_id_res.linked = True
        mock_id_res.project = {"provider": "jira", "project_slug": "PROJ"}
        mock_id_client.resolve_identity.return_value = mock_id_res
        mock_id_client.get_jira_credentials.return_value = {
            "instance_url": "https://test.atlassian.net",
            "token": "jira_tok_abc",
            "user_email": "dev@test.com",
        }

        # Mock the active pm methods
        with patch.object(JiraPlatform, "get_project_id", return_value="10001"):
            with patch.object(JiraPlatform, "get_due_items", return_value=[{
                "id": "10001",
                "ref": "PROJ-12",
                "type": "story",
                "subject": "Implement dynamic Jira reminder",
                "assigned_to": "ghasnain",
                "due_date": "2026-11-15",
            }]):
                service = DueDateReminderService(
                    comm=mock_comm,
                    pm=dyn_pm,
                    channel_map={"guild1": {"chan1": "PROJ"}},
                    identity_client=mock_id_client,
                )

                pending = service.get_pending_reminders()
                assert len(pending) == 1
                guild_id, chan_id, assignee, cache_key, msg_content = pending[0]

                assert chan_id == "chan1"
                assert assignee == "ghasnain"
                assert cache_key.startswith("jira_due_remind:10001:story:10001:2026-11-15")
                assert "PROJ-12" in msg_content
                assert "Implement dynamic Jira reminder" in msg_content
                assert dyn_pm._active_provider == "jira"
