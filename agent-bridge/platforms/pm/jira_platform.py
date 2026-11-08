"""
platforms/pm/jira_platform.py — Full Jira Cloud REST API adapter.
Supports both Jira Cloud API v3 (ADF formatted) and Jira Server/Data Center,
using Basic Auth (email + API token) or Bearer Token (OAuth 2.0).
"""
from __future__ import annotations

import base64
import json
import logging
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import requests

from core.base import ProjectContext, ProjectItem, ProjectManagementPlatform
from core.registry import pm_platform

logger = logging.getLogger("agent_bridge.jira")

_TYPE_MAP = {
    "task": "Task",
    "tasks": "Task",
    "story": "Story",
    "stories": "Story",
    "userstory": "Story",
    "userstories": "Story",
    "bug": "Bug",
    "issue": "Bug",
    "issues": "Bug",
    "epic": "Epic",
    "epics": "Epic",
}


def _norm_type(item_type: str) -> str:
    cleaned = (item_type or "").lower().strip()
    return _TYPE_MAP.get(cleaned, item_type.capitalize() if item_type else "Task")


def _text_to_adf(text: str) -> dict[str, Any]:
    """Wraps plain text in Atlassian Document Format (ADF) JSON for Jira Cloud v3."""
    if not text:
        return {
            "type": "doc",
            "version": 1,
            "content": [],
        }
    paragraphs = [p for p in text.split("\n\n") if p.strip()] or [text]
    content = []
    for p in paragraphs:
        content.append({
            "type": "paragraph",
            "content": [{"type": "text", "text": p.strip()}],
        })
    return {
        "type": "doc",
        "version": 1,
        "content": content,
    }


def _adf_to_text(doc: Any) -> str:
    """Recursively extracts plain text from Atlassian Document Format (ADF)."""
    if isinstance(doc, str):
        return doc
    if not isinstance(doc, dict):
        return ""

    paragraphs = []

    def _extract_inlines(node: Any) -> str:
        if isinstance(node, dict):
            if node.get("type") == "text":
                return node.get("text", "")
            return "".join(_extract_inlines(c) for c in node.get("content", []))
        elif isinstance(node, list):
            return "".join(_extract_inlines(item) for item in node)
        return ""

    for block in doc.get("content", []):
        text = _extract_inlines(block).strip()
        if text:
            paragraphs.append(text)

    return " ".join(paragraphs) if paragraphs else _extract_inlines(doc).strip()


class _JiraHTTP:
    def __init__(
        self,
        base_url: str,
        email: str = "",
        api_token: str = "",
        token: str | None = None,
        cloud_id: str | None = None,
        api_version: str = "3",
    ):
        raw_url = (base_url or "").rstrip("/")
        self.api_version = api_version
        self.email = email or os.environ.get("JIRA_EMAIL", "")
        self.api_token = api_token or os.environ.get("JIRA_API_TOKEN", "")
        self.token = token or os.environ.get("JIRA_TOKEN") or os.environ.get("JIRA_ACCESS_TOKEN")
        self.cloud_id = cloud_id or os.environ.get("JIRA_CLOUD_ID")

        if self.cloud_id:
            self.base_url = f"https://api.atlassian.com/ex/jira/{self.cloud_id}"
        elif "atlassian.net" in raw_url:
            self.base_url = raw_url
        elif raw_url:
            self.base_url = raw_url
        else:
            self.base_url = os.environ.get("JIRA_URL", "https://api.atlassian.com").rstrip("/")

        self._project_cache: dict[str, dict[str, Any]] = {}
        self._board_cache: dict[str, int] = {}

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        elif self.email and self.api_token:
            auth_str = f"{self.email}:{self.api_token}"
            encoded = base64.b64encode(auth_str.encode("utf-8")).decode("utf-8")
            headers["Authorization"] = f"Basic {encoded}"
        else:
            # Fallback to env
            env_token = os.environ.get("JIRA_TOKEN") or os.environ.get("JIRA_ACCESS_TOKEN")
            if env_token:
                headers["Authorization"] = f"Bearer {env_token}"
            else:
                logger.warning("No Jira credentials supplied (email/api_token or Bearer token)")
        return headers

    def request(self, method: str, path: str, **kwargs) -> Any:
        # Determine full URL
        if path.startswith("http://") or path.startswith("https://"):
            url = path
        else:
            if not path.startswith("/rest/"):
                endpoint = f"/rest/api/{self.api_version}{path}"
            else:
                endpoint = path
            url = f"{self.base_url}{endpoint}"

        headers = self._headers()
        timeout = kwargs.pop("timeout", 30)

        r = requests.request(method, url, headers=headers, timeout=timeout, **kwargs)

        if r.status_code == 401:
            logger.warning("Jira authentication failed or token expired (HTTP 401)")
            raise PermissionError("Jira authentication failed: invalid credentials or expired token.")

        if r.status_code == 404:
            raise KeyError(f"Jira resource not found at {path}")

        r.raise_for_status()
        if r.status_code == 204 or not r.text.strip():
            return None
        return r.json()

    def get_project(self, key_or_id: str) -> dict[str, Any]:
        key = str(key_or_id).upper().strip()
        if key not in self._project_cache:
            data = self.request("GET", f"/project/{key}")
            self._project_cache[key] = data
            if "id" in data:
                self._project_cache[str(data["id"])] = data
        return self._project_cache[key]


def _to_item(raw: dict[str, Any], base_url: str) -> ProjectItem:
    fields = raw.get("fields", {})
    key = raw.get("key", str(raw.get("id", "")))
    issuetype = fields.get("issuetype", {})
    issue_type_name = issuetype.get("name", "Task")

    description = _adf_to_text(fields.get("description", ""))
    status = fields.get("status", {}).get("name", "Open")

    assignee = None
    assignee_data = fields.get("assignee")
    if assignee_data:
        assignee = (
            assignee_data.get("displayName")
            or assignee_data.get("emailAddress")
            or assignee_data.get("name")
        )

    labels = fields.get("labels", []) or []

    web_url = None
    if base_url and "api.atlassian.com" not in base_url:
        web_url = f"{base_url.rstrip('/')}/browse/{key}"

    return ProjectItem(
        platform="jira",
        item_id=key,
        item_type=issue_type_name.lower(),
        subject=fields.get("summary", ""),
        description=description,
        status=status,
        assignee=assignee,
        tags=labels,
        url=web_url,
        raw=raw,
    )


@pm_platform
class JiraPlatform(ProjectManagementPlatform):
    platform_id = "jira"
    display_name = "Jira"
    required_config_keys = ["url"]

    def __init__(self):
        self._http: _JiraHTTP | None = None
        self._config: dict[str, Any] = {}
        self._context_cache: dict[str, tuple[float, ProjectContext]] = {}
        self._ttl: float = 60.0

    def configure(self, config: dict[str, Any]) -> None:
        self._config = dict(config)
        url = (
            config.get("url")
            or config.get("instance_url")
            or config.get("site_url")
            or os.environ.get("JIRA_URL", "https://api.atlassian.com")
        )
        email = config.get("email", "") or os.environ.get("JIRA_EMAIL", "")
        api_token = config.get("api_token", "") or os.environ.get("JIRA_API_TOKEN", "")
        token = (
            config.get("token")
            or config.get("access_token")
            or os.environ.get("JIRA_TOKEN")
            or os.environ.get("JIRA_ACCESS_TOKEN")
        )
        cloud_id = config.get("cloud_id", "") or os.environ.get("JIRA_CLOUD_ID", "")

        self._http = _JiraHTTP(
            base_url=url,
            email=email,
            api_token=api_token,
            token=token,
            cloud_id=cloud_id,
        )
        self._ttl = float(config.get("context_cache_ttl", 60))
        logger.info("Jira configured at %s (cloud_id=%s)", url, cloud_id or "direct")

    def get_project_id(self, key: str) -> str:
        if not self._http:
            return key
        try:
            proj = self._http.get_project(key)
            return proj.get("key", key).upper()
        except Exception:
            return key.upper()

    def get_project_context(self, project_id: str) -> ProjectContext:
        now = time.time()
        project_key = str(project_id).upper()
        if project_key in self._context_cache:
            ts, ctx = self._context_cache[project_key]
            if now - ts < self._ttl:
                return ctx

        proj = self._http.get_project(project_key)
        project_name = proj.get("name", project_key)
        members = self.list_members(project_key)

        # Sprints (via Jira Agile API)
        active_sprint = self.get_active_sprint(project_key)
        sprint_name = active_sprint.get("name") if active_sprint else None
        sprint_end = (
            active_sprint.get("endDate") or active_sprint.get("estimated_finish")
            if active_sprint
            else None
        )

        # Issue counts by status category
        open_task_count = 0
        open_bug_count = 0
        open_story_count = 0
        try:
            task_resp = self._http.request(
                "POST",
                "/search",
                json={
                    "jql": f'project = "{project_key}" AND issuetype in (Task, "Sub-task") AND statusCategory != Done',
                    "maxResults": 0,
                },
            )
            open_task_count = task_resp.get("total", 0)
        except Exception as e:
            logger.debug("Failed to count open tasks in Jira: %s", e)

        try:
            bug_resp = self._http.request(
                "POST",
                "/search",
                json={
                    "jql": f'project = "{project_key}" AND issuetype in (Bug) AND statusCategory != Done',
                    "maxResults": 0,
                },
            )
            open_bug_count = bug_resp.get("total", 0)
        except Exception as e:
            logger.debug("Failed to count open bugs in Jira: %s", e)

        try:
            story_resp = self._http.request(
                "POST",
                "/search",
                json={
                    "jql": f'project = "{project_key}" AND issuetype in (Story) AND statusCategory != Done',
                    "maxResults": 0,
                },
            )
            open_story_count = story_resp.get("total", 0)
        except Exception as e:
            logger.debug("Failed to count open stories in Jira: %s", e)

        # Recent items
        recent: list[ProjectItem] = []
        try:
            recent_resp = self._http.request(
                "POST",
                "/search",
                json={
                    "jql": f'project = "{project_key}" ORDER BY created DESC',
                    "maxResults": 5,
                },
            )
            recent = [
                _to_item(issue, self._http.base_url)
                for issue in recent_resp.get("issues", [])
            ]
        except Exception as e:
            logger.warning("Failed to fetch recent Jira items: %s", e)

        ctx = ProjectContext(
            project_id=project_key,
            project_name=project_name,
            active_sprint=sprint_name,
            sprint_end_date=sprint_end,
            open_task_count=open_task_count,
            open_issue_count=open_bug_count,
            open_story_count=open_story_count,
            members=members,
            recent_items=recent,
        )
        self._context_cache[project_key] = (now, ctx)
        return ctx

    def create_item(
        self,
        project_id: str,
        item_type: str,
        subject: str,
        description: str = "",
        assigned_to: str | None = None,
        tags: list[str] | None = None,
        extra: dict[str, Any] | None = None,
    ) -> ProjectItem:
        project_key = str(project_id).upper()
        jira_type = _norm_type(item_type)

        fields: dict[str, Any] = {
            "project": {"key": project_key},
            "summary": subject,
            "description": _text_to_adf(description),
            "issuetype": {"name": jira_type},
        }

        if tags:
            fields["labels"] = [t.replace(" ", "_") for t in tags]

        if assigned_to:
            # Lookup account ID or use provided identifier
            members = self.list_members(project_key)
            matched = next(
                (
                    m
                    for m in members
                    if assigned_to.lower()
                    in (
                        m.get("username", "").lower(),
                        m.get("full_name", "").lower(),
                        str(m.get("id", "")).lower(),
                    )
                ),
                None,
            )
            if matched and matched.get("id"):
                fields["assignee"] = {"accountId": str(matched["id"])}
            elif len(assigned_to) > 20 and "-" in assigned_to:
                # Likely already an Atlassian accountId
                fields["assignee"] = {"accountId": assigned_to}
            else:
                fields["assignee"] = {"name": assigned_to}

        if extra:
            fields.update(extra)

        payload = {"fields": fields}
        raw = self._http.request("POST", "/issue", json=payload)
        issue_key = raw.get("key", raw.get("id", ""))

        # Fetch newly created issue with full fields
        full_issue = self._http.request("GET", f"/issue/{issue_key}")
        return _to_item(full_issue, self._http.base_url)

    def update_item(
        self,
        project_id: str,
        item_id: str,
        fields: dict[str, Any],
    ) -> ProjectItem:
        jira_fields: dict[str, Any] = {}
        if "subject" in fields or "summary" in fields:
            jira_fields["summary"] = fields.get("summary") or fields.get("subject")
        if "description" in fields:
            jira_fields["description"] = _text_to_adf(fields["description"])
        if "tags" in fields or "labels" in fields:
            jira_fields["labels"] = fields.get("labels") or fields.get("tags")
        if "assigned_to" in fields:
            assignee = fields["assigned_to"]
            if assignee:
                members = self.list_members(project_id)
                matched = next(
                    (
                        m
                        for m in members
                        if assignee.lower()
                        in (
                            m.get("username", "").lower(),
                            m.get("full_name", "").lower(),
                            str(m.get("id", "")).lower(),
                        )
                    ),
                    None,
                )
                if matched and matched.get("id"):
                    jira_fields["assignee"] = {"accountId": str(matched["id"])}
                else:
                    jira_fields["assignee"] = {"name": assignee}
            else:
                jira_fields["assignee"] = None

        payload = {"fields": jira_fields}
        self._http.request("PUT", f"/issue/{item_id}", json=payload)
        full_issue = self._http.request("GET", f"/issue/{item_id}")
        return _to_item(full_issue, self._http.base_url)

    def close_item(
        self,
        project_id: str,
        item_id: str,
        item_type: str | None = None,
    ) -> ProjectItem:
        """Transitions the issue to a closed/done status."""
        transitions_data = self._http.request("GET", f"/issue/{item_id}/transitions")
        transitions = transitions_data.get("transitions", [])

        target_trans = None
        for t in transitions:
            to_cat = t.get("to", {}).get("statusCategory", {}).get("key", "").lower()
            t_name = t.get("name", "").lower()
            if to_cat == "done" or t_name in ("done", "closed", "resolve", "resolved", "complete"):
                target_trans = t
                break

        if not target_trans and transitions:
            target_trans = transitions[-1]

        if not target_trans:
            raise ValueError(f"No available transitions to close issue {item_id}")

        self._http.request(
            "POST",
            f"/issue/{item_id}/transitions",
            json={"transition": {"id": target_trans["id"]}},
        )
        full_issue = self._http.request("GET", f"/issue/{item_id}")
        return _to_item(full_issue, self._http.base_url)

    def get_item(
        self,
        project_id: str,
        item_id: str,
        item_type: str | None = None,
    ) -> ProjectItem:
        raw = self._http.request("GET", f"/issue/{item_id}")
        return _to_item(raw, self._http.base_url)

    def list_items(
        self,
        project_id: str,
        item_type: str | None = None,
        status: str | None = "open",
        assigned_to: str | None = None,
        limit: int = 20,
    ) -> list[ProjectItem]:
        project_key = str(project_id).upper()
        clauses = [f'project = "{project_key}"']

        if item_type and item_type.lower() != "all":
            jira_type = _norm_type(item_type)
            clauses.append(f'issuetype in ("{jira_type}")')

        if status == "open":
            clauses.append("statusCategory != Done")
        elif status == "closed":
            clauses.append("statusCategory = Done")

        if assigned_to:
            clauses.append(f'(assignee = "{assigned_to}" OR assignee = currentUser())')

        jql = " AND ".join(clauses) + " ORDER BY updated DESC"
        resp = self._http.request(
            "POST",
            "/search",
            json={"jql": jql, "maxResults": limit},
        )
        issues = resp.get("issues", [])
        return [_to_item(issue, self._http.base_url) for issue in issues]

    def search_items(self, project_id: str, query: str, limit: int = 20) -> list[ProjectItem]:
        project_key = str(project_id).upper()
        cleaned_query = query.replace('"', '\\"')
        jql = f'project = "{project_key}" AND (summary ~ "{cleaned_query}" OR description ~ "{cleaned_query}") ORDER BY updated DESC'
        try:
            resp = self._http.request(
                "POST",
                "/search",
                json={"jql": jql, "maxResults": limit},
            )
            issues = resp.get("issues", [])
            return [_to_item(issue, self._http.base_url) for issue in issues]
        except Exception as e:
            logger.warning("Jira search failed for query '%s': %s", query, e)
            return []

    def list_members(self, project_id: str) -> list[dict[str, Any]]:
        project_key = str(project_id).upper()
        try:
            raw_users = self._http.request(
                "GET",
                f"/user/assignable/search?project={project_key}",
            ) or []
            members = []
            for u in raw_users:
                members.append({
                    "id": u.get("accountId") or u.get("name"),
                    "username": u.get("displayName") or u.get("name", "Unknown"),
                    "full_name": u.get("displayName", ""),
                    "email": u.get("emailAddress", ""),
                    "role": "Member",
                })
            return members
        except Exception as e:
            logger.warning("Could not fetch Jira assignable users for %s: %s", project_key, e)
            return []

    def get_active_sprint(self, project_id: str) -> dict[str, Any] | None:
        sprints = self.list_sprints(project_id)
        return next((s for s in sprints if s.get("state") == "active"), None)

    def list_sprints(self, project_id: str) -> list[dict[str, Any]]:
        project_key = str(project_id).upper()
        try:
            boards_resp = self._http.request(
                "GET",
                f"/rest/agile/1.0/board?projectKeyOrId={project_key}",
            )
            boards = boards_resp.get("values", [])
            if not boards:
                return []
            board_id = boards[0]["id"]
            sprints_resp = self._http.request(
                "GET",
                f"/rest/agile/1.0/board/{board_id}/sprint",
            )
            return sprints_resp.get("values", [])
        except Exception as e:
            logger.debug("Could not fetch sprints via Jira Agile API: %s", e)
            return []

    def create_epic(
        self,
        project_id: str,
        subject: str,
        description: str = "",
    ) -> ProjectItem:
        return self.create_item(
            project_id=project_id,
            item_type="Epic",
            subject=subject,
            description=description,
        )

    def link_to_epic(self, project_id: str, item_id: str, epic_id: str) -> ProjectItem:
        # In modern Jira Cloud, Epic link is represented by 'parent' field
        payload = {"fields": {"parent": {"key": epic_id}}}
        self._http.request("PUT", f"/issue/{item_id}", json=payload)
        return self.get_item(project_id, item_id)

    def get_due_items(self, project_id: str, days_ahead: int = 2) -> list[dict[str, Any]]:
        project_key = str(project_id).upper()
        target_date = (datetime.now(timezone.utc) + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
        jql = f'project = "{project_key}" AND statusCategory != Done AND duedate <= "{target_date}" ORDER BY duedate ASC'
        try:
            resp = self._http.request(
                "POST",
                "/search",
                json={"jql": jql, "maxResults": 30},
            )
            results = []
            for issue in resp.get("issues", []):
                fields = issue.get("fields", {})
                results.append({
                    "id": issue.get("key"),
                    "subject": fields.get("summary", ""),
                    "due_date": fields.get("duedate"),
                    "status": fields.get("status", {}).get("name"),
                    "assignee": fields.get("assignee", {}).get("displayName") if fields.get("assignee") else None,
                })
            return results
        except Exception as e:
            logger.warning("Could not fetch due items from Jira: %s", e)
            return []
