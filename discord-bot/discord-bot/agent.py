import os
import logging
import requests
from dotenv import load_dotenv
from datetime import datetime, timezone
import dateparser
from langchain_groq import ChatGroq
from langchain.agents import create_agent
from langchain.tools import tool
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from taiga_client import TaigaClient

load_dotenv()
logger = logging.getLogger("discord_bot.agent")

GROQ_API_KEY=os.getenv("GROQ_API_KEY")
GROQ_MODEL= "openai/gpt-oss-20b"

# model = ChatGroq(model = "openai/gpt-oss-20b", groq_api_key = GROQ_API_KEY)

taiga= TaigaClient(os.getenv("TAIGA_URL"),os.getenv("TAIGA_USER"),os.getenv("TAIGA_PASS"))

SYSTEM_PROMPT = (
    "You are a Taiga project assistant. Use the available tools to fulfil the user's request. "
    "Today's date is {today}. When the user gives a relative date (e.g. '2 weeks from now', "
    "'next Friday'), call resolve_date with that exact phrase rather than computing it yourself. "
    "When creating an issue, pass any of assigned_to, priority, severity, type, status, or "
    "due_date the user mentioned - use the person's name or the word they used (e.g. 'high', "
    "'bug', 'critical', 'umer') and the tool will resolve it against the project's actual data. "
    "If a field can't be resolved, tell the user which one and continue with the rest."
)

def _best_match(items,query, keys):
    """Case-insensitive exact match first, then substring match, over 'keys' per item."""
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

def _resolve_member_id(project_id, name):
    memebers= taiga.get_memberships(project_id)
    match =_best_match(memebers,name,["full_name_display", "full_name", "username"])
    return match["user"] if match else None
    
def _resolve_reference_id(project_id, name, getter):
    items = getter(project_id)
    match = _best_match(items, name, ["name"])
    return match["id"] if match else None

_model = None

def get_model():
    """Lazily build the ChatGroq client so import time doesn't require a running server."""
    global _model 
    if _model is None:
        logger.info("Creating ChatGroq client model=%s")
        _model = ChatGroq(model=GROQ_MODEL, groq_api_key = GROQ_API_KEY, temperature=0)

    return _model

def make_tools(project_id):
    """Build the Taiga tools bound to the specific project id
    Rebuilt per call(mirror the old code's per request agent) since project_id comes from the Discord message, not from the model.
    """

    @tool
    def resolve_date(expression:str)->str:
        """Convert a natural-language date expression (e.g. '2 weeks from now',
        'next Friday', 'tomorrow') into an ISO date string (YYYY-MM-DD).
        Always use this instead of computing relative dates yourself."""
        parsed = dateparser.parse(
            expression,
            settings={"PREFER_DATES_FROM": "future", "RELATIVE_BASE": datetime.now()}
        )
        if not parsed:
            return f"Could not parse a date from '{expression}'"
        return parsed.date().isoformat()

    @tool
    def create_item(
        resource:str,
        subject:str,
        description:str="",
        assigned_to:str=None,
        priority: str = None,
        severity: str = None,
        type: str = None,
        status: str = None,
        due_date: str = None,
    ) -> dict:
        """Create a new issue, task, user story or epic in Taiga.
        resource must be one of: issues, tasks, userstories, epics.
        assigned_to: the assignee's name or username, e.g. 'umer'.
        priority: priority name, e.g. 'high' (issues, tasks, userstories only).
        severity: severity name, e.g. 'critical' (issues only).
        type: issue type name, e.g. 'bug' (issues only).
        status: status name, e.g. 'in progress'.
        due_date: an ISO date (YYYY-MM-DD) - resolve relative dates with resolve_date first."""

        payload = {"project":project_id,"subject":subject, "description":description}    

        warnings = []

        if assigned_to:
            uid = _resolve_member_id (project_id, assigned_to)
            if uid:
                payload["assigned_to"] = uid
            else:
                warnings.append(f"could not find a project member matching '{assigned_to}'")

        if priority:
            if resource in ("issues", "tasks", "userstories"):
                pid = _resolve_reference_id(project_id, priority, taiga.get_priorities)
                if pid:
                    payload["priority"] = pid
                else:
                    warnings.append(f"could not find a priority matching '{priority}'")
            else:
                warnings.append(f"priority does not apply to {resource}")

        if severity:
            if resource == "issues":
                sid = _resolve_reference_id(project_id, severity, taiga.get_severities)
                if sid:
                    payload["severity"] = sid
                else:
                    warnings.append(f"could not find a severity matching '{severity}'")
            else:
                warnings.append(f"severity only applies to issues, not {resource}")
 
        if type:
            if resource == "issues":
                tid = _resolve_reference_id(project_id, type, taiga.get_issue_types)
                if tid:
                    payload["type"] = tid
                else:
                    warnings.append(f"could not find an issue type matching '{type}'")
            else:
                warnings.append(f"type does not apply to {resource}")
 
        if status:
            stid = _resolve_reference_id(
                project_id, status, lambda pid: taiga.get_statuses(pid, resource)
            )
            if stid:
                payload["status"] = stid
            else:
                warnings.append(f"could not find a status matching '{status}'")
 
        if due_date:
            payload["due_date"] = due_date
 
        result = taiga.create(resource, payload)

        logger.info("TOOL NAME: %s", create_item.name)
        logger.info("TOOL DESCRIPTION: %s", create_item.description)
        logger.info("TOOL SCHEMA: %s", create_item.args_schema.model_json_schema())


        return {"created": result, "warnings": warnings} if warnings else {"created": result}
    
    @tool
    def fetch_item(resource:str, ref:int )->dict:
        """Fetch an existing issue, task, user story or epic by its Taiga reference number(the number shown in Taiga, e.g. 'Epic #14' -> ref=14).
        resource must be one of: issues, tasks, userstories, epics."""

        try:
            return taiga.get_by_ref(resource, project_id, ref)
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                return {"error": f"No {resource[:-1]} with ref {ref} found in this project."}
            raise

    @tool
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
        due_date: str = None,
        tags: list[str] = None,
        ) -> dict:
        """Update any attribute of an existing issue, task, userstory or epic,
        identified by its Taiga reference number. Only pass fields that should change.
        resource must be one of: issues, tasks, userstories, epics."""

        try:
            current = taiga.get_by_ref(resource, project_id,ref)
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                return {"error": f"No {resource[:-1]} with ref {ref} found in this project."}
            raise

        payload = {"version": current["version"]}
        warnings= []

        if subject is not None:
            payload["subject"] = subject

        if description is not None:
            payload["description"] = description

        if assigned_to:
            uid = _resolve_member_id(project_id, assigned_to)
            if uid:
                payload["assigned_to"] = uid
            else:
                warnings.append(f"could not find a project member matching '{assigned_to}'")

        if priority:
            if resource in ("issues", "tasks", "userstories"):
                pid = _resolve_reference_id(project_id, priority, taiga.get_priorities)
                if pid:
                    payload["priority"] = pid
                else:
                    warnings.append(f"could not find a priority matching '{priority}'")
            else:
                warnings.append(f"priority does not apply to {resource}")

        if severity:
            if resource == "issues":
                sid = _resolve_reference_id(project_id, severity, taiga.get_severities)
                if sid:
                    payload["severity"] = sid
                else:
                    warnings.append(f"could not find a severity matching '{severity}'")
            else:
                warnings.append(f"severity only applies to issues, not {resource}")

        if type:
            if resource == "issues":
                tid = _resolve_reference_id(project_id, type, taiga.get_issue_types)
                if tid:
                    payload["type"] = tid
                else:
                    warnings.append(f"could not find an issue type matching '{type}'")
            else:
                warnings.append(f"type does not apply to {resource}")
        
        if status:
            stid = _resolve_reference_id(
                project_id, status, lambda pid: taiga.get_statuses(pid, resource)
            )
            if stid:
                payload["status"] = stid
            else:
                warnings.append(f"could not find a status matching '{status}'")

        if due_date:
            payload["due_date"] = due_date
        if tags is not None:
            payload["tags"] = tags

        result = taiga.update(resource, current["id"], payload)
        return {"updated": result, "warnings": warnings} if warnings else {"updated": result}


    return [resolve_date, create_item, fetch_item, update_item]

        
# later functionality
def _history_to_messages(history):
    """Convert DB rows (objects with .role/.content) into LangChain messages."""
    messages = []
    for row in history or []:
        if row.role == "user":
            messages.append(HumanMessage(content=row.content))
        else:
            messages.append(AIMessage(content=row.content))
    return messages

def run_agent(user_message, project_id, history =None):
    """Run one turn of the Taiga agent via Groq and return the reply text.
    history: optional list of DB Message rows (oldest first) used as short-term memory.
    """
    tools = make_tools(project_id)
    system_prompt = SYSTEM_PROMPT.format(today=datetime.now().date().isoformat())
    agent = create_agent(
        get_model(),
        tools = tools, 
        system_prompt = system_prompt,
    )
    messages = [HumanMessage(content=user_message)]
    try:
        result = agent.invoke({"messages":messages})
    except Exception:
        logger.exception("Agent invocation failed")
        raise

    final_messages = result.get("messages",[])
    for msg in reversed(final_messages):
        if isinstance(msg, AIMessage) and msg.content:
            return msg.content

    return "Sorry, I couldn't complete that request."

