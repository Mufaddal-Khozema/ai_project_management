"""
agent/tools.py
--------------
Builds LangChain tools bound to a specific PM platform instance, project, and voice meeting operations.
Tools are permission-tier-gated — the agent only sees what the user can do.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any
from langchain_core.tools import tool
from core.base import ProjectManagementPlatform, MemoryStore

logger = logging.getLogger("agent_bridge.tools")


def _resolve_voice_channel(raw_channel: str, default_channel_id: str, default_channel_name: str) -> tuple[str, str]:
    """
    Resolve a channel input (which could be a voice channel snowflake, text channel snowflake,
    Discord mention <#id>, or channel name) to the appropriate voice channel ID and display name.
    """
    voice_map_raw = os.environ.get("VOICE_TO_TEXT_CHANNEL_MAP", "")
    text_to_voice: dict[str, str] = {}
    voice_ids: set[str] = set()
    for pair in voice_map_raw.split(","):
        pair = pair.strip()
        if ":" in pair:
            v, t = pair.split(":", 1)
            v, t = v.strip(), t.strip()
            if v and t:
                text_to_voice[t] = v
                voice_ids.add(v)

    target = (raw_channel or "").strip()
    if target.startswith("<#") and target.endswith(">"):
        target = target[2:-1].strip()

    # If target is already a known voice channel ID
    if target in voice_ids:
        return target, "voice-channel"

    # If target is a text channel ID that is mapped to a voice channel
    if target in text_to_voice:
        return text_to_voice[target], "voice-channel"

    # If no target was given or target is current text channel, check default_channel_id
    if (not target or target == default_channel_id or target.lower() == (default_channel_name or "").lower()) and default_channel_id in text_to_voice:
        return text_to_voice[default_channel_id], "voice-channel"

    # If there is only one voice channel configured in VOICE_TO_TEXT_CHANNEL_MAP and target is not another snowflake
    if len(voice_ids) == 1 and (not target or not target.isdigit()):
        only_voice = list(voice_ids)[0]
        return only_voice, target or "voice-channel"

    ch_id = target or default_channel_id or ""
    ch_name = target if not target.isdigit() else (default_channel_name or "voice-channel")
    return ch_id, ch_name



def build_tools(
    pm: ProjectManagementPlatform,
    project_id: str,
    tier: str,
    memory_store: MemoryStore | None = None,
    project_key: str | None = None,
    guild_id: str | None = None,
    channel_id: str | None = None,
    channel_name: str | None = None,
    org_id: str = "default",
) -> list:
    """
    Return the tool list for the given permission tier.
    tier: 'admin' | 'write' | 'read' | 'none'
    memory_store: optional DualMemoryStore for meeting memory & scheduling queries
    project_key: the PM platform's project slug
    guild_id: Discord server ID
    channel_id: Discord channel ID
    channel_name: Discord channel name
    org_id: multi-tenant organization identifier
    """
    project_key = project_key or project_id

    # ── READ TOOLS (available to everyone with tier >= read) ────────────

    @tool
    def list_items(item_type: str = "all", status: str = "open", assigned_to: str = "") -> str:
        """
        List work items in the current project.
        item_type: task | story | issue | epic | all
        status: open | closed | all
        assigned_to: username (optional, leave blank for all)
        Returns a formatted list of items.
        """
        try:
            results = pm.list_items(
                project_id,
                item_type=None if item_type in ("all", "") else item_type,
                status=None if status == "all" else status,
                assigned_to=assigned_to or None,
            )
            if not results:
                return f"No {item_type} items found with status '{status}'."
            lines = [f"Found {len(results)} item(s):"]
            for item in results[:15]:
                assignee = f" → {item.assignee}" if item.assignee else ""
                lines.append(f"  • #{item.item_id} [{item.item_type}] {item.subject} ({item.status}){assignee}")
            return "\n".join(lines)
        except Exception as e:
            logger.error("list_items error: %s", e)
            return f"Error listing items: {e}"

    @tool
    def get_item(item_id: str) -> str:
        """
        Get details of a specific work item by its ID.
        item_id: numeric or string ID of the item (e.g. '42')
        """
        try:
            item = pm.get_item(project_id, item_id)
            lines = [
                f"**#{item.item_id} [{item.item_type}] {item.subject}**",
                f"Status: {item.status}",
                f"Assigned to: {item.assignee or 'Unassigned'}",
            ]
            if item.tags:
                lines.append(f"Tags: {', '.join(item.tags)}")
            if item.description:
                lines.append(f"\n{item.description}")
            if item.url:
                lines.append(f"\n{item.url}")
            return "\n".join(lines)
        except Exception as e:
            logger.error("get_item error: %s", e)
            return f"Error fetching item #{item_id}: {e}"

    @tool
    def search_items(query: str) -> str:
        """
        Search work items in the project by keyword in subject or description.
        query: search terms
        """
        try:
            results = pm.search_items(project_id, query)
            if not results:
                return f"No items found matching '{query}'."
            lines = [f"Found {len(results)} item(s) matching '{query}':"]
            for item in results[:10]:
                assignee = f" → {item.assignee}" if item.assignee else ""
                lines.append(f"  • #{item.item_id} [{item.item_type}] {item.subject} ({item.status}){assignee}")
            return "\n".join(lines)
        except Exception as e:
            logger.error("search_items error: %s", e)
            return f"Error searching items: {e}"

    @tool
    def get_project_summary() -> str:
        """
        Get an overview of the current project: active sprint, open task/issue/story counts,
        and team members.
        """
        try:
            ctx = pm.get_project_context(project_id)
            lines = [
                f"**Project: {ctx.project_name}**",
                f"Active Sprint: {ctx.active_sprint or 'None'}" + (f" (ends {ctx.sprint_end_date})" if ctx.sprint_end_date else ""),
                f"Open Tasks: {ctx.open_task_count} | Issues: {ctx.open_issue_count} | Stories: {ctx.open_story_count}",
                f"Members ({len(ctx.members)}): " + ", ".join(m["username"] for m in ctx.members),
            ]
            return "\n".join(lines)
        except Exception as e:
            logger.error("get_project_summary error: %s", e)
            return f"Error fetching project summary: {e}"

    @tool
    def list_members() -> str:
        """
        List all team members on this project with their roles.
        Use this when you need to check valid usernames before assigning tasks.
        """
        try:
            members = pm.list_members(project_id)
            if not members:
                return "No members found for this project."
            lines = [f"Project members ({len(members)}):"]
            for m in members:
                role = f" ({m['role']})" if m.get("role") else ""
                full = f" - {m['full_name']}" if m.get("full_name") else ""
                lines.append(f"  • **{m['username']}**{role}{full}")
            return "\n".join(lines)
        except Exception as e:
            logger.error("list_members error: %s", e)
            return f"Error listing members: {e}"

    @tool
    def get_sprint_info() -> str:
        """
        Get details about the active sprint including dates, status, and associated items.
        """
        try:
            sprint = pm.get_active_sprint(project_id)
            if not sprint:
                return "No active sprint currently in this project."
            lines = [
                f"**Active Sprint: {sprint.get('name', 'Sprint')}**",
                f"Dates: {sprint.get('start_date', '?')} → {sprint.get('end_date', '?')}",
                f"Closed: {'Yes' if sprint.get('closed') else 'No'}",
            ]
            if sprint.get("total_points") is not None:
                lines.append(f"Total Points: {sprint['total_points']}")
            return "\n".join(lines)
        except Exception as e:
            logger.error("get_sprint_info error: %s", e)
            return f"Error fetching sprint info: {e}"

    @tool
    def get_upcoming_due_items(days_ahead: int = 3) -> str:
        """
        List open tasks, stories, and issues that are approaching their due date or are overdue.
        days_ahead: number of days ahead to inspect (default: 3)
        """
        try:
            items = pm.get_due_items(project_id, days_ahead=days_ahead)
            if not items:
                return f"No open items found with due dates within the next {days_ahead} day(s)."
            lines = [f"Found {len(items)} item(s) due soon or overdue:"]
            for item in items:
                assignee = f" → @{item['assigned_to']}" if item.get("assigned_to") else " → Unassigned"
                lines.append(f"  • #{item['ref']} [{item['type']}] {item['subject']} (Due: **{item['due_date']}**){assignee}")
            return "\n".join(lines)
        except Exception as e:
            logger.error("get_upcoming_due_items error: %s", e)
            return f"Error fetching due items: {e}"

    read_tools = [list_items, get_item, search_items, get_project_summary, list_members, get_sprint_info, get_upcoming_due_items]

    # ── Memory & Meeting Tools (available if MemoryStore configured) ────

    if memory_store:
        @tool
        def search_meetings(query: str) -> str:
            """
            Search past meeting transcripts and summaries for keywords, people, decisions,
            or topics — including paraphrased matches.
            Returns matching meeting excerpts with dates and participants.
            """
            try:
                meetings = memory_store.search_meetings(query, project_key=project_key) if hasattr(memory_store, "search_meetings") else []
                if not meetings:
                    return f"No meeting records found matching '{query}'."
                lines = [f"Meeting search results for '{query}' ({len(meetings)} found):"]
                for m in meetings:
                    date = m.get("ended_at", "")
                    participants = m.get("participants", [])
                    decisions = m.get("decisions", [])
                    topics = m.get("topics", [])
                    lines.append(f"\n  Meeting on {date}")
                    lines.append(f"  Participants: {', '.join(participants)}")
                    if topics:
                        lines.append(f"  Topics: {', '.join(topics)}")
                    if decisions:
                        lines.append(f"  Decisions: {'; '.join(decisions)}")
                    matched = m.get("matched_chunks")
                    if matched:
                        lines.append("  Most relevant excerpts:")
                        for c in matched:
                            lines.append(f"    ({c.get('kind', 'excerpt')}, score={c.get('score')}) {c.get('text', '')[:200]}")
                return "\n".join(lines)
            except Exception as e:
                return f"Error searching meetings: {e}"

        @tool
        def get_project_decisions() -> str:
            """
            Get recent decisions made in project meetings.
            """
            try:
                decisions = memory_store.get_project_decisions(project_key) if hasattr(memory_store, "get_project_decisions") else []
                if not decisions:
                    return "No decisions recorded in meetings yet."
                lines = ["Recent project decisions:"]
                for d in decisions:
                    date = d.get("date", "")
                    text = d.get("decision", "")
                    lines.append(f"  • {text} (meeting {d.get('meeting_id', '?')}, {date})")
                return "\n".join(lines)
            except Exception as e:
                return f"Error fetching decisions: {e}"

        @tool
        def get_action_items(owner: str = "") -> str:
            """
            Get currently OPEN action items tracked from past meetings, optionally filtered to a person.
            owner: optional username/name to filter by
            """
            try:
                items = memory_store.get_action_items(project_key, owner=owner or None)
                if not items:
                    scope = f" for {owner}" if owner else ""
                    return f"No open action items{scope}."
                lines = [f"Open action items ({len(items)}):"]
                for i in items:
                    who = i.get("owner") or "Unassigned"
                    text = i.get("text", "")
                    ref = i.get("created_in", "")
                    lines.append(f"  • [{who}] {text}" + (f" (from meeting {ref})" if ref else ""))
                return "\n".join(lines)
            except Exception as e:
                return f"Error fetching action items: {e}"

        @tool
        def remember_fact(fact: str) -> str:
            """
            Record a durable fact about this project that should be remembered going forward.
            fact: the fact to remember, stated plainly in one sentence
            """
            try:
                memory_store.remember_fact(project_key, fact, source="chat")
                return f"✅ Noted: {fact}"
            except Exception as e:
                return f"❌ Error saving fact: {e}"

        @tool
        def recall_facts(topic: str = "") -> str:
            """
            Recall durable facts previously saved about this project.
            topic: optional keyword/topic to filter by
            """
            try:
                facts = memory_store.recall_facts(project_key, topic=topic or None)
                if not facts:
                    return "No project facts recorded yet."
                lines = ["Project facts:"]
                for f in facts:
                    lines.append(f"  • {f.get('fact', '')} (source: {f.get('source', 'unknown')})")
                return "\n".join(lines)
            except Exception as e:
                return f"Error recalling facts: {e}"

        @tool
        def search_chat_history(query: str, channel_name: str = "") -> str:
            """
            Search past channel text chat messages and team conversations for keywords, topics, or decisions.
            query: search keywords or topic
            """
            try:
                if not hasattr(memory_store, "search_chat_messages"):
                    return "Chat message search is not available with the current storage backend."
                messages = memory_store.search_chat_messages(query, project_key=project_key, top_k=6)
                if not messages:
                    return f"No chat messages found matching '{query}'."
                lines = [f"Found {len(messages)} matching chat message(s):"]
                for msg in messages:
                    author = msg.get("author_name", "Team Member")
                    content = msg.get("content", "")
                    ts = msg.get("created_at", "")
                    ch = msg.get("channel_name", "")
                    ch_info = f" in #{ch}" if ch else ""
                    lines.append(f"  • [{author}{ch_info} | {ts}]: {content[:250]}")
                return "\n".join(lines)
            except Exception as e:
                return f"Error searching chat history: {e}"

        @tool
        def get_recent_channel_chat(limit: int = 15) -> str:
            """
            Fetch the most recent text chat messages in the current channel.
            """
            try:
                if not hasattr(memory_store, "get_recent_channel_messages"):
                    return "Recent chat retrieval is not available with the current storage backend."
                messages = memory_store.get_recent_channel_messages(channel_id or project_id, limit=min(limit, 30))
                if not messages:
                    return "No recent chat messages recorded in this channel."
                ordered = list(reversed(messages))
                lines = ["Recent channel messages:"]
                for msg in ordered:
                    author = msg.get("author_name", "Team Member")
                    content = msg.get("content", "")
                    lines.append(f"  • {author}: {content}")
                return "\n".join(lines)
            except Exception as e:
                return f"Error retrieving recent channel chat: {e}"

        @tool
        def get_chat_summary(topic: str = "") -> str:
            """
            Retrieve and summarize recent team chat messages regarding a specific topic, feature, or blocker.
            """
            try:
                if not hasattr(memory_store, "search_chat_messages"):
                    return "Chat summarization is not available with the current storage backend."
                messages = memory_store.search_chat_messages(topic, project_key=project_key, top_k=8)
                if not messages:
                    return f"No chat records found regarding '{topic}'."
                lines = [f"Chat discussion context for '{topic}':"]
                for msg in messages:
                    author = msg.get("author_name", "Team Member")
                    content = msg.get("content", "")
                    ch = msg.get("channel_name", "")
                    ch_info = f" (#{ch})" if ch else ""
                    lines.append(f"  • {author}{ch_info}: {content}")
                return "\n".join(lines)
            except Exception as e:
                return f"Error summarizing chat: {e}"

        @tool
        def list_scheduled_meetings() -> str:
            """
            List active scheduled standup meetings and recurring voice sessions configured for this server/organization.
            Use this when asked what meetings or standups are scheduled, or to check schedule times.
            """
            try:
                if not hasattr(memory_store, "list_scheduled_meetings"):
                    return "Schedule listing is not supported by the current storage backend."
                schedules = memory_store.list_scheduled_meetings(org_id=org_id, guild_id=guild_id)
                if not schedules:
                    return "No scheduled meetings or standups found for this organization/server."
                lines = [f"Found {len(schedules)} scheduled meeting(s):"]
                for s in schedules:
                    sid = s.get("id", "?")
                    title = s.get("title", "Standup")
                    rec = s.get("recurrence", "daily")
                    time_str = s.get("time", "10:00")
                    tz = s.get("timezone", "UTC")
                    ch = s.get("channelName", "")
                    days = s.get("daysOfWeek", [])
                    days_str = f" on {', '.join(days)}" if days else ""
                    status_icon = "🟢" if s.get("enabled", True) else "⚪ (disabled)"
                    lines.append(f"  • {status_icon} **{title}** [ID: `{sid}`] — {rec.capitalize()} at {time_str} {tz}{days_str} (Channel: #{ch})")
                return "\n".join(lines)
            except Exception as e:
                return f"Error listing scheduled meetings: {e}"

        read_tools.extend([
            search_meetings, get_project_decisions,
            get_action_items, remember_fact, recall_facts,
            search_chat_history, get_recent_channel_chat, get_chat_summary,
            list_scheduled_meetings,
        ])

    if tier in ("none", "read"):
        return read_tools

    # ── WRITE TOOLS (write + admin) ──────────────────────────────────

    @tool
    def create_item(item_type: str, subject: str, description: str = "",
                    assigned_to: str = "", tags: str = "") -> str:
        """
        Create a new work item in the project.
        item_type: task | story | issue | epic
        subject: title of the item (required)
        description: optional detailed description
        assigned_to: optional username to assign to (must be a team member username)
        tags: optional comma-separated tags e.g. 'backend,urgent'
        """
        try:
            tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
            item = pm.create_item(
                project_id, item_type, subject, description,
                assigned_to or None, tag_list or None,
            )
            result = f"✅ Created {item_type} **#{item.item_id}**: {item.subject}"
            if item.assignee:
                result += f"\n   Assigned to: {item.assignee}"
            if item.url:
                result += f"\n   {item.url}"
            return result
        except Exception as e:
            logger.error("create_item error: %s", e)
            return f"❌ Error creating {item_type}: {e}"

    @tool
    def close_item(item_id: str) -> str:
        """
        Mark a work item as closed/done.
        item_id: the numeric ID of the item to close (e.g. '42')
        """
        try:
            item = pm.close_item(project_id, item_id)
            result = f"✅ Closed #{item.item_id}: **{item.subject}** → {item.status}"
            if item.url:
                result += f"\n   {item.url}"
            return result
        except Exception as e:
            return f"❌ Error closing item #{item_id}: {e}"

    @tool
    def update_item(item_id: str, subject: str = "", description: str = "",
                    assigned_to: str = "") -> str:
        """
        Update fields on an existing work item. Only provide fields you want to change.
        item_id: numeric ID of the item
        subject: new title (optional)
        description: new description (optional)
        assigned_to: username to assign to (optional)
        """
        try:
            fields: dict[str, Any] = {}
            if subject:
                fields["subject"] = subject
            if description:
                fields["description"] = description
            if assigned_to:
                members = pm.list_members(project_id)
                m = next((x for x in members if x["username"] == assigned_to), None)
                if m:
                    fields["assigned_to"] = m["id"]
                else:
                    return f"❌ User '{assigned_to}' not found in project. Use list_members to check usernames."
            if not fields:
                return "No fields to update. Provide at least one of: subject, description, assigned_to."
            item = pm.update_item(project_id, item_id, fields)
            return f"✅ Updated #{item.item_id}: **{item.subject}**"
        except Exception as e:
            return f"❌ Error updating item #{item_id}: {e}"

    @tool
    def create_epic(subject: str, description: str = "") -> str:
        """
        Create a new epic in the project.
        subject: title of the epic
        description: optional description
        """
        try:
            item = pm.create_epic(project_id, subject, description)
            result = f"✅ Created epic **#{item.item_id}**: {item.subject}"
            if item.url:
                result += f"\n   {item.url}"
            return result
        except Exception as e:
            return f"❌ Error creating epic: {e}"

    @tool
    def link_story_to_epic(story_id: str, epic_id: str) -> str:
        """
        Link a user story to an existing epic.
        story_id: numeric ID of the user story
        epic_id: numeric ID of the epic
        """
        try:
            item = pm.link_to_epic(project_id, story_id, epic_id)
            return f"✅ Linked story #{story_id} to epic #{epic_id}"
        except Exception as e:
            return f"❌ Error linking story to epic: {e}"

    @tool
    def extend_due_date(item_id: str, new_due_date: str, reason: str = "") -> str:
        """
        Extend or update the due date of a work item (task, user story, issue) and notify all watchers/stakeholders.
        item_id: numeric ID of the item (e.g. '42')
        new_due_date: new due date in YYYY-MM-DD format (e.g. '2026-10-30')
        reason: explanation for why the due date was extended (shared with stakeholders)
        """
        try:
            res = pm.extend_due_date(project_id, item_id, new_due_date, reason)
            subject = res.get("subject", f"Item #{item_id}")
            ref = res.get("ref", item_id)
            res_type = res.get("type", "item")
            old_date = res.get("old_due_date") or "none"
            watchers_ids = res.get("watchers", [])
            watchers_info = pm.get_watchers_info(project_id, watchers_ids) if watchers_ids else []

            watcher_mentions = []
            for w in watchers_info:
                uname = w.get("username")
                if uname:
                    watcher_mentions.append(f"@{uname}")

            lines = [
                f"✅ **Due Date Extended** for {res_type} **#{ref}** (*{subject}*)",
                f"📅 **Deadline**: `{old_date}` ➔ `{new_due_date}`",
            ]
            if reason:
                lines.append(f"📝 **Reason**: {reason}")

            if watcher_mentions:
                lines.append(f"📢 **Stakeholders / Watchers Notified**: {', '.join(watcher_mentions)}")
            else:
                lines.append("ℹ️ *No watchers currently registered on this item.*")

            if res.get("url"):
                lines.append(f"🔗 {res['url']}")

            return "\n".join(lines)
        except Exception as e:
            logger.error("extend_due_date error: %s", e)
            return f"❌ Error extending due date for #{item_id}: {e}"

    write_tools = [create_item, close_item, update_item, extend_due_date, create_epic, link_story_to_epic]

    # ── Meeting Scheduling & Voice Control Tools ─────────────────────────

    if memory_store:
        @tool
        def schedule_meeting(
            title: str = "Daily Standup",
            recurrence: str = "weekdays",
            time: str = "10:00",
            timezone: str = "UTC",
            channel_name_or_id: str = "",
            days_of_week: str = "",
            date: str = "",
            duration_minutes: int = 15,
        ) -> str:
            """
            Schedule a recurring standup or one-time voice meeting. The bot will automatically join the voice channel at the specified time.
            title: name of the meeting (e.g. 'Daily Standup', 'Sprint Planning')
            recurrence: 'daily' | 'weekdays' | 'weekly' | 'once' (default 'weekdays')
            time: 24-hour time string in HH:MM format (e.g. '09:30', '14:00', '10:00')
            timezone: valid timezone (e.g. 'UTC', 'America/New_York', 'Europe/London', 'Asia/Karachi')
            channel_name_or_id: name or ID of the voice channel (leave blank to use current/mapped channel)
            days_of_week: comma-separated days for weekly recurrence e.g. 'Mon,Tue,Wed,Thu,Fri'
            date: target date in YYYY-MM-DD format (only needed if recurrence is 'once')
            duration_minutes: meeting duration in minutes (default 15)
            """
            try:
                if not hasattr(memory_store, "create_scheduled_meeting"):
                    return "Meeting scheduling is not supported by the current storage backend."

                rec = recurrence.lower().strip()
                if rec in ("daily", "every day", "everyday"):
                    rec = "daily"
                elif rec in ("weekdays", "weekday", "mon-fri", "monday to friday"):
                    rec = "weekdays"
                elif rec in ("once", "one-time", "single"):
                    rec = "once"
                else:
                    rec = "weekly"

                days_list = []
                if rec == "weekly" or days_of_week:
                    day_map = {
                        "0": "Sun", "sun": "Sun", "sunday": "Sun",
                        "1": "Mon", "mon": "Mon", "monday": "Mon",
                        "2": "Tue", "tue": "Tue", "tuesday": "Tue",
                        "3": "Wed", "wed": "Wed", "wednesday": "Wed",
                        "4": "Thu", "thu": "Thu", "thursday": "Thu",
                        "5": "Fri", "fri": "Fri", "friday": "Fri",
                        "6": "Sat", "sat": "Sat", "saturday": "Sat",
                    }
                    raw_days = [d.strip().lower() for d in (days_of_week or "Mon,Tue,Wed,Thu,Fri").split(",") if d.strip()]
                    days_list = [day_map[d] for d in raw_days if d in day_map]
                    if not days_list:
                        days_list = ["Mon", "Tue", "Wed", "Thu", "Fri"]

                target_ch_id, target_ch_name = _resolve_voice_channel(channel_name_or_id, channel_id or "", channel_name or "")

                schedule_input = {
                    "title": title or "Daily Standup",
                    "guildId": guild_id or "",
                    "channelId": target_ch_id,
                    "channelName": target_ch_name,
                    "recurrence": rec,
                    "time": time or "10:00",
                    "timezone": timezone or "UTC",
                    "daysOfWeek": days_list if rec == "weekly" else None,
                    "date": date if rec == "once" else None,
                    "durationMs": max(duration_minutes, 5) * 60 * 1000,
                    "enabled": True,
                }

                created = memory_store.create_scheduled_meeting(schedule_input, org_id=org_id)
                if not created:
                    return "❌ Failed to create scheduled meeting in storage."

                sched_id = created.get("id", created.get("_id", "?"))
                detail = f"{rec.capitalize()} at {time} {timezone}"
                if rec == "weekly" and days_list:
                    detail += f" ({', '.join(days_list)})"
                elif rec == "once" and date:
                    detail += f" on {date}"

                return f"✅ **Scheduled Meeting Created!**\n  • **Title**: {title}\n  • **Schedule**: {detail}\n  • **Voice Channel**: #{target_ch_name}\n  • **Duration**: {duration_minutes} min\n  • **ID**: `{sched_id}`"
            except Exception as e:
                logger.error("schedule_meeting error: %s", e)
                return f"❌ Error creating scheduled meeting: {e}"

        @tool
        def cancel_scheduled_meeting(schedule_id: str) -> str:
            """
            Cancel / delete an existing scheduled meeting by its ID.
            schedule_id: the ID of the schedule (obtain from list_scheduled_meetings)
            """
            try:
                if not hasattr(memory_store, "delete_scheduled_meeting"):
                    return "Meeting cancellation is not supported by the current storage backend."
                success = memory_store.delete_scheduled_meeting(schedule_id.strip(), org_id=org_id)
                if success:
                    return f"✅ Cancelled scheduled meeting `{schedule_id}`."
                return f"❌ Schedule `{schedule_id}` was not found or already deleted."
            except Exception as e:
                return f"❌ Error cancelling schedule: {e}"

        @tool
        def start_voice_meeting(channel_name_or_id: str = "", duration_minutes: int = 30) -> str:
            """
            Start an on-demand voice standup or meeting immediately. The bot will join the voice channel and begin listening & transcribing.
            channel_name_or_id: name or ID of the voice channel to join (optional)
            duration_minutes: duration in minutes (default 30)
            """
            try:
                if not hasattr(memory_store, "start_voice_meeting"):
                    return "On-demand voice meeting is not supported by the current storage backend."
                target_ch, target_ch_name = _resolve_voice_channel(channel_name_or_id, channel_id or "", channel_name or "")
                if not target_ch:
                    return "❌ Voice channel ID or name is required to start a meeting."
                res = memory_store.start_voice_meeting(
                    guild_id=guild_id or "",
                    channel_id=target_ch,
                    org_id=org_id,
                    duration_ms=duration_minutes * 60 * 1000,
                )
                if res.get("started"):
                    return f"🎙️ **Voice Meeting Started!**\n  • Server: `{guild_id}`\n  • Channel: #{target_ch_name} (`{target_ch}`)\n  • Duration: {duration_minutes} min\n  • The Scrum Master bot is joining the voice room now."
                return f"❌ Could not start voice meeting: {res.get('error', 'Unknown error')}"
            except Exception as e:
                return f"❌ Error starting voice meeting: {e}"

        @tool
        def stop_voice_meeting() -> str:
            """
            Stop the active voice meeting in this server immediately. The bot will leave the channel and consolidate the transcript.
            """
            try:
                if not hasattr(memory_store, "stop_voice_meeting"):
                    return "Stopping voice meetings is not supported by the current storage backend."
                res = memory_store.stop_voice_meeting(guild_id=guild_id or "", org_id=org_id)
                if res.get("stopped"):
                    return "⏹️ **Voice Meeting Stopped.**\n  • The bot has left the channel and will consolidate the transcript and action items."
                return f"❌ Could not stop voice meeting: {res.get('error', 'No active meeting in this server')}"
            except Exception as e:
                return f"❌ Error stopping voice meeting: {e}"

        write_tools.extend([
            schedule_meeting,
            cancel_scheduled_meeting,
            start_voice_meeting,
            stop_voice_meeting,
        ])

    if tier == "write":
        return read_tools + write_tools

    # ── ADMIN TOOLS (admin only) ─────────────────────────────────────

    @tool
    def bulk_create(items_json: str) -> str:
        """
        Create multiple items at once.
        items_json: JSON array of objects, each with 'item_type' and 'subject' keys.
        Example: [{"item_type":"task","subject":"Fix login bug"},{"item_type":"issue","subject":"UI crash"}]
        """
        try:
            items = json.loads(items_json)
            results = []
            for it in items:
                item = pm.create_item(project_id, it["item_type"], it["subject"],
                    it.get("description", ""))
                results.append(f"  ✅ #{item.item_id} [{item.item_type}] {item.subject}")
            return f"Bulk created {len(results)} items:\n" + "\n".join(results)
        except json.JSONDecodeError:
            return "❌ Invalid JSON. Format: [{\"item_type\":\"task\",\"subject\":\"...\"},...]"
        except Exception as e:
            return f"❌ Error in bulk create: {e}"

    @tool
    def bulk_close(item_ids_csv: str) -> str:
        """
        Close multiple items by ID.
        item_ids_csv: comma-separated numeric item IDs, e.g. '101,102,103'
        """
        try:
            ids = [i.strip() for i in item_ids_csv.split(",") if i.strip()]
            results = []
            for item_id in ids:
                try:
                    item = pm.close_item(project_id, item_id)
                    results.append(f"  ✅ #{item.item_id} {item.subject} → {item.status}")
                except Exception as e:
                    results.append(f"  ❌ #{item_id}: {e}")
            return f"Bulk close results ({len(ids)} items):\n" + "\n".join(results)
        except Exception as e:
            return f"❌ Error in bulk close: {e}"

    admin_tools = [bulk_create, bulk_close]
    return read_tools + write_tools + admin_tools
