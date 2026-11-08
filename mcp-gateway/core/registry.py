from __future__ import annotations
import logging
from typing import Any, Dict
from plugins.base import BasePlugin

logger = logging.getLogger("mcp_gateway.registry")

class ToolRegistry:
    _plugins: dict[str, BasePlugin] = {}

    @classmethod
    def register_plugin(cls, category: str, plugin: BasePlugin) -> None:
        cls._plugins[category.lower()] = plugin
        logger.info("Registered plugin category '%s' with %d tools", category, len(plugin.get_supported_tools()))

    @classmethod
    def get_plugin(cls, category: str, tool_name: str | None = None) -> BasePlugin | None:
        if tool_name:
            t = tool_name.lower().strip()
            direct = cls._plugins.get(category.lower())
            if direct and t in direct.get_supported_tools():
                return direct
            for plugin in cls._plugins.values():
                if t in plugin.get_supported_tools():
                    return plugin
        return cls._plugins.get(category.lower())

    @classmethod
    def get_categories(cls) -> list[str]:
        return list(cls._plugins.keys())

    @classmethod
    def get_tools_for_category(cls, category: str) -> list[str]:
        cat = category.lower().strip()
        if cat == "pm":
            tools = []
            for p_cat in ("pm", "taiga", "jira"):
                p = cls._plugins.get(p_cat)
                if p:
                    tools.extend(p.get_supported_tools().keys())
            return list(dict.fromkeys(tools))
        plugin = cls.get_plugin(cat)
        if not plugin:
            return []
        return list(plugin.get_supported_tools().keys())

    @classmethod
    def count(cls) -> int:
        return sum(len(p.get_supported_tools()) for p in cls._plugins.values())

    @classmethod
    def search(cls, query: str = "", category: str | None = None) -> dict[str, Any]:
        """
        Search tools across categories. If query is provided, filters by name/description.
        """
        results: dict[str, dict[str, Any]] = {}
        target_cats = [category.lower()] if category and category.lower() in cls._plugins else cls._plugins.keys()

        q = query.lower().strip()
        for cat in target_cats:
            plugin = cls._plugins[cat]
            tools = plugin.get_supported_tools()
            matched = {}
            for name, meta in tools.items():
                if not q or q in name.lower() or q in meta.get("description", "").lower():
                    matched[name] = meta
            if matched:
                results[cat] = matched
        return results

    @classmethod
    async def execute(
        cls,
        category: str,
        tool_name: str,
        params: dict[str, Any],
        auth: dict[str, Any],
    ) -> dict[str, Any]:
        plugin = cls.get_plugin(category, tool_name)
        if not plugin:
            raise KeyError(f"Category '{category}' or tool '{tool_name}' not found")
        return await plugin.execute(tool_name, params, auth)
