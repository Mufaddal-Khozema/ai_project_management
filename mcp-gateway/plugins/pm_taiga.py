from __future__ import annotations
import logging
import os
from typing import Any
import httpx
from plugins.base import BasePlugin
from core.kafka_producer import KafkaTelemetry

logger = logging.getLogger("mcp_gateway.plugins.taiga")

class TaigaPlugin(BasePlugin):
    @property
    def category(self) -> str:
        return "pm"

    def get_supported_tools(self) -> dict[str, dict[str, Any]]:
        return {
            "taiga_list_tasks": {
                "description": "List tasks in a Taiga project, optionally filtered by milestone (sprint) or status.",
                "parameters": {
                    "project_id": "int (Taiga numeric project ID)",
                    "milestone_id": "int (Optional milestone/sprint ID)",
                    "status_id": "int (Optional status ID)"
                }
            },
            "taiga_create_task": {
                "description": "Create a new task in a Taiga project.",
                "parameters": {
                    "project_id": "int (Taiga numeric project ID)",
                    "subject": "str (Title of the task)",
                    "description": "str (Optional task details)",
                    "assigned_to": "int (Optional Taiga user ID)",
                    "user_story": "int (Optional user story ID)"
                }
            },
            "taiga_update_task": {
                "description": "Update an existing task in Taiga (change status, subject, or assigned user).",
                "parameters": {
                    "task_id": "int (Taiga task ID)",
                    "version": "int (Current version of task for optimistic locking)",
                    "subject": "str (Optional new title)",
                    "status_id": "int (Optional new status ID)",
                    "assigned_to": "int (Optional assigned user ID)"
                }
            },
            "taiga_delete_task": {
                "description": "Delete a task in Taiga (Destructive - Admin only).",
                "parameters": {
                    "task_id": "int (Taiga task ID)"
                }
            },
            "taiga_get_milestones": {
                "description": "Retrieve all sprints/milestones for a project.",
                "parameters": {
                    "project_id": "int (Taiga numeric project ID)"
                }
            },
            "taiga_get_user_stories": {
                "description": "List user stories in a Taiga project.",
                "parameters": {
                    "project_id": "int (Taiga numeric project ID)",
                    "milestone_id": "int (Optional milestone ID)"
                }
            }
        }

    async def _get_auth_headers(self, auth: dict[str, Any]) -> tuple[str, dict[str, str]]:
        """Resolves base URL and Bearer token from auth context or env."""
        base_url = (
            auth.get("taiga_url")
            or os.environ.get("TAIGA_URL")
            or "https://api.taiga.io/api/v1"
        ).rstrip("/")

        token = auth.get("decrypted_pm_token") or auth.get("taiga_token") or os.environ.get("TAIGA_TOKEN")
        if not token:
            user = auth.get("taiga_user") or os.environ.get("TAIGA_USER")
            password = auth.get("taiga_pass") or os.environ.get("TAIGA_PASS")
            if user and password:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(
                        f"{base_url}/auth",
                        json={"type": "normal", "username": user, "password": password}
                    )
                    resp.raise_for_status()
                    token = resp.json().get("auth_token")

        if not token:
            raise PermissionError("No valid Taiga authentication token or credentials available.")

        return base_url, {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    async def execute(
        self,
        tool_name: str,
        params: dict[str, Any],
        auth: dict[str, Any],
    ) -> dict[str, Any]:
        base_url, headers = await self._get_auth_headers(auth)

        async with httpx.AsyncClient(timeout=15.0) as client:
            if tool_name == "taiga_list_tasks":
                project_id = params.get("project_id")
                qp: dict[str, Any] = {"project": project_id} if project_id else {}
                if "milestone_id" in params and params["milestone_id"]:
                    qp["milestone"] = params["milestone_id"]
                if "status_id" in params and params["status_id"]:
                    qp["status"] = params["status_id"]
                resp = await client.get(f"{base_url}/tasks", headers=headers, params=qp)
                resp.raise_for_status()
                tasks = resp.json()
                return {
                    "total": len(tasks),
                    "tasks": [
                        {
                            "id": t.get("id"),
                            "ref": t.get("ref"),
                            "subject": t.get("subject"),
                            "status": t.get("status_extra_info", {}).get("name") if t.get("status_extra_info") else t.get("status"),
                            "assigned_to": t.get("assigned_to_extra_info", {}).get("full_name_display") if t.get("assigned_to_extra_info") else None,
                            "milestone_slug": t.get("milestone_slug"),
                        }
                        for t in tasks
                    ]
                }

            elif tool_name == "taiga_create_task":
                payload = {
                    "project": params.get("project_id"),
                    "subject": params.get("subject"),
                    "description": params.get("description", ""),
                }
                if params.get("assigned_to"):
                    payload["assigned_to"] = params["assigned_to"]
                if params.get("user_story"):
                    payload["user_story"] = params["user_story"]

                resp = await client.post(f"{base_url}/tasks", headers=headers, json=payload)
                resp.raise_for_status()
                data = resp.json()
                # Emit task event to Kafka
                KafkaTelemetry.emit_task_event("task_created", {
                    "task_id": data.get("id"),
                    "subject": data.get("subject"),
                    "project_id": data.get("project"),
                    "created_by": auth.get("external_id", "unknown"),
                })
                return {
                    "success": True,
                    "task_id": data.get("id"),
                    "ref": data.get("ref"),
                    "subject": data.get("subject"),
                    "message": f"Task #{data.get('id')} created successfully."
                }

            elif tool_name == "taiga_update_task":
                task_id = params.get("task_id")
                # Need current version if not provided
                version = params.get("version")
                if version is None:
                    get_resp = await client.get(f"{base_url}/tasks/{task_id}", headers=headers)
                    get_resp.raise_for_status()
                    version = get_resp.json().get("version", 1)

                patch_payload: dict[str, Any] = {"version": version}
                if "subject" in params:
                    patch_payload["subject"] = params["subject"]
                if "status_id" in params:
                    patch_payload["status"] = params["status_id"]
                if "assigned_to" in params:
                    patch_payload["assigned_to"] = params["assigned_to"]

                resp = await client.patch(f"{base_url}/tasks/{task_id}", headers=headers, json=patch_payload)
                resp.raise_for_status()
                data = resp.json()
                KafkaTelemetry.emit_task_event("task_updated", {
                    "task_id": task_id,
                    "subject": data.get("subject"),
                    "updated_by": auth.get("external_id", "unknown"),
                })
                return {
                    "success": True,
                    "task_id": task_id,
                    "subject": data.get("subject"),
                    "message": f"Task #{task_id} updated."
                }

            elif tool_name == "taiga_delete_task":
                task_id = params.get("task_id")
                resp = await client.delete(f"{base_url}/tasks/{task_id}", headers=headers)
                resp.raise_for_status()
                KafkaTelemetry.emit_task_event("task_deleted", {
                    "task_id": task_id,
                    "deleted_by": auth.get("external_id", "unknown"),
                })
                return {"success": True, "message": f"Task #{task_id} permanently deleted."}

            elif tool_name == "taiga_get_milestones":
                project_id = params.get("project_id")
                resp = await client.get(f"{base_url}/milestones", headers=headers, params={"project": project_id})
                resp.raise_for_status()
                milestones = resp.json()
                return {
                    "milestones": [
                        {
                            "id": m.get("id"),
                            "name": m.get("name"),
                            "slug": m.get("slug"),
                            "closed": m.get("closed"),
                            "estimated_start": m.get("estimated_start"),
                            "estimated_finish": m.get("estimated_finish"),
                        }
                        for m in milestones
                    ]
                }

            elif tool_name == "taiga_get_user_stories":
                project_id = params.get("project_id")
                qp = {"project": project_id}
                if params.get("milestone_id"):
                    qp["milestone"] = params["milestone_id"]
                resp = await client.get(f"{base_url}/userstories", headers=headers, params=qp)
                resp.raise_for_status()
                stories = resp.json()
                return {
                    "total": len(stories),
                    "stories": [
                        {
                            "id": s.get("id"),
                            "ref": s.get("ref"),
                            "subject": s.get("subject"),
                            "status": s.get("status_extra_info", {}).get("name") if s.get("status_extra_info") else s.get("status"),
                            "is_closed": s.get("is_closed", False),
                        }
                        for s in stories
                    ]
                }

            else:
                raise NotImplementedError(f"Tool '{tool_name}' not implemented in TaigaPlugin")
