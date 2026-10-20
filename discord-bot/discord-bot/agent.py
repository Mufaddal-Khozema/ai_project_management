import os
import logging
from datetime import date, datetime

import dateparser
import requests
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.tools import tool
from langchain_core.messages import AIMessage, HumanMessage
from langchain_groq import ChatGroq

from schema import (
    CreateItemInput,
    FetchItemInput,
    ItemSummary,
    ListItemsInput,
    ListResult,
    ResolveDateInput,
    TaigaItem,
    UpdateItemInput,
)
from taiga_client import TaigaClient

load_dotenv()
logger = logging.getLogger("discord_bot.agent")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = "openai/gpt-oss-20b"

_clients = {}


def get_taiga_client(user_uuid, token):
    key = (user_uuid, token)
    if key not in _clients:
        _clients[key] = TaigaClient(os.getenv("TAIGA_URL"), token=token)
    return _clients[key]


SYSTEM_PROMPT = (
    "You are a Taiga project assistant. Use the available tools to fulfil the user's request. "
    "Today's date is {today}. When the user gives a relative date (e.g. '2 weeks from now', "
    "'next Friday'), call resolve_date with that exact phrase rather than computing it yourself. "
    "When creating an issue, pass any of assigned_to, priority, severity, type, status, or "
    "due_date the user mentioned - use the person's name or the word they used (e.g. 'high', "
    "'bug', 'critical', 'umer') and the tool will resolve it against the project's actual data. "
    "If a field can't be resolved, tell the user which one and continue with the rest. "
    "To find, filter or list items (e.g. 'high priority issues', 'tasks assigned to umer'), "
    "use list_items. Report priority, severity, type and status by name, never by ID. "
    "When showing multiple items, output them as a standard markdown table "
    "(| col | col | with a |---|---| separator row). Put any explanation outside the table. "
)

PRIORITY_RESOURCES = ("issues", "tasks", "userstories")

_model = None


def get_model():
    """Lazily build the ChatGroq client."""
    global _model
    if _model is None:
        _model = ChatGroq(model=GROQ_MODEL, groq_api_key=GROQ_API_KEY, temperature=0)
    return _model


# ---------------------------------------------------------------------------
# Lookup helpers
# ---------------------------------------------------------------------------
def _best_match(items, query, keys):
    """Case-insensitive exact match first, then substring match, over `keys` per item."""
    if not query:
        return None

    q = query.strip().lower()

    for item in items:
        for k in keys:
            value = item.get(k)
            if value and str(value).strip().lower() == q:
                return item

    for item in items:
        for k in keys:
            value = item.get(k)
            if value and q in str(value).strip().lower():
                return item

    return None


def _resolve_member_id(taiga, project_id, name):
    members = [m for m in taiga.get_memberships(project_id) if m.get("user")]
    match = _best_match(members, name, ["full_name_display", "full_name", "username"])
    return match["user"] if match else None


def _resolve_reference_id(taiga, project_id, name, getter):
    match = _best_match(getter(project_id), name, ["name"])
    return match["id"] if match else None


def _name_of(items, item_id):
    for it in items:
        if it.get("id") == item_id:
            return it.get("name")
    return None


def _http_error_text(e):
    return e.response.text if e.response is not None else str(e)


def _iso(value):
    """Tool args may arrive as date objects (from the schema); Taiga wants ISO strings."""
    return value.isoformat() if isinstance(value, date) else value


def _resolve_fields(
    taiga,
    project_id,
    resource,
    *,
    assigned_to=None,
    priority=None,
    severity=None,
    type=None,
    status=None,
    priority_resources=PRIORITY_RESOURCES,
):
    """Turn the user's words into Taiga IDs.

    Returns (fields, problems): `fields` is ready to merge into a payload or filter dict,
    `problems` is a list of human-readable reasons something couldn't be resolved.
    Shared by create_item, update_item and list_items.
    """
    fields, problems = {}, []

    def lookup(label, value, getter, key):
        rid = _resolve_reference_id(taiga, project_id, value, getter)
        if rid:
            fields[key] = rid
        else:
            problems.append(f"could not find a {label} matching '{value}'")

    if assigned_to:
        uid = _resolve_member_id(taiga, project_id, assigned_to)
        if uid:
            fields["assigned_to"] = uid
        else:
            problems.append(f"could not find a project member matching '{assigned_to}'")

    if priority:
        if resource in priority_resources:
            lookup("priority", priority, taiga.get_priorities, "priority")
        else:
            problems.append(f"priority does not apply to {resource}")

    if severity:
        if resource == "issues":
            lookup("severity", severity, taiga.get_severities, "severity")
        else:
            problems.append(f"severity only applies to issues, not {resource}")

    if type:
        if resource == "issues":
            lookup("issue type", type, taiga.get_issue_types, "type")
        else:
            problems.append(f"type does not apply to {resource}")

    if status:
        lookup("status", status, lambda pid: taiga.get_statuses(pid, resource), "status")

    return fields, problems


def _summarize(taiga, raw, resource, project_id, details=False) -> ItemSummary:
    """Validate a raw Taiga record and turn it into a compact, human-readable summary."""
    item = TaigaItem.model_validate(raw)
    out = ItemSummary(
        ref=item.ref,
        subject=item.subject or item.name,
        status=item.status_extra_info.name if item.status_extra_info else None,
        assigned_to=(
            item.assigned_to_extra_info.full_name_display
            if item.assigned_to_extra_info
            else None
        ),
        due_date=item.due_date,
    )

    if resource == "issues":
        out.priority = _name_of(taiga.get_priorities(project_id), item.priority)
        out.severity = _name_of(taiga.get_severities(project_id), item.severity)
        out.type = _name_of(taiga.get_issue_types(project_id), item.type)

    if details:
        out.description = item.description
        out.tags = item.tags
    return out


def _dump(model):
    return model.model_dump(mode="json", exclude_none=True)


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------
def make_tools(taiga, project_id):
    """Build the Taiga tools bound to a specific project id.

    Rebuilt per call because project_id comes from the bot config, not from the model.
    """

    @tool(args_schema=ResolveDateInput)
    def resolve_date(expression: str) -> str:
        """Convert a natural-language date expression (e.g. '2 weeks from now',
        'next Friday', 'tomorrow') into an ISO date string (YYYY-MM-DD).
        Always use this instead of computing relative dates yourself."""
        parsed = dateparser.parse(
            expression,
            settings={"PREFER_DATES_FROM": "future", "RELATIVE_BASE": datetime.now()},
        )
        if not parsed:
            return f"Could not parse a date from '{expression}'"
        return parsed.date().isoformat()

    @tool(args_schema=CreateItemInput)
    def create_item(
        resource: str,
        subject: str,
        description: str = "",
        assigned_to: str = None,
        priority: str = None,
        severity: str = None,
        type: str = None,
        status: str = None,
        due_date: date = None,
    ) -> dict:
        """Create a new issue, task, user story or epic in Taiga.
        Names (assignee, priority, severity, type, status) are resolved against the project."""
        payload = {"project": project_id, "subject": subject, "description": description}

        fields, warnings = _resolve_fields(
            taiga, project_id, resource,
            assigned_to=assigned_to, priority=priority, severity=severity,
            type=type, status=status,
        )
        payload.update(fields)

        if due_date:
            payload["due_date"] = _iso(due_date)

        try:
            result = taiga.create(resource, payload)
        except requests.exceptions.HTTPError as e:
            return {"error": _http_error_text(e)}

        out = {"created": _dump(_summarize(taiga, result, resource, project_id))}
        if warnings:
            out["warnings"] = warnings
        return out

    @tool(args_schema=FetchItemInput)
    def fetch_item(resource: str, ref: int) -> dict:
        """Fetch an existing issue, task, user story or epic by its Taiga reference number
        (the number shown in Taiga, e.g. 'Epic #14' -> ref=14)."""
        try:
            raw = taiga.get_by_ref(resource, project_id, ref)
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                return {"error": f"No {resource[:-1]} with ref {ref} found in this project."}
            return {"error": _http_error_text(e)}

        return _dump(_summarize(taiga, raw, resource, project_id, details=True))

    @tool(args_schema=UpdateItemInput)
    def update_item(
        resource: str,
        ref: int,
        subject: str = None,
        description: str = None,
        assigned_to: str = None,
        priority: str = None,
        severity: str = None,
        type: str = None,
        status: str = None,
        due_date: date = None,
        tags: list[str] = None,
    ) -> dict:
        """Update any attribute of an existing issue, task, user story or epic,
        identified by its Taiga reference number. Only pass fields that should change."""
        try:
            current = taiga.get_by_ref(resource, project_id, ref)
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                return {"error": f"No {resource[:-1]} with ref {ref} found in this project."}
            return {"error": _http_error_text(e)}

        payload = {"version": current["version"]}

        if subject is not None:
            payload["subject"] = subject
        if description is not None:
            payload["description"] = description

        fields, warnings = _resolve_fields(
            taiga, project_id, resource,
            assigned_to=assigned_to, priority=priority, severity=severity,
            type=type, status=status,
        )
        payload.update(fields)

        if due_date:
            payload["due_date"] = _iso(due_date)
        if tags is not None:
            payload["tags"] = tags

        try:
            result = taiga.update(resource, current["id"], payload)
        except requests.exceptions.HTTPError as e:
            return {"error": _http_error_text(e)}

        out = {"updated": _dump(_summarize(taiga, result, resource, project_id))}
        if warnings:
            out["warnings"] = warnings
        return out

    @tool(args_schema=ListItemsInput)
    def list_items(
        resource: str,
        status: str = None,
        priority: str = None,
        severity: str = None,
        type: str = None,
        assigned_to: str = None,
    ) -> dict:
        """List issues, tasks, user stories or epics in the project, optionally filtered.
        Use for requests like 'show high priority issues' or "what's assigned to umer".
        Pass filter values as the user's words. priority, severity and type only apply to issues."""
        fields, problems = _resolve_fields(
            taiga, project_id, resource,
            assigned_to=assigned_to, priority=priority, severity=severity,
            type=type, status=status,
            priority_resources=("issues",),
        )

        # Don't silently return an unfiltered list when a filter didn't resolve
        if problems:
            return {"error": "Could not resolve: " + "; ".join(problems)}

        try:
            items = taiga.list(resource, project=project_id, **fields) or []
        except requests.exceptions.HTTPError as e:
            return {"error": _http_error_text(e)}

        rows = [_summarize(taiga, i, resource, project_id) for i in items[:50]]
        return _dump(ListResult(count=len(items), shown=len(rows), items=rows))

    return [resolve_date, create_item, fetch_item, update_item, list_items]


# ---------------------------------------------------------------------------
# Agent runner
# ---------------------------------------------------------------------------
def _history_to_messages(history):
    """Convert DB rows (objects with .role/.content) into LangChain messages."""
    messages = []
    for row in history or []:
        if row.role == "user":
            messages.append(HumanMessage(content=row.content))
        else:
            messages.append(AIMessage(content=row.content))
    return messages


def run_agent(user_message, taiga, project_id, history=None, related=None):
    """Run one turn of the Taiga agent via Groq and return the reply text."""
    tools = make_tools(taiga, project_id)
    system_prompt = SYSTEM_PROMPT.format(today=datetime.now().date().isoformat())
    if related:
        lines = "\n".join(f"- {r.author_name}: {r.content}" for r in related)
        system_prompt += f"\n\nPossibly relevant earlier messages (context only):\n{lines}"

    agent = create_agent(get_model(), tools=tools, system_prompt=system_prompt)
    messages = _history_to_messages(history) + [HumanMessage(content=user_message)]
    try:
        result = agent.invoke({"messages": messages})
    except Exception:
        logger.exception("Agent invocation failed")
        raise

    for msg in reversed(result.get("messages", [])):
        if isinstance(msg, AIMessage) and msg.content:
            return str(msg.content)

    return "Sorry, I couldn't complete that request."