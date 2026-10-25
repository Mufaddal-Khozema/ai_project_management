"""
platforms/pm/taiga_platform.py — Full Taiga REST API adapter.
"""
from __future__ import annotations
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any
import requests
from core.base import ProjectManagementPlatform, ProjectContext, ProjectItem
from core.registry import pm_platform

logger = logging.getLogger("agent_bridge.taiga")

_RESOURCE_MAP = {
    "task": "tasks", "tasks": "tasks",
    "story": "userstories", "userstory": "userstories", "userstories": "userstories",
    "epic": "epics", "epics": "epics",
    "issue": "issues", "issues": "issues",
}

def _norm(item_type: str) -> str:
    return _RESOURCE_MAP.get(item_type.lower().strip(), item_type.lower().strip())


class _TaigaHTTP:
    def __init__(self, base_url: str, username: str = "", password: str = "", token: str | None = None):
        self.base_url = (base_url or "https://api.taiga.io/api/v1").rstrip("/")
        self.username = username
        self.password = password
        self.token = token
        self._slug_cache: dict[str, str] = {}
        self._status_cache: dict[str, int] = {}

    def login(self) -> None:
        if not self.username or not self.password:
            if self.token:
                return
            raise RuntimeError(
                "Taiga authentication failed: neither credentials (username/password) nor access token provided."
            )
        r = requests.post(f"{self.base_url}/auth",
            json={"type": "normal", "username": self.username, "password": self.password},
            timeout=10)
        if r.status_code in (401, 403):
            raise RuntimeError(
                f"Taiga authentication failed (HTTP {r.status_code}). "
                "Verify the Taiga username/password configured for this organization."
            )
        r.raise_for_status()
        self.token = r.json()["auth_token"]
        logger.info("Taiga login OK")

    def _headers(self) -> dict:
        if not self.token:
            self.login()
        return {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}

    def request(self, method: str, path: str, **kwargs) -> Any:
        r = requests.request(method, f"{self.base_url}{path}",
            headers=self._headers(), timeout=300, **kwargs)
        if r.status_code == 401:
            self.token = None
            self.login()
            r = requests.request(method, f"{self.base_url}{path}",
                headers=self._headers(), timeout=300, **kwargs)
        r.raise_for_status()
        return r.json() if r.text.strip() else None

    def get_project_id(self, slug: str) -> str:
        if slug not in self._slug_cache:
            data = self.request("GET", "/projects/by_slug", params={"slug": slug})
            self._slug_cache[slug] = str(data["id"])
        return self._slug_cache[slug]

    def get_closed_status_id(self, resource: str, project_id: str) -> int:
        key = f"{resource}:{project_id}"
        if key not in self._status_cache:
            statuses = self.request("GET", f"/{resource}/statuses", params={"project": project_id})
            closed = next((s for s in statuses if s.get("is_closed")), None)
            if not closed:
                raise ValueError(f"No closed status for {resource} in project {project_id}")
            self._status_cache[key] = closed["id"]
        return self._status_cache[key]


def _to_item(raw: dict, resource: str, base_url: str) -> ProjectItem:
    ref = raw.get("ref", raw.get("id", ""))
    slug = raw.get("project_extra_info", {}).get("slug", "")
    resource_singular = resource.rstrip("s").replace("userstorie", "us")
    url = f"{base_url.replace('/api/v1','')}/project/{slug}/{resource_singular}/{ref}" if slug else None
    assignee = None
    if raw.get("assigned_to_extra_info"):
        assignee = raw["assigned_to_extra_info"].get("username")
    return ProjectItem(
        platform="taiga", item_id=str(raw.get("id", "")),
        item_type=resource, subject=raw.get("subject", ""),
        description=raw.get("description", "") or "",
        status=raw.get("status_extra_info", {}).get("name", str(raw.get("status", ""))),
        assignee=assignee, tags=raw.get("tags", []) or [],
        url=url, raw=raw,
    )


@pm_platform
class TaigaPlatform(ProjectManagementPlatform):
    platform_id = "taiga"
    display_name = "Taiga"
    required_config_keys = ["url", "username", "password"]

    def __init__(self):
        self._http: _TaigaHTTP | None = None
        self._config: dict[str, Any] = {}
        self._context_cache: dict[str, tuple[float, ProjectContext]] = {}

    def configure(self, config: dict[str, Any]) -> None:
        self._config = dict(config)
        token = config.get("token") or config.get("access_token")
        url = config.get("url") or config.get("instance_url") or "https://api.taiga.io/api/v1"
        username = config.get("username", "")
        password = config.get("password", "")
        self._http = _TaigaHTTP(url, username, password, token=token)
        self._ttl = config.get("context_cache_ttl", 60)
        logger.info("Taiga configured at %s", url)

    def get_project_id(self, key: str) -> str:
        return self._http.get_project_id(key)

    def get_project_context(self, project_id: str) -> ProjectContext:
        now = time.time()
        if project_id in self._context_cache:
            ts, ctx = self._context_cache[project_id]
            if now - ts < self._ttl:
                return ctx
        project = self._http.request("GET", f"/projects/{project_id}")
        members = self.list_members(project_id)
        sprints = self._http.request("GET", "/milestones", params={"project": project_id}) or []
        active = next((s for s in sprints if not s.get("closed")), None)
        stats = {}
        try:
            stats = self._http.request("GET", f"/projects/{project_id}/stats") or {}
        except Exception:
            pass
        recent_raw = self._http.request("GET", "/tasks", params={
            "project": project_id, "order_by": "-created_date"}) or []
        recent = [_to_item(r, "tasks", self._http.base_url) for r in recent_raw[:5]]
        ctx = ProjectContext(
            project_id=project_id, project_name=project.get("name", ""),
            active_sprint=active["name"] if active else None,
            sprint_end_date=active.get("estimated_finish") if active else None,
            open_task_count=stats.get("opened_tasks", 0),
            open_issue_count=stats.get("opened_issues", 0),
            open_story_count=stats.get("opened_userstories", 0),
            members=members, recent_items=recent,
        )
        self._context_cache[project_id] = (now, ctx)
        return ctx

    def create_item(self, project_id: str, item_type: str, subject: str,
                    description: str = "", assigned_to: str | None = None,
                    tags: list[str] | None = None) -> ProjectItem:
        resource = _norm(item_type)
        payload: dict[str, Any] = {
            "project": int(project_id), "subject": subject,
            "description": description, "tags": tags or [],
        }
        if assigned_to:
            members = self.list_members(project_id)
            m = next((x for x in members if x["username"] == assigned_to), None)
            if m:
                payload["assigned_to"] = m["id"]
        raw = self._http.request("POST", f"/{resource}", json=payload)
        return _to_item(raw, resource, self._http.base_url)

    def update_item(self, project_id: str, item_id: str,
                    fields: dict[str, Any]) -> ProjectItem:
        for resource in ("tasks", "userstories", "issues", "epics"):
            try:
                raw = self._http.request("PATCH", f"/{resource}/{item_id}", json=fields)
                return _to_item(raw, resource, self._http.base_url)
            except Exception:
                continue
        raise ValueError(f"Item {item_id} not found in any resource type")

    def close_item(self, project_id: str, item_id: str) -> ProjectItem:
        for resource in ("tasks", "userstories", "issues", "epics"):
            try:
                raw = self._http.request("GET", f"/{resource}/{item_id}")
                closed_status = self._http.get_closed_status_id(resource, project_id)
                version = raw.get("version", 1)
                updated = self._http.request("PATCH", f"/{resource}/{item_id}",
                    json={"status": closed_status, "version": version})
                return _to_item(updated, resource, self._http.base_url)
            except Exception:
                continue
        raise ValueError(f"Item {item_id} not found")

    def get_item(self, project_id: str, item_id: str) -> ProjectItem:
        for resource in ("tasks", "userstories", "issues", "epics"):
            try:
                raw = self._http.request("GET", f"/{resource}/{item_id}")
                return _to_item(raw, resource, self._http.base_url)
            except Exception:
                continue
        raise ValueError(f"Item {item_id} not found")

    def list_items(self, project_id: str, item_type: str | None = None,
                   status: str | None = None, assigned_to: str | None = None,
                   limit: int = 20) -> list[ProjectItem]:
        resources = [_norm(item_type)] if item_type and item_type != "all" \
            else ["tasks", "userstories", "issues"]
        results = []
        for resource in resources:
            params: dict[str, Any] = {"project": project_id}
            if status == "open":
                params["status__is_closed"] = "false"
            elif status == "closed":
                params["status__is_closed"] = "true"
            if assigned_to:
                params["assigned_to__username"] = assigned_to
            try:
                raw_list = self._http.request("GET", f"/{resource}", params=params) or []
                results.extend(_to_item(r, resource, self._http.base_url) for r in raw_list)
            except Exception as e:
                logger.warning("list_items failed for %s: %s", resource, e)
        return results[:limit]

    def search_items(self, project_id: str, query: str) -> list[ProjectItem]:
        try:
            data = self._http.request("GET", "/search",
                params={"project": project_id, "text": query}) or {}
        except Exception:
            return []
        results = []
        for resource in ("tasks", "userstories", "issues", "epics"):
            for raw in data.get(resource, []):
                results.append(_to_item(raw, resource, self._http.base_url))
        return results

    def list_members(self, project_id: str) -> list[dict]:
        try:
            raw = self._http.request("GET", "/memberships",
                params={"project": project_id}) or []
            return [{
                "id":        m.get("user"),
                "username":  m.get("user_extra_info", {}).get("username", ""),
                "full_name": m.get("full_name", ""),
                "role":      m.get("role_name", ""),
            } for m in raw]
        except Exception:
            return []

    def get_active_sprint(self, project_id: str) -> dict | None:
        try:
            sprints = self._http.request("GET", "/milestones",
                params={"project": project_id}) or []
            return next((s for s in sprints if not s.get("closed")), None)
        except Exception:
            return None

    def list_sprints(self, project_id: str) -> list[dict]:
        try:
            return self._http.request("GET", "/milestones",
                params={"project": project_id}) or []
        except Exception:
            return []

    def create_epic(self, project_id: str, subject: str,
                    description: str = "") -> ProjectItem:
        raw = self._http.request("POST", "/epics",
            json={"project": int(project_id), "subject": subject, "description": description})
        return _to_item(raw, "epics", self._http.base_url)

    def link_to_epic(self, project_id: str, item_id: str, epic_id: str) -> ProjectItem:
        raw = self._http.request("POST", f"/epics/{epic_id}/related_userstories",
            json={"user_story": int(item_id)})
        return _to_item(raw, "userstories", self._http.base_url)

    def get_due_items(self, project_id: str, days_ahead: int = 2) -> list[dict]:
        """
        Retrieve open tasks, user stories, and issues with due_date on or before today + days_ahead,
        including overdue items.
        """
        threshold = (datetime.now(timezone.utc) + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
        results = []
        for resource in ("tasks", "userstories", "issues"):
            try:
                raw_list = self._http.request(
                    "GET", f"/{resource}",
                    params={"project": project_id, "status__is_closed": "false"}
                ) or []
                for raw in raw_list:
                    due = raw.get("due_date")
                    if due and str(due) <= threshold:
                        ref = raw.get("ref", raw.get("id", ""))
                        slug = raw.get("project_extra_info", {}).get("slug", "")
                        resource_singular = resource.rstrip("s").replace("userstorie", "us")
                        url = f"{self._http.base_url.replace('/api/v1','')}/project/{slug}/{resource_singular}/{ref}" if slug else None
                        assignee = None
                        if raw.get("assigned_to_extra_info"):
                            assignee = raw["assigned_to_extra_info"].get("username")

                        results.append({
                            "id": str(raw.get("id", "")),
                            "ref": str(ref),
                            "type": resource,
                            "subject": raw.get("subject", ""),
                            "description": raw.get("description", "") or "",
                            "due_date": str(due),
                            "due_date_reason": raw.get("due_date_reason") or "",
                            "due_date_status": raw.get("due_date_status") or "",
                            "assigned_to": assignee,
                            "assigned_to_id": raw.get("assigned_to"),
                            "watchers": raw.get("watchers", []) or [],
                            "version": raw.get("version", 1),
                            "url": url,
                        })
            except Exception as e:
                logger.warning("get_due_items failed for %s: %s", resource, e)
        return results

    def extend_due_date(self, project_id: str, item_id: str, new_date: str, reason: str = "") -> dict:
        """
        Extend or change the due date of a task, user story, or issue with version-checked optimistic concurrency.
        Returns details of the updated item and watchers.
        """
        for resource in ("tasks", "userstories", "issues"):
            try:
                raw = self._http.request("GET", f"/{resource}/{item_id}")
                version = raw.get("version", 1)
                patch_payload = {
                    "due_date": new_date,
                    "version": version,
                }
                if reason:
                    patch_payload["due_date_reason"] = reason

                updated = self._http.request("PATCH", f"/{resource}/{item_id}", json=patch_payload)

                ref = updated.get("ref", updated.get("id", item_id))
                slug = updated.get("project_extra_info", {}).get("slug", "")
                resource_singular = resource.rstrip("s").replace("userstorie", "us")
                url = f"{self._http.base_url.replace('/api/v1','')}/project/{slug}/{resource_singular}/{ref}" if slug else None
                assignee = None
                if updated.get("assigned_to_extra_info"):
                    assignee = updated["assigned_to_extra_info"].get("username")

                return {
                    "item_id": str(updated.get("id", item_id)),
                    "ref": str(ref),
                    "type": resource,
                    "subject": updated.get("subject", ""),
                    "old_due_date": raw.get("due_date"),
                    "new_due_date": new_date,
                    "reason": reason,
                    "assignee": assignee,
                    "watchers": updated.get("watchers", []) or raw.get("watchers", []) or [],
                    "version": updated.get("version", version + 1),
                    "url": url,
                }
            except Exception:
                continue
        raise ValueError(f"Item #{item_id} not found in any resource type")

    def get_watchers_info(self, project_id: str, watcher_ids: list[int | str]) -> list[dict]:
        """
        Resolve watcher IDs into full user and role details via project memberships.
        """
        if not watcher_ids:
            return []
        members = self.list_members(project_id)
        member_by_id = {m["id"]: m for m in members if m.get("id") is not None}

        info = []
        for wid in watcher_ids:
            try:
                num_id = int(wid)
            except (ValueError, TypeError):
                num_id = wid
            if num_id in member_by_id:
                info.append(member_by_id[num_id])
            else:
                info.append({"id": num_id, "username": f"user_{num_id}", "full_name": "", "role": ""})
        return info
