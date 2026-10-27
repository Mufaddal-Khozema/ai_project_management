from __future__ import annotations
import logging
from typing import Any
from core.config import settings

logger = logging.getLogger("mcp_gateway.guardrails")

class GuardrailViolation(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message

class GuardrailEngine:
    DESTRUCTIVE_KEYWORDS = {"delete", "remove", "drop", "terminate", "archive", "purge"}
    WRITE_KEYWORDS = {"create", "add", "update", "patch", "start", "stop", "assign"}

    @classmethod
    def verify_request(cls, tool_name: str, params: dict[str, Any], auth: dict[str, Any]) -> None:
        """
        Deterministic multi-tier verification before tool execution.
        Raises GuardrailViolation on failure.
        """
        user_role = str(auth.get("user_role", "read")).lower()
        entitlements = auth.get("entitlements", {})

        # 1. Subscription & Entitlement Guard (if strict enforcement enabled)
        if entitlements and not entitlements.get("has_subscription", False):
            # In strict production mode, unentitled workspaces cannot mutate state
            if any(kw in tool_name.lower() for kw in cls.WRITE_KEYWORDS | cls.DESTRUCTIVE_KEYWORDS):
                raise GuardrailViolation(
                    "GUARDRAIL_ENTITLEMENT_REQUIRED",
                    "An active workspace subscription is required to perform modifications or create items."
                )

        # 2. Destructive Actions RBAC Guard
        is_destructive = any(kw in tool_name.lower() for kw in cls.DESTRUCTIVE_KEYWORDS)
        if is_destructive and user_role != "admin":
            raise GuardrailViolation(
                "GUARDRAIL_RBAC_ADMIN_REQUIRED",
                f"Role '{user_role}' is not authorized to execute destructive action '{tool_name}'. Admin role required."
            )

        # 3. Write Actions RBAC Guard
        is_write = any(kw in tool_name.lower() for kw in cls.WRITE_KEYWORDS)
        if is_write and user_role not in {"admin", "write"}:
            raise GuardrailViolation(
                "GUARDRAIL_RBAC_WRITE_REQUIRED",
                f"Role '{user_role}' only has read permissions. Cannot execute action '{tool_name}'."
            )

    @classmethod
    def sanitize_output(cls, data: Any) -> Any:
        """
        Recursively scrubs sensitive authentication credentials and secret tokens.
        """
        scrub_targets = {k.strip().lower() for k in settings.DLP_SCRUB_KEYS.split(",") if k.strip()}

        if isinstance(data, dict):
            clean = {}
            for k, v in data.items():
                if any(target in k.lower() for target in scrub_targets):
                    clean[k] = "[REDACTED]"
                else:
                    clean[k] = cls.sanitize_output(v)
            return clean
        elif isinstance(data, list):
            return [cls.sanitize_output(item) for item in data]
        return data
