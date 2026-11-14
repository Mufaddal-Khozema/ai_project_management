"""
platforms/pm/dynamic_platform.py — Dynamic Multi-Tenant PM Platform Adapter.
Dispatches requests to the appropriate PM platform (Jira, Taiga, Linear, etc.)
resolved dynamically per workspace/channel from the central Identity Resolver API.
"""
from __future__ import annotations

import logging
from typing import Any

from core.base import ProjectContext, ProjectItem, ProjectManagementPlatform
from core.registry import PlatformRegistry, pm_platform

logger = logging.getLogger("agent_bridge.dynamic_pm")


@pm_platform
class DynamicPMPlatform(ProjectManagementPlatform):
    platform_id = "dynamic"
    display_name = "Dynamic PM"
    required_config_keys = []

    def __init__(self, default_provider: str = "taiga"):
        self._default_provider = default_provider
        self._instances: dict[str, ProjectManagementPlatform] = {}
        self._active_provider: str = default_provider
        self._config: dict[str, Any] = {}

    @property
    def active_pm(self) -> ProjectManagementPlatform:
        if self._active_provider not in self._instances:
            self.bind_provider(self._active_provider)
        return self._instances[self._active_provider]

    @property
    def display_name(self) -> str:
        if self._active_provider in self._instances:
            return self._instances[self._active_provider].display_name
        return "Project Management"

    def bind_provider(
        self,
        provider_name: str,
        config: dict[str, Any] | None = None,
    ) -> ProjectManagementPlatform:
        clean_name = (provider_name or self._default_provider).strip().lower()
        if clean_name not in self._instances:
            try:
                PMClass = PlatformRegistry.get_pm(clean_name)
                instance = PMClass()
                self._instances[clean_name] = instance
            except Exception as e:
                logger.error("Could not instantiate PM platform '%s': %s", clean_name, e)
                if clean_name != self._default_provider:
                    return self.bind_provider(self._default_provider, config)
                raise

        instance = self._instances[clean_name]
        if config:
            instance.configure(config)
        self._active_provider = clean_name
        return instance

    def configure(self, config: dict[str, Any]) -> None:
        self._config = dict(config)
        if "default_provider" in config:
            self._default_provider = config["default_provider"].strip().lower()
            self._active_provider = self._default_provider
        prov = config.get("provider") or self._default_provider
        self.bind_provider(prov, config)

    def get_project_id(self, key: str) -> str:
        return self.active_pm.get_project_id(key)

    def get_project_context(self, project_id: str) -> ProjectContext:
        return self.active_pm.get_project_context(project_id)

    def create_item(
        self,
        project_id: str,
        item_type: str,
        subject: str,
        description: str = "",
        assigned_to: str | None = None,
        tags: list[str] | None = None,
    ) -> ProjectItem:
        return self.active_pm.create_item(
            project_id=project_id,
            item_type=item_type,
            subject=subject,
            description=description,
            assigned_to=assigned_to,
            tags=tags,
        )

    def update_item(
        self,
        project_id: str,
        item_id: str,
        fields: dict[str, Any],
    ) -> ProjectItem:
        return self.active_pm.update_item(project_id, item_id, fields)

    def close_item(self, project_id: str, item_id: str) -> ProjectItem:
        return self.active_pm.close_item(project_id, item_id)

    def get_item(self, project_id: str, item_id: str) -> ProjectItem:
        return self.active_pm.get_item(project_id, item_id)

    def list_items(
        self,
        project_id: str,
        item_type: str | None = None,
        status: str | None = None,
        assigned_to: str | None = None,
        limit: int = 20,
    ) -> list[ProjectItem]:
        return self.active_pm.list_items(
            project_id=project_id,
            item_type=item_type,
            status=status,
            assigned_to=assigned_to,
            limit=limit,
        )

    def search_items(self, project_id: str, query: str) -> list[ProjectItem]:
        return self.active_pm.search_items(project_id, query)

    def list_members(self, project_id: str) -> list[dict]:
        return self.active_pm.list_members(project_id)

    def get_active_sprint(self, project_id: str) -> dict | None:
        return self.active_pm.get_active_sprint(project_id)

    def list_sprints(self, project_id: str) -> list[dict]:
        return self.active_pm.list_sprints(project_id)

    def create_epic(
        self,
        project_id: str,
        subject: str,
        description: str = "",
    ) -> ProjectItem:
        return self.active_pm.create_epic(project_id, subject, description)

    def link_to_epic(
        self,
        project_id: str,
        item_id: str,
        epic_id: str,
    ) -> ProjectItem:
        return self.active_pm.link_to_epic(project_id, item_id, epic_id)

    def get_due_items(self, project_id: str, days_ahead: int = 2) -> list[dict]:
        return self.active_pm.get_due_items(project_id, days_ahead=days_ahead)

    def extend_due_date(
        self,
        project_id: str,
        item_id: str,
        new_date: str,
        reason: str = "",
    ) -> dict:
        return self.active_pm.extend_due_date(project_id, item_id, new_date, reason=reason)

    def get_watchers_info(self, project_id: str, watcher_ids: list[int | str]) -> list[dict]:
        return self.active_pm.get_watchers_info(project_id, watcher_ids)
