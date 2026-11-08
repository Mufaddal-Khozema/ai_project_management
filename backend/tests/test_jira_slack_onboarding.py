"""
backend/tests/test_jira_slack_onboarding.py
Unit tests for Jira and Slack support across Backend OAuth, Integrations, Projects, and Identity.
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from litestar.exceptions import HTTPException

import piccolo.utils.sync
piccolo.utils.sync.run_sync = lambda coro: coro.close() if hasattr(coro, "close") else None

from lib import oauth
from services import projects as project_service
from services import integrations as integration_service
from services import identity as identity_service


def _run(coro):
    """Run a coroutine to completion when awaited mocks return synchronously."""
    try:
        coro.send(None)
    except StopIteration as e:
        return e.value
    raise RuntimeError("Coroutine did not complete synchronously")


# 1. Provider Pair Validation Tests
def test_validate_provider_pair_all_valid_combinations():
    project_service.validate_provider_pair("taiga", "discord")
    project_service.validate_provider_pair("jira", "discord")
    project_service.validate_provider_pair("taiga", "slack")
    project_service.validate_provider_pair("jira", "slack")


def test_validate_provider_pair_invalid_pm():
    with pytest.raises(HTTPException) as exc:
        project_service.validate_provider_pair("clickup", "slack")
    assert exc.value.status_code == 400
    assert "Unsupported project provider: clickup" in exc.value.detail


def test_validate_provider_pair_invalid_comm():
    with pytest.raises(HTTPException) as exc:
        project_service.validate_provider_pair("jira", "teams")
    assert exc.value.status_code == 400
    assert "Unsupported channel provider: teams" in exc.value.detail


# 2. Scope & Member Provider Registry Tests
def test_scope_providers():
    assert "jira" in integration_service._SCOPE_PROVIDERS["projects"]
    assert "taiga" in integration_service._SCOPE_PROVIDERS["projects"]
    assert "slack" in integration_service._SCOPE_PROVIDERS["channels"]
    assert "discord" in integration_service._SCOPE_PROVIDERS["channels"]
    assert "jira" in integration_service._MEMBER_PROVIDERS
    assert "slack" in integration_service._MEMBER_PROVIDERS


# 3. Jira OAuth Helper Tests
def test_list_jira_projects_success():
    async def mock_coro():
        with patch("lib.oauth.get_jira_cloud_id", new=AsyncMock(return_value="cloud-abc")):
            mock_resp = MagicMock(status_code=200)
            mock_resp.json.return_value = [
                {"id": "10001", "name": "Sprint Board Project", "key": "SBP"},
                {"id": "10002", "name": "Backend Engine", "key": "ENG"},
            ]
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_resp)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            with patch("httpx.AsyncClient", return_value=mock_client):
                return await oauth.list_jira_projects("mock-access-token")

    projects = _run(mock_coro())
    assert len(projects) == 2
    assert projects[0] == {"id": "10001", "name": "Sprint Board Project", "slug": "SBP"}
    assert projects[1] == {"id": "10002", "name": "Backend Engine", "slug": "ENG"}


def test_list_jira_project_members_success():
    async def mock_coro():
        with patch("lib.oauth.get_jira_cloud_id", new=AsyncMock(return_value="cloud-abc")):
            mock_resp = MagicMock(status_code=200)
            mock_resp.json.return_value = [
                {
                    "accountId": "acc-1",
                    "displayName": "Alice Engineer",
                    "emailAddress": "alice@company.com",
                    "avatarUrls": {"48x48": "https://avatar.url/48"},
                }
            ]
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_resp)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            with patch("httpx.AsyncClient", return_value=mock_client):
                return await oauth.list_jira_project_members("mock-access-token", "10001")

    members = _run(mock_coro())
    assert len(members) == 1
    assert members[0]["id"] == "acc-1"
    assert members[0]["name"] == "Alice Engineer"
    assert members[0]["email"] == "alice@company.com"
    assert members[0]["avatar"] == "https://avatar.url/48"


# 4. Slack OAuth Helper Tests
def test_list_slack_channels_success():
    async def mock_coro():
        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = {
            "ok": True,
            "channels": [
                {"id": "C12345", "name": "general", "context_team_id": "T999"},
                {"id": "C67890", "name": "standup", "context_team_id": "T999"},
            ],
        }
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_client):
            return await oauth.list_slack_channels("mock-slack-token")

    channels = _run(mock_coro())
    assert len(channels) == 2
    assert channels[0]["id"] == "C12345"
    assert channels[0]["name"] == "general"
    assert channels[0]["guild_id"] == "T999"


def test_get_slack_channel_team_success():
    async def mock_coro():
        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = {
            "ok": True,
            "channel": {"id": "C12345", "context_team_id": "T999"},
        }
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_client):
            return await oauth.get_slack_channel_team("mock-slack-token", "C12345")

    team_id = _run(mock_coro())
    assert team_id == "T999"


def test_list_slack_channel_members_success():
    async def mock_coro():
        mock_members_resp = MagicMock(status_code=200)
        mock_members_resp.json.return_value = {"ok": True, "members": ["U001", "U002"]}

        mock_users_resp = MagicMock(status_code=200)
        mock_users_resp.json.return_value = {
            "ok": True,
            "members": [
                {
                    "id": "U001",
                    "name": "bob",
                    "real_name": "Bob Builder",
                    "is_bot": False,
                    "deleted": False,
                    "profile": {"email": "bob@build.com", "image_48": "https://img.48"},
                },
                {"id": "U002", "name": "slackbot", "is_bot": True, "deleted": False},
            ],
        }

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=[mock_members_resp, mock_users_resp])
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_client):
            return await oauth.list_slack_channel_members("mock-slack-token", "C12345")

    members = _run(mock_coro())
    assert len(members) == 1
    assert members[0]["id"] == "U001"
    assert members[0]["name"] == "Bob Builder"
    assert members[0]["email"] == "bob@build.com"


# 5. Integration Service Listing Tests
def test_integrations_list_projects_jira():
    async def mock_coro():
        fake_projects = [{"id": "10001", "name": "Project Alpha", "slug": "PA"}]
        with patch.object(integration_service, "_scope_credentials", new=AsyncMock(return_value=({"account_name": "atlassian-user"}, {"access_token": "tok"}))):
            with patch("lib.oauth.list_jira_projects", new=AsyncMock(return_value=fake_projects)):
                return await integration_service.list_projects("test@example.com", "jira")

    res = _run(mock_coro())
    assert res["provider"] == "jira"
    assert res["account_name"] == "atlassian-user"
    assert res["scopes"] == [{"id": "10001", "name": "Project Alpha", "slug": "PA"}]


def test_integrations_list_channels_slack():
    async def mock_coro():
        fake_channels = [{"id": "C1", "name": "general", "guild_id": "T1"}]
        with patch.object(integration_service, "_scope_credentials", new=AsyncMock(return_value=({"account_name": "slack-workspace"}, {"access_token": "tok"}))):
            with patch("lib.oauth.list_slack_channels", new=AsyncMock(return_value=fake_channels)):
                return await integration_service.list_channels("test@example.com", "slack")

    res = _run(mock_coro())
    assert res["provider"] == "slack"
    assert res["account_name"] == "slack-workspace"
    assert res["scopes"] == [{"id": "C1", "name": "general", "parent_id": "T1"}]


# 6. Project Resolution Tests
def test_resolve_project_jira():
    async def mock_coro():
        with patch.object(project_service, "_provider_payload", new=AsyncMock(return_value={"access_token": "tok"})):
            with patch("lib.oauth.list_jira_projects", new=AsyncMock(return_value=[{"id": "101", "name": "Jira Proj", "slug": "JP"}])):
                return await project_service._resolve_project(1, "jira", "101")

    name, slug = _run(mock_coro())
    assert name == "Jira Proj"
    assert slug == "JP"


def test_resolve_guild_slack():
    async def mock_coro():
        with patch.object(project_service, "_provider_payload", new=AsyncMock(return_value={"access_token": "tok"})):
            with patch("lib.oauth.get_slack_channel_team", new=AsyncMock(return_value="T-SLACK-TEAM")):
                return await project_service._resolve_guild(1, "slack", "C-CHANNEL")

    team_id = _run(mock_coro())
    assert team_id == "T-SLACK-TEAM"


if __name__ == "__main__":
    test_validate_provider_pair_all_valid_combinations()
    test_validate_provider_pair_invalid_pm()
    test_validate_provider_pair_invalid_comm()
    test_scope_providers()
    test_list_jira_projects_success()
    test_list_jira_project_members_success()
    test_list_slack_channels_success()
    test_get_slack_channel_team_success()
    test_list_slack_channel_members_success()
    test_integrations_list_projects_jira()
    test_integrations_list_channels_slack()
    test_resolve_project_jira()
    test_resolve_guild_slack()
    print("ALL 13 JIRA & SLACK ONBOARDING TESTS PASSED!")
