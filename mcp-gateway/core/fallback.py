from __future__ import annotations
import difflib
import logging
from typing import Any
from core.config import settings
from core.kafka_producer import KafkaTelemetry

logger = logging.getLogger("mcp_gateway.fallback")

class FallbackEngine:
    @staticmethod
    def handle_unsupported_tool(
        category: str,
        tool_name: str,
        available_tools: list[str],
        auth: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Fuzzy matches closest supported tools, publishes demand telemetry to Kafka,
        and produces a structured recovery payload for LLM auto-correction.
        """
        # 1. Fuzzy match closest supported tools
        cutoff = getattr(settings, "FUZZY_MATCH_CUTOFF", 0.5)
        closest_matches = difflib.get_close_matches(tool_name.lower(), [t.lower() for t in available_tools], n=3, cutoff=cutoff)


        # 2. Emit telemetry event to Kafka
        org_id = auth.get("org_id") or auth.get("workspace_id") or "default"
        user_id = auth.get("external_id") or auth.get("author_id") or "unknown"
        KafkaTelemetry.emit_missing_tool_event(
            requested_tool=tool_name,
            category=category,
            org_id=str(org_id),
            user_id=str(user_id),
        )

        logger.info(
            "Unsupported tool requested: '%s' in category '%s'. Suggestions: %s",
            tool_name, category, closest_matches
        )

        # 3. Return structured guidance for the LLM
        return {
            "status": "error",
            "error_code": "TOOL_NOT_SUPPORTED",
            "requested_tool": tool_name,
            "category": category,
            "message": f"Tool '{tool_name}' is not supported in category '{category}'.",
            "did_you_mean": closest_matches if closest_matches else None,
            "supported_tools": available_tools,
            "instructions_for_llm": (
                f"Tool '{tool_name}' could not be found. If one of the tools in 'did_you_mean' matches "
                f"your intent, invoke it immediately. Otherwise, kindly explain to the user that this feature is not supported."
            )
        }
