"""
tests/test_jira_platform.py — Comprehensive unit tests for JiraPlatform adapter.
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch
import pytest

from core.registry import PlatformRegistry
import platforms.pm.jira_platform  # noqa: triggers self-registration
from platforms.pm.jira_platform import JiraPlatform, _text_to_adf, _adf_to_text


class TestJiraPlatformRegistration:
    def test_registered_in_registry(self):
        assert "jira" in PlatformRegistry.list_pm()
        cls = PlatformRegistry.get_pm("jira")
        assert cls is JiraPlatform


class TestJiraADFFormatting:
    def test_text_to_adf_simple(self):
        adf = _text_to_adf("Hello World")
        assert adf["type"] == "doc"
        assert adf["version"] == 1
        assert len(adf["content"]) == 1
        assert adf["content"][0]["content"][0]["text"] == "Hello World"

    def test_text_to_adf_paragraphs(self):
        adf = _text_to_adf("Paragraph 1\n\nParagraph 2")
        assert len(adf["content"]) == 2
        assert adf["content"][0]["content"][0]["text"] == "Paragraph 1"
        assert adf["content"][1]["content"][0]["text"] == "Paragraph 2"

    def test_text_to_adf_empty(self):
        adf = _text_to_adf("")
        assert adf["content"] == []

    def test_adf_to_text_nested(self):
        doc = {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {"type": "text", "text": "Fix "},
                        {"type": "text", "text": "the bug"},
                    ],
                },
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": "Immediately"}],
                },
            ],
        }
        text = _adf_to_text(doc)
        assert text == "Fix the bug Immediately"

    def test_adf_to_text_plain_string(self):
        assert _adf_to_text("Already plain text") == "Already plain text"


class TestJiraPlatformOperations:
    @pytest.fixture
    def jira(self):
        p = JiraPlatform()
        p.configure({
            "url": "https://myorg.atlassian.net",
            "email": "dev@myorg.com",
            "api_token": "secret_api_token",
            "context_cache_ttl": 60,
        })
        return p

    def test_headers_basic_auth(self, jira):
        headers = jira._http._headers()
        assert "Authorization" in headers
        assert headers["Authorization"].startswith("Basic ")
        assert headers["Content-Type"] == "application/json"

    def test_headers_bearer_token(self):
        p = JiraPlatform()
        p.configure({
            "url": "https://api.atlassian.com",
            "token": "oauth_access_token_123",
            "cloud_id": "test-cloud-id",
        })
        headers = p._http._headers()
        assert headers["Authorization"] == "Bearer oauth_access_token_123"
        assert p._http.base_url == "https://api.atlassian.com/ex/jira/test-cloud-id"

    @patch("platforms.pm.jira_platform.requests.request")
    def test_get_project_id(self, mock_req, jira):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = json.dumps({"id": "10001", "key": "PROJ", "name": "Project Alpha"})
        mock_resp.json.return_value = {"id": "10001", "key": "PROJ", "name": "Project Alpha"}
        mock_req.return_value = mock_resp

        pid = jira.get_project_id("proj")
        assert pid == "PROJ"

    @patch("platforms.pm.jira_platform.requests.request")
    def test_create_item(self, mock_req, jira):
        # 1st call for members list (if any), 2nd call for POST /issue, 3rd call for GET /issue/{key}
        mock_members = MagicMock(status_code=200, text="[]")
        mock_members.json.return_value = [
            {"accountId": "acc_123", "displayName": "Alice Smith", "emailAddress": "alice@test.com"}
        ]

        mock_post = MagicMock(status_code=201, text='{"key": "PROJ-101", "id": "101"}')
        mock_post.json.return_value = {"key": "PROJ-101", "id": "101"}

        mock_get = MagicMock(status_code=200, text='{}')
        mock_get.json.return_value = {
            "key": "PROJ-101",
            "id": "101",
            "fields": {
                "summary": "Fix auth login crash",
                "description": _text_to_adf("App crashes on login"),
                "status": {"name": "To Do"},
                "issuetype": {"name": "Bug"},
                "assignee": {"displayName": "Alice Smith"},
                "labels": ["critical", "backend"],
            },
        }

        mock_req.side_effect = [mock_members, mock_post, mock_get]

        item = jira.create_item(
            project_id="PROJ",
            item_type="bug",
            subject="Fix auth login crash",
            description="App crashes on login",
            assigned_to="Alice Smith",
            tags=["critical", "backend"],
        )

        assert item.item_id == "PROJ-101"
        assert item.platform == "jira"
        assert item.item_type == "bug"
        assert item.subject == "Fix auth login crash"
        assert item.assignee == "Alice Smith"
        assert "critical" in item.tags
        assert item.url == "https://myorg.atlassian.net/browse/PROJ-101"

    @patch("platforms.pm.jira_platform.requests.request")
    def test_update_item(self, mock_req, jira):
        mock_put = MagicMock(status_code=204, text="")
        mock_get = MagicMock(status_code=200, text='{}')
        mock_get.json.return_value = {
            "key": "PROJ-101",
            "id": "101",
            "fields": {
                "summary": "New updated summary",
                "description": _text_to_adf("New description"),
                "status": {"name": "In Progress"},
                "issuetype": {"name": "Task"},
            },
        }
        mock_req.side_effect = [mock_put, mock_get]

        item = jira.update_item("PROJ", "PROJ-101", {"summary": "New updated summary", "description": "New description"})
        assert item.item_id == "PROJ-101"
        assert item.subject == "New updated summary"

    @patch("platforms.pm.jira_platform.requests.request")
    def test_close_item(self, mock_req, jira):
        # 1. GET transitions
        mock_trans = MagicMock(status_code=200, text='{}')
        mock_trans.json.return_value = {
            "transitions": [
                {"id": "11", "name": "In Progress", "to": {"name": "In Progress", "statusCategory": {"key": "indeterminate"}}},
                {"id": "31", "name": "Done", "to": {"name": "Done", "statusCategory": {"key": "done"}}},
            ]
        }
        # 2. POST transition
        mock_post_trans = MagicMock(status_code=204, text="")
        # 3. GET issue
        mock_get = MagicMock(status_code=200, text='{}')
        mock_get.json.return_value = {
            "key": "PROJ-101",
            "id": "101",
            "fields": {
                "summary": "Completed item",
                "status": {"name": "Done"},
                "issuetype": {"name": "Task"},
            },
        }
        mock_req.side_effect = [mock_trans, mock_post_trans, mock_get]

        item = jira.close_item("PROJ", "PROJ-101")
        assert item.item_id == "PROJ-101"
        assert item.status == "Done"

    @patch("platforms.pm.jira_platform.requests.request")
    def test_list_items_with_jql(self, mock_req, jira):
        mock_search = MagicMock(status_code=200, text='{}')
        mock_search.json.return_value = {
            "total": 1,
            "issues": [
                {
                    "key": "PROJ-200",
                    "id": "200",
                    "fields": {
                        "summary": "Implement Kafka consumer",
                        "status": {"name": "In Review"},
                        "issuetype": {"name": "Story"},
                        "assignee": {"displayName": "Bob Builder"},
                    },
                }
            ],
        }
        mock_req.return_value = mock_search

        items = jira.list_items("PROJ", item_type="story", status="open", limit=10)
        assert len(items) == 1
        assert items[0].item_id == "PROJ-200"
        assert items[0].item_type == "story"

        # Verify JQL sent in POST
        called_args, called_kwargs = mock_req.call_args
        sent_body = called_kwargs.get("json", {})
        jql = sent_body.get("jql", "")
        assert 'project = "PROJ"' in jql
        assert 'issuetype in ("Story")' in jql
        assert "statusCategory != Done" in jql

    @patch("platforms.pm.jira_platform.requests.request")
    def test_list_members(self, mock_req, jira):
        mock_resp = MagicMock(status_code=200, text='{}')
        mock_resp.json.return_value = [
            {"accountId": "acc_1", "displayName": "Alice", "emailAddress": "alice@org.com"},
            {"accountId": "acc_2", "displayName": "Bob", "emailAddress": "bob@org.com"},
        ]
        mock_req.return_value = mock_resp

        members = jira.list_members("PROJ")
        assert len(members) == 2
        assert members[0]["username"] == "Alice"
        assert members[0]["id"] == "acc_1"
