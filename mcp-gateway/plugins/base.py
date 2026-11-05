from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, Dict

class BasePlugin(ABC):
    @property
    @abstractmethod
    def category(self) -> str:
        """Category identifier, e.g. 'pm', 'meetings', 'discord'."""
        ...

    @abstractmethod
    def get_supported_tools(self) -> dict[str, dict[str, Any]]:
        """
        Returns a mapping of tool_name -> tool metadata.
        Example:
        {
            "taiga_create_task": {
                "description": "Create a task in Taiga PM",
                "parameters": {"project_id": "int", "subject": "str"}
            }
        }
        """
        ...

    @abstractmethod
    async def execute(
        self,
        tool_name: str,
        params: dict[str, Any],
        auth: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Executes the specified tool action.
        """
        ...
