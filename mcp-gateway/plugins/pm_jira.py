from __future__ import annotations

import base64
import logging
import os
from typing import Any

import httpx

from core.kafka_producer import KafkaTelemetry
from plugins.base import BasePlugin

logger = logging.getLogger("mcp_gateway.plugins.jira")


def _text_to_adf(text: str) -> dict[str, Any]:
    if not text:
        return {"type": "doc", "version": 1, "content": []}
    paragraphs = [p for p in text.split("\n\n") if p.strip()] or [text]
    content = []
    for p in paragraphs:
        content.append({
            "type": "paragraph",
            "content": [{"type": "text", "text": p.strip()}],
        })
    return {"type": "doc", "version": 1, "content": content}


def _adf_to_text(doc: Any) -> str:
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


class JiraPlugin(BasePlugin):
    @property
    def category(self) -> str:
        return "jira"

    def get_supported_tools(self) -> dict[str, dict[str, Any]]:
        return {
            "jira_list_issues": {
                "description": "List issues in a Jira project, filtered by status, assignee, or item type.",
                "parameters": {
                    "project_key": "str (Jira project key, e.g. PROJ)",
                    "status": "str (Optional: open, closed, or specific status)",
                    "assigned_to": "str (Optional accountId or username)",
                    "issue_type": "str (Optional: Task, Story, Bug, Epic)",
                    "limit": "int (Optional max items, default 20)",
                },
            },
            "jira_get_issue": {
                "description": "Retrieve full details of a specific Jira issue by key.",
                "parameters": {
                    "issue_key": "str (Jira issue key, e.g. PROJ-101)",
                },
            },
            "jira_create_issue": {
                "description": "Create a new issue, task, story, or bug in Jira.",
                "parameters": {
                    "project_key": "str (Jira project key)",
                    "summary": "str (Title/summary of the issue)",
                    "description": "str (Optional task details)",
                    "issue_type": "str (Optional: Task, Story, Bug, Epic. Defaults to Task)",
                    "assigned_to": "str (Optional Atlassian accountId)",
                    "priority": "str (Optional: Highest, High, Medium, Low, Lowest)",
                    "labels": "list[str] (Optional labels)",
                },
            },
            "jira_update_issue": {
                "description": "Update an existing issue's summary, description, priority, or assignee in Jira.",
                "parameters": {
                    "issue_key": "str (Jira issue key, e.g. PROJ-101)",
                    "summary": "str (Optional new title)",
                    "description": "str (Optional new details)",
                    "assigned_to": "str (Optional new assignee accountId)",
                    "priority": "str (Optional new priority)",
                    "labels": "list[str] (Optional new labels)",
                },
            },
            "jira_transition_issue": {
                "description": "Move a Jira issue to a different workflow status (e.g. 'Done', 'In Progress', 'In Review').",
                "parameters": {
                    "issue_key": "str (Jira issue key, e.g. PROJ-101)",
                    "status": "str (Target status name, e.g. 'Done', 'In Progress')",
                },
            },
            "jira_delete_issue": {
                "description": "Permanently delete an issue in Jira (Destructive - Admin only).",
                "parameters": {
                    "issue_key": "str (Jira issue key, e.g. PROJ-101)",
                },
            },
            "jira_get_sprints": {
                "description": "Retrieve active or planned sprints for a Jira project board.",
                "parameters": {
                    "project_key": "str (Jira project key)",
                    "state": "str (Optional: active, future, closed. Default: active)",
                },
            },
            "jira_search_issues": {
                "description": "Full-text search for Jira issues by keyword across summary and description.",
                "parameters": {
                    "project_key": "str (Jira project key)",
                    "query": "str (Search keyword)",
                    "limit": "int (Optional max items, default 20)",
                },
            },
        }

    async def _get_auth_headers(self, auth: dict[str, Any]) -> tuple[str, dict[str, str]]:
        """Resolves Jira base URL and authentication headers from auth context or env."""
        base_url = (
            auth.get("jira_url")
            or auth.get("url")
            or os.environ.get("JIRA_URL")
            or "https://api.atlassian.com"
        ).rstrip("/")

        cloud_id = auth.get("jira_cloud_id") or auth.get("cloud_id") or os.environ.get("JIRA_CLOUD_ID")
        if cloud_id and "api.atlassian.com" in base_url:
            base_url = f"https://api.atlassian.com/ex/jira/{cloud_id}"

        # Resolve token / creds
        token = (
            auth.get("decrypted_pm_token")
            or auth.get("jira_token")
            or auth.get("access_token")
            or os.environ.get("JIRA_TOKEN")
        )
        if isinstance(token, dict):
            # Might be decrypted OAuth JSON blob
            if token.get("cloud_id") and not cloud_id:
                base_url = f"https://api.atlassian.com/ex/jira/{token['cloud_id']}"
            token = token.get("access_token") or token.get("token")

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        if token:
            headers["Authorization"] = f"Bearer {token}"
            return base_url, headers

        email = auth.get("jira_email") or os.environ.get("JIRA_EMAIL")
        api_token = auth.get("jira_api_token") or os.environ.get("JIRA_API_TOKEN")
        if email and api_token:
            auth_str = f"{email}:{api_token}"
            encoded = base64.b64encode(auth_str.encode("utf-8")).decode("utf-8")
            headers["Authorization"] = f"Basic {encoded}"
            return base_url, headers

        raise PermissionError("No valid Jira authentication credentials available (Bearer token or Email/API Token).")

    async def execute(
        self,
        tool_name: str,
        params: dict[str, Any],
        auth: dict[str, Any],
    ) -> dict[str, Any]:
        base_url, headers = await self._get_auth_headers(auth)
        api_prefix = f"{base_url}/rest/api/3"

        async with httpx.AsyncClient(timeout=25.0) as client:
            if tool_name == "jira_list_issues":
                project_key = params.get("project_key", "").upper()
                clauses = [f'project = "{project_key}"']
                status = params.get("status")
                if status == "open":
                    clauses.append("statusCategory != Done")
                elif status == "closed":
                    clauses.append("statusCategory = Done")
                elif status:
                    clauses.append(f'status = "{status}"')

                if params.get("issue_type"):
                    clauses.append(f'issuetype in ("{params["issue_type"]}")')
                if params.get("assigned_to"):
                    clauses.append(f'assignee = "{params["assigned_to"]}"')

                jql = " AND ".join(clauses) + " ORDER BY updated DESC"
                limit = int(params.get("limit", 20))
                resp = await client.post(
                    f"{api_prefix}/search",
                    headers=headers,
                    json={"jql": jql, "maxResults": limit},
                )
                resp.raise_for_status()
                data = resp.json()
                issues = data.get("issues", [])
                return {
                    "total": data.get("total", len(issues)),
                    "issues": [
                        {
                            "id": i.get("id"),
                            "key": i.get("key"),
                            "summary": i.get("fields", {}).get("summary"),
                            "status": i.get("fields", {}).get("status", {}).get("name"),
                            "issue_type": i.get("fields", {}).get("issuetype", {}).get("name"),
                            "assignee": i.get("fields", {}).get("assignee", {}).get("displayName") if i.get("fields", {}).get("assignee") else None,
                            "url": f"{base_url.rstrip('/')}/browse/{i.get('key')}" if "api.atlassian.com" not in base_url else None,
                        }
                        for i in issues
                    ],
                }

            elif tool_name == "jira_get_issue":
                issue_key = params.get("issue_key", "").upper()
                resp = await client.get(f"{api_prefix}/issue/{issue_key}", headers=headers)
                resp.raise_for_status()
                data = resp.json()
                fields = data.get("fields", {})
                return {
                    "id": data.get("id"),
                    "key": data.get("key"),
                    "summary": fields.get("summary"),
                    "description": _adf_to_text(fields.get("description", "")),
                    "status": fields.get("status", {}).get("name"),
                    "issue_type": fields.get("issuetype", {}).get("name"),
                    "assignee": fields.get("assignee", {}).get("displayName") if fields.get("assignee") else None,
                    "labels": fields.get("labels", []),
                    "created": fields.get("created"),
                    "updated": fields.get("updated"),
                }

            elif tool_name == "jira_create_issue":
                project_key = params.get("project_key", "").upper()
                summary = params.get("summary", "")
                description = params.get("description", "")
                issue_type = params.get("issue_type", "Task")

                fields_payload: dict[str, Any] = {
                    "project": {"key": project_key},
                    "summary": summary,
                    "description": _text_to_adf(description),
                    "issuetype": {"name": issue_type},
                }

                if params.get("assigned_to"):
                    fields_payload["assignee"] = {"accountId": params["assigned_to"]}
                if params.get("priority"):
                    fields_payload["priority"] = {"name": params["priority"]}
                if params.get("labels"):
                    fields_payload["labels"] = params["labels"]

                resp = await client.post(
                    f"{api_prefix}/issue",
                    headers=headers,
                    json={"fields": fields_payload},
                )
                resp.raise_for_status()
                data = resp.json()
                created_key = data.get("key", data.get("id"))

                KafkaTelemetry.emit_task_event("jira_task_created", {
                    "task_id": created_key,
                    "subject": summary,
                    "project_key": project_key,
                    "created_by": auth.get("external_id", "unknown"),
                })

                return {
                    "success": True,
                    "id": data.get("id"),
                    "key": created_key,
                    "summary": summary,
                    "message": f"Jira issue {created_key} created successfully.",
                }

            elif tool_name == "jira_update_issue":
                issue_key = params.get("issue_key", "").upper()
                fields_payload: dict[str, Any] = {}
                if "summary" in params:
                    fields_payload["summary"] = params["summary"]
                if "description" in params:
                    fields_payload["description"] = _text_to_adf(params["description"])
                if "priority" in params:
                    fields_payload["priority"] = {"name": params["priority"]}
                if "assigned_to" in params:
                    fields_payload["assignee"] = (
                        {"accountId": params["assigned_to"]} if params["assigned_to"] else None
                    )
                if "labels" in params:
                    fields_payload["labels"] = params["labels"]

                resp = await client.put(
                    f"{api_prefix}/issue/{issue_key}",
                    headers=headers,
                    json={"fields": fields_payload},
                )
                resp.raise_for_status()

                KafkaTelemetry.emit_task_event("jira_task_updated", {
                    "task_id": issue_key,
                    "updated_by": auth.get("external_id", "unknown"),
                })

                return {
                    "success": True,
                    "key": issue_key,
                    "message": f"Jira issue {issue_key} updated.",
                }

            elif tool_name == "jira_transition_issue":
                issue_key = params.get("issue_key", "").upper()
                target_status = params.get("status", "").lower()

                # 1. Fetch available transitions
                trans_resp = await client.get(
                    f"{api_prefix}/issue/{issue_key}/transitions",
                    headers=headers,
                )
                trans_resp.raise_for_status()
                transitions = trans_resp.json().get("transitions", [])

                matched = next(
                    (
                        t
                        for t in transitions
                        if t.get("name", "").lower() == target_status
                        or t.get("to", {}).get("name", "").lower() == target_status
                    ),
                    None,
                )

                if not matched:
                    available = [t.get("name") for t in transitions]
                    raise ValueError(
                        f"Cannot transition to '{target_status}'. Available transitions: {available}"
                    )

                # 2. Execute transition
                post_resp = await client.post(
                    f"{api_prefix}/issue/{issue_key}/transitions",
                    headers=headers,
                    json={"transition": {"id": matched["id"]}},
                )
                post_resp.raise_for_status()

                KafkaTelemetry.emit_task_event("jira_task_transitioned", {
                    "task_id": issue_key,
                    "new_status": matched.get("name"),
                    "updated_by": auth.get("external_id", "unknown"),
                })

                return {
                    "success": True,
                    "key": issue_key,
                    "status": matched.get("name"),
                    "message": f"Jira issue {issue_key} transitioned to {matched.get('name')}.",
                }

            elif tool_name == "jira_delete_issue":
                issue_key = params.get("issue_key", "").upper()
                resp = await client.delete(f"{api_prefix}/issue/{issue_key}", headers=headers)
                resp.raise_for_status()

                KafkaTelemetry.emit_task_event("jira_task_deleted", {
                    "task_id": issue_key,
                    "deleted_by": auth.get("external_id", "unknown"),
                })

                return {
                    "success": True,
                    "key": issue_key,
                    "message": f"Jira issue {issue_key} permanently deleted.",
                }

            elif tool_name == "jira_get_sprints":
                project_key = params.get("project_key", "").upper()
                boards_resp = await client.get(
                    f"{base_url}/rest/agile/1.0/board?projectKeyOrId={project_key}",
                    headers=headers,
                )
                boards_resp.raise_for_status()
                boards = boards_resp.json().get("values", [])
                if not boards:
                    return {"sprints": []}

                board_id = boards[0]["id"]
                state = params.get("state", "active")
                sprints_resp = await client.get(
                    f"{base_url}/rest/agile/1.0/board/{board_id}/sprint?state={state}",
                    headers=headers,
                )
                sprints_resp.raise_for_status()
                return {"sprints": sprints_resp.json().get("values", [])}

            elif tool_name == "jira_search_issues":
                project_key = params.get("project_key", "").upper()
                query = params.get("query", "").replace('"', '\\"')
                limit = int(params.get("limit", 20))
                jql = f'project = "{project_key}" AND (summary ~ "{query}" OR description ~ "{query}") ORDER BY updated DESC'

                resp = await client.post(
                    f"{api_prefix}/search",
                    headers=headers,
                    json={"jql": jql, "maxResults": limit},
                )
                resp.raise_for_status()
                data = resp.json()
                return {
                    "total": data.get("total", 0),
                    "issues": [
                        {
                            "key": i.get("key"),
                            "summary": i.get("fields", {}).get("summary"),
                            "status": i.get("fields", {}).get("status", {}).get("name"),
                        }
                        for i in data.get("issues", [])
                    ],
                }

            else:
                raise NotImplementedError(f"Tool '{tool_name}' not implemented in JiraPlugin")
