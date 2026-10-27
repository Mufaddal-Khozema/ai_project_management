"""
agent/agent.py
--------------
AgentBridge — full pipeline using LangChain 1.x native tool-calling loop.
No AgentExecutor — uses the bind_tools + manual ReAct pattern that works
with LangChain >= 1.0 and Gemini.

Memory architecture:
  - DualMemoryStore: Redis (short-term conversation history) + MongoDB (long-term meeting data)
  - ChannelMemoryStore: In-memory fallback for standalone mode (no Redis/MongoDB)
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import BaseTool
from langchain_core.messages import (
    HumanMessage, SystemMessage, AIMessage, ToolMessage, BaseMessage
)

from core.base import (
    IncomingMessage, OutgoingMessage,
    CommunicationPlatform, ProjectManagementPlatform, ProjectContext,
    MemoryStore,
)
from core.embeddings import EmbeddingProvider, chunk_text, rank_by_similarity
from core.identity_client import IdentityClient, IdentityResult
from agent.context import ContextAssembler
from agent.tools import build_tools

logger = logging.getLogger("agent_bridge.agent")


# ── System prompt ──────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """\
You are Agent Bridge, a project management assistant embedded in {comm_platform}.
You help the team manage their work in {pm_platform} and coordinate voice standups & meetings.

## Current Project: {project_name}
- Active Sprint: {active_sprint} (ends {sprint_end})
- Open Tasks: {open_tasks}  |  Open Issues: {open_issues}  |  Open Stories: {open_stories}
- Team members: {members}

## Recent meeting context
{meetings}

## Guidelines
- Use available tools to perform actions — never fabricate IDs or data.
- If a request is ambiguous, ask ONE short clarifying question before acting.
- For bulk or destructive actions (closing many items), confirm with the user first.
- Keep replies concise and clear. Use ✅ for success, ❌ for errors.
- When you create or close an item, always include the item ID and URL if available.
- If you cannot find a user by username, call list_members first.
- You can create and list recurring standup schedules or start on-demand voice meetings when requested.
- You may reference details from the meeting transcripts above (people, decisions,
  tasks discussed) when answering — prefer them over guessing.
- Today you are speaking with: {author_name} (permission tier: {tier})
"""

# ── Intent classifier ──────────────────────────────────────────────────────────

CLASSIFIER_PROMPT = """\
Classify this project management message. Respond ONLY with valid JSON, no markdown fences.

Message: {message}

JSON (exactly this schema):
{{"intent": "create|update|close|list|query|search|summarize|schedule|unknown",
  "resource": "task|story|epic|issue|sprint|project|schedule|meeting|unknown",
  "confidence": 0.95,
  "needs_write": false}}"""


FALLBACK_CLASSIFIER_MODELS = [
    "gemini-3.6-flash",
    "gemini-3.8-flash",
    "gemini-flash-latest",
]


class IntentRouter:
    def __init__(self, api_key: str, model: str = "gemini-3.6-flash"):
        self._api_key = api_key
        models = [model] + [m for m in FALLBACK_CLASSIFIER_MODELS if m != model]
        self._model_candidates = models
        self._current_idx = 0
        self.model = self._model_candidates[0]
        self._llm = ChatGoogleGenerativeAI(
            model=self.model, google_api_key=api_key, temperature=0
        )

    def _switch_to_next_model(self) -> bool:
        if self._current_idx < len(self._model_candidates) - 1:
            self._current_idx += 1
            self.model = self._model_candidates[self._current_idx]
            logger.info("Switching classifier to fallback model: %s", self.model)
            self._llm = ChatGoogleGenerativeAI(
                model=self.model, google_api_key=self._api_key, temperature=0
            )
            return True
        return False

    def classify(self, message: str) -> dict[str, Any]:
        while True:
            try:
                resp = self._llm.invoke([
                    HumanMessage(content=CLASSIFIER_PROMPT.format(message=message))
                ])
                from core.base import extract_text_content
                text = extract_text_content(resp.content).strip()
                # Strip markdown fences if model adds them
                if "```" in text:
                    parts = text.split("```")
                    for part in parts:
                        part = part.strip()
                        if part.startswith("json"):
                            part = part[4:].strip()
                        if part.startswith("{"):
                            text = part
                            break
                return json.loads(text)
            except Exception as e:
                err_str = str(e)
                if ("404" in err_str or "NOT_FOUND" in err_str or "no longer available" in err_str) and self._switch_to_next_model():
                    continue
                logger.warning("Intent classification failed (%s), defaulting to unknown", e)
                return {"intent": "unknown", "resource": "unknown",
                        "confidence": 0.0, "needs_write": True}


# ── In-memory fallback (standalone mode, no Redis/MongoDB) ─────────────────────

class ChannelMemoryStore(MemoryStore):
    """
    Stores conversation history per Discord channel as a list of BaseMessage.
    Uses a simple ring buffer bounded by max_messages to avoid context overflow.
    Fallback for standalone mode when Redis/MongoDB are not available.

    Inherits MemoryStore's no-op defaults for get_action_items/remember_fact/
    recall_facts/get_relevant_meeting_context — this store has no durable
    project-scoped memory, only per-channel conversation + injected meeting
    summaries, so those simply degrade gracefully instead of erroring.
    """
    def __init__(self, max_messages: int = 20):
        self._store: dict[str, list[BaseMessage]] = {}
        self._max = max_messages

    def get(self, channel_id: str) -> list[BaseMessage]:
        return self._store.setdefault(channel_id, [])

    def append(self, channel_id: str, messages: list[BaseMessage]) -> None:
        buf = self._store.setdefault(channel_id, [])
        buf.extend(messages)
        # Keep only the last N messages to avoid context overflow
        if len(buf) > self._max:
            self._store[channel_id] = buf[-self._max:]

    def clear(self, channel_id: str) -> None:
        self._store.pop(channel_id, None)

    def get_meeting_context(self, channel_id: str) -> list[str]:
        """
        Return the raw text of every injected meeting summary
        ("[MEETING CONTEXT ...]" SystemMessages) for a channel, oldest first.
        These are surfaced to the agent through the system prompt so context
        survives even after the last-30-messages ring buffer drops them.
        """
        buf = self.get(channel_id)
        return [
            m.content
            for m in buf
            if isinstance(m, SystemMessage) and m.content.startswith("[MEETING CONTEXT")
        ]


# ── Dual-layer memory store (Redis short-term + MongoDB long-term) ─────────────

_MESSAGE_TYPE_MAP = {
    "human": HumanMessage,
    "ai": AIMessage,
    "system": SystemMessage,
    "tool": ToolMessage,
}


def _serialize_message(msg: BaseMessage) -> dict:
    """Convert a BaseMessage to a JSON-serializable dict."""
    from core.base import extract_text_content
    msg_type = type(msg).__name__.lower().replace("message", "")
    if msg_type == "base":
        msg_type = "human"
    data = {
        "type": msg_type,
        "content": extract_text_content(msg.content),
        "ts": time.time(),
    }
    if hasattr(msg, "tool_call_id") and getattr(msg, "tool_call_id", None):
        data["tool_call_id"] = msg.tool_call_id
    if hasattr(msg, "tool_calls") and getattr(msg, "tool_calls", None):
        data["tool_calls"] = msg.tool_calls
    return data


def _deserialize_message(data: dict) -> BaseMessage:
    """Convert a dict back to a BaseMessage."""
    from core.base import extract_text_content
    msg_type = data.get("type", "human")
    cls = _MESSAGE_TYPE_MAP.get(msg_type, HumanMessage)
    content = extract_text_content(data.get("content", ""))

    if cls is ToolMessage:
        return ToolMessage(
            content=content,
            tool_call_id=data.get("tool_call_id", "call_default"),
        )
    if cls is AIMessage:
        tool_calls = data.get("tool_calls")
        if tool_calls:
            return AIMessage(content=content, tool_calls=tool_calls)
        return AIMessage(content=content)
    return cls(content=content)


class DualMemoryStore(MemoryStore):
    """
    Redis for hot path (conversation history, live transcripts).
    MongoDB for durable long-term (meeting summaries, extracted entities).

    Keys:
      channel:{channel_id}:history  — Redis LIST of serialized messages, TTL 7 days
      meeting:{meeting_id}:transcript — Redis LIST of transcript lines, TTL 24h
      meeting:{meeting_id}:standup  — Redis HASH of standup data, TTL 24h
    """

    def __init__(
        self,
        redis_client,
        mongo_db,
        max_messages: int = 50,
        history_ttl_seconds: int = 7 * 86400,
        meeting_ttl_seconds: int = 24 * 3600,
        embeddings: EmbeddingProvider | None = None,
        chunk_tokens: int = 400,
        chunk_overlap_tokens: int = 60,
    ):
        self._redis = redis_client
        self._mongo = mongo_db
        self._max = max_messages
        self._history_ttl = history_ttl_seconds
        self._meeting_ttl = meeting_ttl_seconds
        # Optional — when unset, semantic search/embedding features silently
        # degrade to keyword/regex search and recency-based ranking.
        self._embeddings = embeddings
        self._chunk_tokens = chunk_tokens
        self._chunk_overlap_tokens = chunk_overlap_tokens

    # ── Conversation history (Redis) ──────────────────────────────────────────

    def get(self, channel_id: str) -> list[BaseMessage]:
        key = f"channel:{channel_id}:history"
        try:
            raw_list = self._redis.lrange(key, 0, -1)
            return [_deserialize_message(json.loads(r)) for r in raw_list]
        except Exception as e:
            logger.warning("Redis get failed for channel %s: %s", channel_id, e)
            return []

    def append(self, channel_id: str, messages: list[BaseMessage]) -> None:
        key = f"channel:{channel_id}:history"
        try:
            pipe = self._redis.pipeline()
            for msg in messages:
                pipe.rpush(key, json.dumps(_serialize_message(msg)))
            pipe.ltrim(key, -self._max, -1)
            pipe.expire(key, self._history_ttl)
            pipe.execute()
        except Exception as e:
            logger.warning("Redis append failed for channel %s: %s", channel_id, e)

    def clear(self, channel_id: str) -> None:
        key = f"channel:{channel_id}:history"
        try:
            self._redis.delete(key)
        except Exception as e:
            logger.warning("Redis clear failed for channel %s: %s", channel_id, e)

    # ── Meeting context (MongoDB long-term) ───────────────────────────────────

    def get_meeting_context(self, channel_id: str) -> list[str]:
        """
        Query MongoDB for the most recent meetings for this channel, newest
        first. Recency-only fallback — used when no query is available (e.g.
        no current user message yet) or ranking isn't needed.
        """
        try:
            meetings = list(
                self._mongo.meetings.find({"text_channel_id": channel_id})
                .sort("ended_at", -1)
                .limit(3)
            )
        except Exception as e:
            logger.warning("MongoDB query failed for meeting context: %s", e)
            return []

        summaries = []
        for m in meetings:
            summaries.append(self._format_meeting_summary(m))
        return summaries

    def get_relevant_meeting_context(
        self, channel_id: str, query: str, project_key: str | None = None, top_k: int = 3
    ) -> list[str]:
        """
        Query-aware meeting context: rank meetings for this channel by
        semantic similarity to `query` when embeddings are available, else
        fall back to recency. This is what fixes the old behavior of always
        injecting "the last 3 meetings" regardless of what the user actually
        asked about.
        """
        if not query or not query.strip() or not (self._embeddings and self._embeddings.available):
            return self.get_meeting_context(channel_id)[-top_k:]

        query_vector = self._embeddings.embed_query(query)
        if not query_vector:
            return self.get_meeting_context(channel_id)[-top_k:]

        try:
            candidates = list(
                self._mongo.meeting_chunks.find(
                    {"channel_id": channel_id, "kind": {"$in": ["decision", "action_item", "blocker", "topic"]}}
                )
                .sort("ended_at", -1)
                .limit(300)
            )
        except Exception as e:
            logger.warning("MongoDB meeting_chunks query failed: %s", e)
            return self.get_meeting_context(channel_id)[-top_k:]

        if not candidates:
            return self.get_meeting_context(channel_id)[-top_k:]

        ranked = rank_by_similarity(query_vector, candidates, top_k=top_k * 3)
        # Pull the *full* meeting summary for each distinct meeting_id the
        # ranked chunks point to, best-scoring meeting first, deduplicated.
        seen_meetings: set[str] = set()
        ordered_meeting_ids: list[str] = []
        for chunk in ranked:
            mid = chunk.get("meeting_id")
            if mid and mid not in seen_meetings:
                seen_meetings.add(mid)
                ordered_meeting_ids.append(mid)
            if len(ordered_meeting_ids) >= top_k:
                break

        if not ordered_meeting_ids:
            return self.get_meeting_context(channel_id)[-top_k:]

        try:
            docs = {
                d["meeting_id"]: d
                for d in self._mongo.meetings.find({"meeting_id": {"$in": ordered_meeting_ids}})
            }
        except Exception as e:
            logger.warning("MongoDB meetings lookup failed: %s", e)
            return self.get_meeting_context(channel_id)[-top_k:]

        return [
            self._format_meeting_summary(docs[mid])
            for mid in ordered_meeting_ids
            if mid in docs
        ]

    def _format_meeting_summary(self, meeting: dict) -> str:
        """Format a MongoDB meeting document into a readable summary."""
        participants = meeting.get("participants", [])
        decisions = meeting.get("decisions", [])
        action_items = meeting.get("action_items", [])
        blockers = meeting.get("blockers", [])
        standups = meeting.get("standups", {})
        ended_at = meeting.get("ended_at", "")
        duration_min = meeting.get("duration_min", 0)
        topics = meeting.get("topics", [])

        lines = [f"[MEETING — {ended_at} | {duration_min} min]"]
        lines.append(f"Participants: {', '.join(participants) or 'unknown'}")

        if topics:
            lines.append(f"Topics: {', '.join(topics)}")

        if decisions:
            lines.append("Decisions:")
            for d in decisions:
                lines.append(f"  - {d}")

        if action_items:
            lines.append("Action items:")
            for ai_item in action_items:
                owner = ai_item.get("owner", "?")
                text = ai_item.get("text", "")
                task_id = ai_item.get("task_id")
                task_ref = f" (→ {task_id})" if task_id else ""
                lines.append(f"  - [{owner}] {text}{task_ref}")

        if blockers:
            lines.append("Blockers:")
            for b in blockers:
                owner = b.get("owner", "?")
                text = b.get("text", "")
                lines.append(f"  - [{owner}] {text}")

        if standups:
            lines.append("Standups:")
            for person, data in standups.items():
                if isinstance(data, dict):
                    yesterday = data.get("yesterday", [])
                    today = data.get("today", [])
                    person_blockers = data.get("blockers", [])
                    lines.append(f"  - {person}:")
                    if yesterday:
                        lines.append(f"    Yesterday: {'; '.join(yesterday)}")
                    if today:
                        lines.append(f"    Today: {'; '.join(today)}")
                    if person_blockers:
                        lines.append(f"    Blockers: {'; '.join(person_blockers)}")

        return "\n".join(lines)

    # ── Meeting persistence (write path) ──────────────────────────────────────

    def save_meeting(self, event: dict, project_key: str | None = None, channel_id: str | None = None) -> None:
        """
        Persist a meeting.ended event to MongoDB.
        Called by MeetingMemoryInjector after injecting into channel memory.

        project_key: the Taiga/PM project this channel is mapped to (resolved
        by the caller from channel_mappings config). Memory is scoped by
        project — not just channel — so a decision made in one channel is
        recallable from any other channel mapped to the same project.

        channel_id: the *Discord text channel* this meeting's memory should
        be attached to. IMPORTANT: `event["channelId"]` is the *voice*
        channel the meeting happened in, not the text channel the bot reads
        from — passing it straight through here (as earlier code did) silently
        breaks every text_channel_id lookup (get_meeting_context, search
        filters) because they're keyed by the real text channel. Callers
        (MeetingMemoryInjector) resolve the voice→text mapping and must pass
        the resolved text channel id explicitly.
        """
        meeting_id = event.get("meetingId", "unknown")
        summary = event.get("summary", {})
        duration_ms = event.get("durationMs", 0)
        resolved_channel_id = channel_id or event.get("channelId", "")

        participants = [p.get("name", "?") for p in event.get("participants", [])]
        full_transcript = summary.get("fullTranscript", [])
        tasks_created = summary.get("tasksCreated", [])
        tasks_closed = summary.get("tasksClosed", [])

        # Parse standup data from transcript (if standup format detected)
        standups = self._parse_standups_from_transcript(full_transcript, participants)

        doc = {
            "meeting_id": meeting_id,
            "text_channel_id": resolved_channel_id,
            "project_key": project_key or "",
            "started_at": event.get("startedAt", 0),
            "ended_at": event.get("endedAt", 0),
            "duration_min": round(duration_ms / 60_000, 1),
            "participants": participants,
            "transcript": [
                {
                    "speaker": entry.get("speakerName", "Unknown"),
                    "text": entry.get("text", ""),
                    "ts": entry.get("timestamp", 0),
                    "role": entry.get("role", "user"),
                }
                for entry in full_transcript
            ],
            "standups": standups,
            "tasks_created": tasks_created,
            "tasks_closed": tasks_closed,
            "decisions": [],       # Populated by consolidation worker
            "action_items": [],    # Populated by consolidation worker
            "blockers": [],        # Populated by consolidation worker
            "topics": [],          # Populated by consolidation worker
            "consolidated": False,
            "stored_at": datetime.now(timezone.utc),
        }

        try:
            self._mongo.meetings.insert_one(doc)
            logger.info("Meeting %s persisted to MongoDB (%d transcript lines)",
                        meeting_id, len(full_transcript))
        except Exception as e:
            logger.error("Failed to persist meeting %s to MongoDB: %s", meeting_id, e)

        # Also store raw transcript in Redis for quick access (24h TTL)
        self._store_meeting_transcript_redis(meeting_id, full_transcript)

        # Embed and index the raw transcript for semantic search right away —
        # don't wait for the (delayed) consolidation pass, so "what did we
        # just talk about" works immediately after a meeting ends. The
        # consolidation worker later adds higher-signal chunks (decisions,
        # action items, blockers) on top of these.
        self._embed_transcript_chunks(meeting_id, resolved_channel_id, project_key, doc["ended_at"], full_transcript)

    def _embed_transcript_chunks(
        self,
        meeting_id: str,
        channel_id: str,
        project_key: str | None,
        ended_at: int,
        transcript: list[dict],
    ) -> None:
        """Chunk the raw transcript and store embeddings in `meeting_chunks`
        for semantic search. No-op if no embedding provider is configured —
        keeps this purely additive on top of keyword/regex search."""
        if not (self._embeddings and self._embeddings.available) or not transcript:
            return

        full_text = "\n".join(
            f"[{entry.get('speakerName', 'Unknown')}]: {entry.get('text', '')}"
            for entry in transcript
            if entry.get("text", "").strip()
        )
        chunks = chunk_text(full_text, self._chunk_tokens, self._chunk_overlap_tokens)
        if not chunks:
            return

        vectors = self._embeddings.embed_documents(chunks)
        if not vectors or len(vectors) != len(chunks):
            logger.warning("Embedding generation returned mismatched results for meeting %s", meeting_id)
            return

        try:
            docs = [
                {
                    "meeting_id": meeting_id,
                    "channel_id": channel_id,
                    "project_key": project_key or "",
                    "kind": "transcript_chunk",
                    "chunk_index": i,
                    "text": chunk,
                    "embedding": vector,
                    "ended_at": ended_at,
                    "created_at": datetime.now(timezone.utc),
                }
                for i, (chunk, vector) in enumerate(zip(chunks, vectors))
            ]
            self._mongo.meeting_chunks.insert_many(docs)
            logger.info("Indexed %d transcript chunk(s) for meeting %s", len(docs), meeting_id)
        except Exception as e:
            logger.warning("Failed to index transcript chunks for meeting %s: %s", meeting_id, e)

    def _store_meeting_transcript_redis(self, meeting_id: str, transcript: list) -> None:
        """Store raw transcript in Redis with 24h TTL for quick recall."""
        key = f"meeting:{meeting_id}:transcript"
        try:
            pipe = self._redis.pipeline()
            for entry in transcript:
                pipe.rpush(key, json.dumps({
                    "speaker": entry.get("speakerName", "Unknown"),
                    "text": entry.get("text", ""),
                    "ts": entry.get("timestamp", 0),
                }))
            pipe.expire(key, self._meeting_ttl)
            pipe.execute()
        except Exception as e:
            logger.warning("Failed to store transcript in Redis: %s", e)

    def _parse_standups_from_transcript(
        self, transcript: list, participants: list
    ) -> dict:
        """
        Extract standup data from transcript if it follows the standup format.
        Returns a dict like {participant_name: {yesterday: [...], today: [...], blockers: [...]}}.
        """
        standups = {}
        for name in participants:
            standups[name] = {"yesterday": [], "today": [], "blockers": []}

        # Simple heuristic: look for standup keywords in transcript
        current_speaker = None
        for entry in transcript:
            speaker = entry.get("speakerName", "")
            text = entry.get("text", "").lower().strip()
            if speaker in standups:
                current_speaker = speaker
            if current_speaker and current_speaker in standups:
                if "yesterday" in text or "what i did" in text:
                    standups[current_speaker]["yesterday"].append(entry.get("text", ""))
                elif "today" in text or "what i will" in text or "going to" in text:
                    standups[current_speaker]["today"].append(entry.get("text", ""))
                elif "blocker" in text or "blocked" in text or "issue" in text:
                    standups[current_speaker]["blockers"].append(entry.get("text", ""))

        return standups

    def get_meeting_transcript(self, meeting_id: str) -> list[dict]:
        """Read raw transcript from Redis for deep recall."""
        key = f"meeting:{meeting_id}:transcript"
        try:
            raw_list = self._redis.lrange(key, 0, -1)
            return [json.loads(r) for r in raw_list]
        except Exception as e:
            logger.warning("Redis get transcript failed for %s: %s", meeting_id, e)
            return []

    def search_meetings(self, query: str, project_key: str | None = None) -> list[dict]:
        """
        Hybrid search over meeting memory: exact/keyword matching (regex,
        safely escaped) merged with semantic similarity search over embedded
        transcript/decision/action-item chunks (when embeddings are
        configured). Keyword search alone misses paraphrases ("we agreed to
        use OAuth" won't match a query for "auth decision"); semantic search
        alone misses exact identifiers (ticket IDs, names). Combining both
        and deduplicating by meeting gives better recall than either alone.
        Returns matching meeting summaries, each optionally annotated with
        `matched_chunks` (best semantic excerpts) when semantic search ran.
        """
        query = (query or "").strip()
        if not query:
            return []
        # Cap length and escape before it ever reaches $regex — untrusted
        # input (ultimately from chat) must never be interpolated raw into a
        # regex (ReDoS / unexpectedly expensive scans).
        safe_query = re.escape(query[:200])

        keyword_meetings: dict[str, dict] = {}
        try:
            filter_query: dict = {"consolidated": True}
            if project_key:
                filter_query["project_key"] = project_key
            filter_query["$or"] = [
                {"transcript.text": {"$regex": safe_query, "$options": "i"}},
                {"decisions": {"$regex": safe_query, "$options": "i"}},
                {"topics": {"$regex": safe_query, "$options": "i"}},
            ]
            for m in self._mongo.meetings.find(filter_query).sort("ended_at", -1).limit(5):
                keyword_meetings[m.get("meeting_id", str(m.get("_id")))] = m
        except Exception as e:
            logger.warning("MongoDB keyword search_meetings failed: %s", e)

        semantic_hits: list[dict] = []
        if self._embeddings and self._embeddings.available:
            query_vector = self._embeddings.embed_query(query)
            if query_vector:
                try:
                    chunk_filter: dict = {}
                    if project_key:
                        chunk_filter["project_key"] = project_key
                    candidates = list(
                        self._mongo.meeting_chunks.find(chunk_filter)
                        .sort("ended_at", -1)
                        .limit(500)
                    )
                    semantic_hits = rank_by_similarity(query_vector, candidates, top_k=8)
                except Exception as e:
                    logger.warning("MongoDB semantic search_meetings failed: %s", e)

        # Merge: hydrate any meetings the semantic pass found that keyword
        # search missed, and attach matched excerpts to meetings found by
        # either path.
        chunks_by_meeting: dict[str, list[dict]] = {}
        missing_meeting_ids = set()
        for chunk in semantic_hits:
            mid = chunk.get("meeting_id")
            if not mid:
                continue
            chunks_by_meeting.setdefault(mid, []).append(chunk)
            if mid not in keyword_meetings:
                missing_meeting_ids.add(mid)

        if missing_meeting_ids:
            try:
                for m in self._mongo.meetings.find({"meeting_id": {"$in": list(missing_meeting_ids)}}):
                    keyword_meetings[m.get("meeting_id", str(m.get("_id")))] = m
            except Exception as e:
                logger.warning("MongoDB hydrate semantic hits failed: %s", e)

        results = []
        for mid, meeting in keyword_meetings.items():
            meeting = dict(meeting)
            if mid in chunks_by_meeting:
                meeting["matched_chunks"] = [
                    {"kind": c.get("kind"), "text": c.get("text"), "score": round(c.get("_score", 0), 3)}
                    for c in sorted(chunks_by_meeting[mid], key=lambda c: c.get("_score", 0), reverse=True)[:3]
                ]
            results.append(meeting)

        results.sort(key=lambda m: m.get("ended_at", 0), reverse=True)
        return results[:5]

    def get_project_decisions(self, project_key: str) -> list[dict]:
        """Get recent decisions from consolidated meetings for a project."""
        try:
            meetings = list(
                self._mongo.meetings.find(
                    {"project_key": project_key, "consolidated": True, "decisions": {"$ne": []}}
                )
                .sort("ended_at", -1)
                .limit(5)
            )
            decisions = []
            for m in meetings:
                for d in m.get("decisions", []):
                    decisions.append({
                        "decision": d,
                        "meeting_id": m.get("meeting_id"),
                        "date": m.get("ended_at"),
                    })
            return decisions[:10]
        except Exception as e:
            logger.warning("MongoDB get_project_decisions failed: %s", e)
            return []

    # ── Reconciled project state (open action items / durable facts) ───────────
    # Backed by `project_context` (maintained by ConsolidationWorker, which
    # reconciles — not just appends — as items get resolved) and
    # `project_facts` (durable, project-scoped facts independent of any one
    # meeting or conversation).

    def get_action_items(
        self, project_key: str, owner: str | None = None, status: str = "open"
    ) -> list[dict[str, Any]]:
        """Return tracked action items for a project. `status='open'` reads
        the reconciled open_action_items list (items the consolidation
        worker hasn't seen marked resolved in a later meeting); any other
        status value returns everything MongoDB has, unfiltered by status,
        since there's currently no separate closed-items archive."""
        try:
            ctx = self._mongo.project_context.find_one({"_id": project_key})
        except Exception as e:
            logger.warning("MongoDB get_action_items failed: %s", e)
            return []
        if not ctx:
            return []
        items = ctx.get("open_action_items", [])
        if owner:
            owner_lower = owner.strip().lower()
            items = [
                i for i in items
                if owner_lower in (i.get("owner") or "").lower()
            ]
        return items

    def remember_fact(self, project_key: str, fact: str, source: str = "chat") -> None:
        """Persist a durable, project-scoped fact outside any single
        conversation or meeting (e.g. something a user tells the bot in
        chat that should be recalled later, not just this session)."""
        fact = (fact or "").strip()
        if not fact or not project_key:
            return
        doc: dict[str, Any] = {
            "project_key": project_key,
            "fact": fact,
            "source": source,
            "created_at": datetime.now(timezone.utc),
            "superseded": False,
        }
        if self._embeddings and self._embeddings.available:
            vector = self._embeddings.embed_query(fact)
            if vector:
                doc["embedding"] = vector
        try:
            self._mongo.project_facts.insert_one(doc)
        except Exception as e:
            logger.warning("MongoDB remember_fact failed: %s", e)

    def recall_facts(
        self, project_key: str, topic: str | None = None, limit: int = 10
    ) -> list[dict[str, Any]]:
        """Retrieve durable project facts, ranked by relevance to `topic`
        when embeddings are available, else most recent first. Superseded
        facts (explicitly contradicted by a later meeting/consolidation) are
        excluded so stale info doesn't resurface."""
        try:
            base_filter = {"project_key": project_key, "superseded": {"$ne": True}}
            if topic and self._embeddings and self._embeddings.available:
                query_vector = self._embeddings.embed_query(topic)
                if query_vector:
                    candidates = list(
                        self._mongo.project_facts.find(base_filter).limit(300)
                    )
                    return rank_by_similarity(query_vector, candidates, top_k=limit)

            filter_query = dict(base_filter)
            if topic:
                filter_query["fact"] = {"$regex": re.escape(topic[:200]), "$options": "i"}
            return list(
                self._mongo.project_facts.find(filter_query)
                .sort("created_at", -1)
                .limit(limit)
            )
        except Exception as e:
            logger.warning("MongoDB recall_facts failed: %s", e)
            return []

    # ── Channel Chat Persistence & Retrieval ─────────────────────────────────

    def save_chat_message(self, message_doc: dict[str, Any]) -> None:
        """Persist a raw Discord/Slack channel chat message to MongoDB and index its embedding."""
        if not message_doc or not message_doc.get("content"):
            return
        doc = {
            **message_doc,
            "stored_at": datetime.now(timezone.utc),
            "indexed": False,
        }
        try:
            res = self._mongo.channel_messages.insert_one(doc)
            msg_id = str(res.inserted_id)

            # Real-time embedding indexing if provider is available
            if self._embeddings and self._embeddings.available:
                content = message_doc.get("content", "").strip()
                if content:
                    author = message_doc.get("author_name", "User")
                    ch_name = message_doc.get("channel_name", "channel")
                    formatted_text = f"[{author} in #{ch_name}]: {content}"
                    vector = self._embeddings.embed_query(formatted_text)
                    if vector:
                        chunk_doc = {
                            "chunk_id": msg_id,
                            "message_id": message_doc.get("message_id", ""),
                            "channel_id": message_doc.get("channel_id", ""),
                            "channel_name": ch_name,
                            "project_key": message_doc.get("project_key", ""),
                            "org_id": message_doc.get("org_id") or "default",
                            "author_name": author,
                            "text": formatted_text,
                            "embedding": vector,
                            "created_at": message_doc.get("created_at") or datetime.now(timezone.utc).isoformat(),
                        }
                        self._mongo.chat_chunks.insert_one(chunk_doc)
                        self._mongo.channel_messages.update_one(
                            {"_id": res.inserted_id},
                            {"$set": {"indexed": True, "indexed_at": datetime.now(timezone.utc)}}
                        )
        except Exception as e:
            logger.warning("Failed to save channel chat message: %s", e)

    def get_recent_channel_messages(self, channel_id: str, limit: int = 20) -> list[dict[str, Any]]:
        """Fetch the most recent chat messages from a specific channel."""
        try:
            return list(
                self._mongo.channel_messages.find({"channel_id": str(channel_id)})
                .sort("created_at", -1)
                .limit(limit)
            )
        except Exception as e:
            logger.warning("MongoDB get_recent_channel_messages failed: %s", e)
            return []

    def search_chat_messages(
        self, query: str, project_key: str, channel_id: str | None = None, top_k: int = 5
    ) -> list[dict[str, Any]]:
        """
        Hybrid search over past channel text chats:
        Exact regex/keyword matching combined with semantic vector search over chat_chunks.
        """
        query = (query or "").strip()
        if not query:
            return []
        safe_query = re.escape(query[:200])

        results_map: dict[str, dict] = {}

        # 1. Keyword / Regex search across channel_messages
        try:
            filter_query: dict[str, Any] = {
                "project_key": project_key,
                "content": {"$regex": safe_query, "$options": "i"},
            }
            if channel_id:
                filter_query["channel_id"] = str(channel_id)

            for msg in self._mongo.channel_messages.find(filter_query).sort("created_at", -1).limit(top_k * 2):
                msg_id = msg.get("message_id", str(msg.get("_id")))
                results_map[msg_id] = {
                    "author_name": msg.get("author_name", "Team Member"),
                    "content": msg.get("content", ""),
                    "channel_name": msg.get("channel_name", ""),
                    "created_at": msg.get("created_at", ""),
                }
        except Exception as e:
            logger.warning("MongoDB keyword search_chat_messages failed: %s", e)

        # 2. Semantic search across chat_chunks if embeddings configured
        if self._embeddings and self._embeddings.available:
            query_vector = self._embeddings.embed_query(query)
            if query_vector:
                try:
                    chunk_filter: dict[str, Any] = {"project_key": project_key}
                    if channel_id:
                        chunk_filter["channel_id"] = str(channel_id)
                    candidates = list(
                        self._mongo.chat_chunks.find(chunk_filter).sort("created_at", -1).limit(300)
                    )
                    semantic_hits = rank_by_similarity(query_vector, candidates, top_k=top_k)
                    for hit in semantic_hits:
                        hit_id = hit.get("chunk_id", str(hit.get("_id")))
                        results_map[hit_id] = {
                            "author_name": hit.get("author_name", "Team"),
                            "content": hit.get("text", ""),
                            "channel_name": hit.get("channel_name", ""),
                            "created_at": hit.get("created_at", ""),
                            "score": round(hit.get("_score", 0), 3),
                        }
                except Exception as e:
                    logger.warning("MongoDB semantic search_chat_messages failed: %s", e)

        formatted = list(results_map.values())
        return formatted[:top_k]

    # ── Voice Meeting Schedules & Live Operations ────────────────────────────

    def create_scheduled_meeting(
        self, schedule_input: dict[str, Any], org_id: str = "default"
    ) -> dict[str, Any] | None:
        """Create a scheduled standup/meeting in MongoDB scheduled_meetings."""
        now = datetime.now(timezone.utc)
        doc = {
            "orgId": org_id,
            "title": schedule_input.get("title", "Daily Standup"),
            "provider": schedule_input.get("provider", "discord"),
            "guildId": str(schedule_input.get("guildId", "")),
            "channelId": str(schedule_input.get("channelId", "")),
            "guildName": schedule_input.get("guildName", ""),
            "channelName": schedule_input.get("channelName", ""),
            "recurrence": schedule_input.get("recurrence", "daily"),
            "time": schedule_input.get("time", "10:00"),
            "timezone": schedule_input.get("timezone", "UTC"),
            "daysOfWeek": schedule_input.get("daysOfWeek", [1, 2, 3, 4, 5]),
            "date": schedule_input.get("date"),
            "durationMs": schedule_input.get("durationMs", 15 * 60 * 1000),
            "enabled": schedule_input.get("enabled", True),
            "lastRunAt": None,
            "lastRunDateKey": None,
            "lastStatus": "idle",
            "createdAt": now,
            "updatedAt": now,
        }
        try:
            res = self._mongo.scheduled_meetings.insert_one(doc)
            doc["id"] = str(res.inserted_id)
            return doc
        except Exception as e:
            logger.error("Failed to create scheduled meeting in MongoDB: %s", e)
            return None

    def list_scheduled_meetings(
        self, org_id: str = "default", guild_id: str | None = None
    ) -> list[dict[str, Any]]:
        """List active scheduled meetings for an org and optionally guild."""
        query: dict[str, Any] = {"orgId": org_id}
        if guild_id:
            query["guildId"] = str(guild_id)
        try:
            docs = list(self._mongo.scheduled_meetings.find(query).sort("createdAt", -1))
            results = []
            for d in docs:
                results.append({
                    "id": str(d.get("_id")),
                    "title": d.get("title", "Standup"),
                    "recurrence": d.get("recurrence", "daily"),
                    "time": d.get("time", "10:00"),
                    "timezone": d.get("timezone", "UTC"),
                    "daysOfWeek": d.get("daysOfWeek", []),
                    "channelName": d.get("channelName") or d.get("channelId", ""),
                    "channelId": d.get("channelId", ""),
                    "enabled": d.get("enabled", True),
                    "lastStatus": d.get("lastStatus", "idle"),
                })
            return results
        except Exception as e:
            logger.warning("Failed to list scheduled meetings: %s", e)
            return []

    def delete_scheduled_meeting(
        self, schedule_id: str, org_id: str = "default"
    ) -> bool:
        """Delete a scheduled meeting by ID and org."""
        try:
            try:
                from bson import ObjectId
                query: dict[str, Any] = {"orgId": org_id, "_id": ObjectId(schedule_id)}
            except Exception:
                query = {"orgId": org_id, "_id": str(schedule_id)}
            res = self._mongo.scheduled_meetings.delete_one(query)
            if res and getattr(res, "deleted_count", 0) > 0:
                return True
            res2 = self._mongo.scheduled_meetings.delete_one({"orgId": org_id, "_id": str(schedule_id)})
            return bool(res2 and getattr(res2, "deleted_count", 0) > 0)
        except Exception as e:
            logger.warning("Failed to delete scheduled meeting: %s", e)
            return False

    def start_voice_meeting(
        self,
        guild_id: str,
        channel_id: str,
        org_id: str = "default",
        duration_ms: int = 1800000,
        project_slug: str | None = None,
        text_channel_id: str | None = None,
    ) -> dict[str, Any]:
        """Trigger an on-demand voice meeting via the voice service API."""
        voice_url = os.environ.get("SCRUM_MASTER_AI_URL", "http://localhost:3001")
        endpoint = f"{voice_url.rstrip('/')}/integrations/discord/meetings/start"
        body: dict[str, Any] = {
            "guildId": str(guild_id),
            "channelId": str(channel_id),
            "textChannelId": str(text_channel_id or channel_id),
            "durationMs": duration_ms,
        }
        if project_slug:
            body["projectSlug"] = str(project_slug)
        payload = json.dumps(body).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "x-org-id": org_id,
        }
        service_key = os.environ.get("SERVICE_API_KEY", "")
        if service_key:
            headers["Authorization"] = f"Bearer {service_key}"
        internal_key = os.environ.get("INTERNAL_SERVICE_KEY") or os.environ.get("AUTH_SERVICE_INTERNAL_KEY", "")
        if internal_key:
            headers["x-internal-key"] = internal_key
        req = urllib.request.Request(
            endpoint,
            data=payload,
            headers=headers,
        )
        try:
            with urllib.request.urlopen(req, timeout=12) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data
        except urllib.error.HTTPError as e:
            err_msg = str(e)
            try:
                body = e.read().decode("utf-8")
                err_json = json.loads(body)
                err_msg = err_json.get("error") or err_json.get("message") or err_msg
            except Exception:
                pass
            logger.warning("Failed to start voice meeting via HTTP API (%s): %s", endpoint, err_msg)
            return {"started": False, "error": err_msg}
        except Exception as e:
            logger.warning("Failed to start voice meeting via HTTP API (%s): %s", endpoint, e)
            return {"started": False, "error": str(e)}

    def stop_voice_meeting(
        self, guild_id: str, org_id: str = "default"
    ) -> dict[str, Any]:
        """Stop an active voice meeting via the voice service API."""
        voice_url = os.environ.get("SCRUM_MASTER_AI_URL", "http://localhost:3001")
        endpoint = f"{voice_url.rstrip('/')}/integrations/discord/meetings/stop"
        payload = json.dumps({"guildId": str(guild_id)}).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "x-org-id": org_id,
        }
        service_key = os.environ.get("SERVICE_API_KEY", "")
        if service_key:
            headers["Authorization"] = f"Bearer {service_key}"
        internal_key = os.environ.get("INTERNAL_SERVICE_KEY") or os.environ.get("AUTH_SERVICE_INTERNAL_KEY", "")
        if internal_key:
            headers["x-internal-key"] = internal_key
        req = urllib.request.Request(
            endpoint,
            data=payload,
            headers=headers,
        )
        try:
            with urllib.request.urlopen(req, timeout=12) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data
        except urllib.error.HTTPError as e:
            err_msg = str(e)
            try:
                body = e.read().decode("utf-8")
                err_json = json.loads(body)
                err_msg = err_json.get("error") or err_json.get("message") or err_msg
            except Exception:
                pass
            logger.warning("Failed to stop voice meeting via HTTP API (%s): %s", endpoint, err_msg)
            return {"stopped": False, "error": err_msg}
        except Exception as e:
            logger.warning("Failed to stop voice meeting via HTTP API (%s): %s", endpoint, e)
            return {"stopped": False, "error": str(e)}


# ── ReAct tool-calling loop ───────────────────────────────────────────────────

def _run_agent_loop(
    llm_with_tools,
    tools_by_name: dict[str, BaseTool],
    messages: list[BaseMessage],
    max_iterations: int = 8,
) -> tuple[str, list[BaseMessage]]:
    """
    LangChain 1.x native ReAct loop:
      1. Call LLM with current message list
      2. If response has tool_calls → execute each tool, append ToolMessage results
      3. Repeat until no tool_calls or max_iterations reached
    Returns (final_text_reply, new_messages_to_store)
    """
    new_messages: list[BaseMessage] = []
    iteration = 0

    while iteration < max_iterations:
        iteration += 1
        response: AIMessage = llm_with_tools.invoke(messages + new_messages)

        if not response.tool_calls:
            # No tool calls — this is the final answer
            from core.base import extract_text_content
            final = extract_text_content(response.content) or "I wasn't able to complete that request."
            new_messages.append(response)
            return final, new_messages

        # Execute all tool calls in this step
        new_messages.append(response)
        for tc in response.tool_calls:
            tool_name = tc["name"]
            tool_args = tc["args"]
            tool_id   = tc["id"]

            logger.info("Tool call: %s(%s)", tool_name, tool_args)

            tool_fn = tools_by_name.get(tool_name)
            if tool_fn is None:
                tool_result = f"Error: tool '{tool_name}' not found."
            else:
                try:
                    tool_result = tool_fn.invoke(tool_args)
                    if not isinstance(tool_result, str):
                        tool_result = str(tool_result)
                except Exception as e:
                    tool_result = f"Error executing {tool_name}: {e}"
                    logger.error("Tool %s failed: %s", tool_name, e)

            logger.info("Tool result: %s", tool_result[:200])
            new_messages.append(ToolMessage(content=tool_result, tool_call_id=tool_id))

    # Max iterations reached
    return "I reached the maximum number of steps. Please try a simpler request.", new_messages


# ── Main agent orchestrator ────────────────────────────────────────────────────

class AgentBridge:
    """Full pipeline from IncomingMessage to OutgoingMessage."""

    def __init__(
        self,
        comm_platform: CommunicationPlatform,
        pm_platform: ProjectManagementPlatform,
        gemini_api_key: str,
        agent_model: str = "gemini-3.6-flash",
        classifier_model: str = "gemini-3.6-flash",
        max_iterations: int = 8,
        memory_max_tokens: int = 2000,
        memory_store: MemoryStore | None = None,
        identity_client: IdentityClient | None = None,
        strict_identity: bool | None = None,
    ):
        self.comm = comm_platform
        self.pm   = pm_platform
        self._identity_client = identity_client
        self.strict_identity: bool = (
            strict_identity
            if strict_identity is not None
            else os.environ.get("STRICT_IDENTITY_ENFORCEMENT", "true").lower() in ("true", "1", "yes")
        )

        self._router  = IntentRouter(gemini_api_key, classifier_model)
        self._memory  = memory_store or ChannelMemoryStore(max_messages=30)
        self._llm     = ChatGoogleGenerativeAI(
            model=agent_model, google_api_key=gemini_api_key, temperature=0)
        self._max_iter = max_iterations
        self._context  = ContextAssembler(total_budget_tokens=memory_max_tokens)

        self._project_id_cache: dict[str, str] = {}

    def record_chat_message(self, message_doc: dict[str, Any]) -> None:
        """Enrich incoming raw chat message with identity (workspace uuid as org_id) and persist."""
        if not message_doc or not self._memory:
            return

        author_id = message_doc.get("author_id")
        guild_id = message_doc.get("guild_id")
        channel_id = message_doc.get("channel_id")

        if self._identity_client and self._identity_client.is_configured() and author_id:
            try:
                id_res = self._identity_client.resolve_discord_identity(
                    external_id=author_id,
                    guild_id=guild_id,
                    channel_id=channel_id,
                )
                if id_res and id_res.org_id:
                    message_doc["org_id"] = id_res.org_id
                if id_res and id_res.project_slug and not message_doc.get("project_key"):
                    message_doc["project_key"] = id_res.project_slug
            except Exception as e:
                logger.debug("Could not resolve author identity for chat record: %s", e)

        if not message_doc.get("org_id"):
            message_doc["org_id"] = getattr(self.comm, "_org_id", "") or "default"

        if hasattr(self._memory, "save_chat_message"):
            self._memory.save_chat_message(message_doc)

    async def handle(self, incoming: IncomingMessage) -> OutgoingMessage:
        logger.info("[%s] %s: %s",
                    incoming.channel_id, incoming.author_name, incoming.content[:100])

        # ── 0. Identity & Entitlement Verification (Root Backend) ────────────
        id_result = None
        if self._identity_client and self._identity_client.is_configured():
            try:
                id_result = self._identity_client.resolve_discord_identity(
                    external_id=incoming.author_id,
                    guild_id=incoming.server_id,
                    channel_id=incoming.channel_id,
                )
                if not id_result.linked:
                    return OutgoingMessage(
                        channel_id=incoming.channel_id,
                        content=(
                            "⚠️ **Identity Not Linked**\n"
                            "Your Discord account is not linked to any project workspace.\n"
                            "Please link your Discord account in the CoordinaAI dashboard (Settings → Integrations).\n"
                            f"Discord User ID: `{incoming.author_id}`"
                        ),
                    )
                # if not id_result.has_subscription:
                #     return OutgoingMessage(
                #         channel_id=incoming.channel_id,
                #         content=(
                #             "⚠️ **Active Subscription Required**\n"
                #             f"Workspace **{id_result.company_name or 'Default'}** does not have an active subscription.\n"
                #             "Please activate or upgrade your plan in the CoordinaAI dashboard."
                #         ),
                #     )
            except Exception as e:
                logger.error("Identity resolution check failed: %s", e)
                if self.strict_identity:
                    return OutgoingMessage(
                        channel_id=incoming.channel_id,
                        content=(
                            "⚠️ **Identity Service Temporarily Unavailable**\n"
                            "Could not verify your workspace account authorization with the central server.\n"
                            "To protect AI token quotas, requests cannot proceed while identity verification is offline. Please try again shortly."
                        ),
                    )
                logger.warning(
                    "Identity resolution check failed: %s — continuing with local configuration fallback (STRICT_IDENTITY_ENFORCEMENT=false)", e
                )
        elif self.strict_identity:
            return OutgoingMessage(
                channel_id=incoming.channel_id,
                content=(
                    "🔒 **Workspace Identity Required**\n"
                    "Central identity verification is strictly enforced to protect AI token quotas, but the identity service is not configured.\n"
                    "Please configure `BACKEND_URL` and `SERVICE_API_KEY`."
                ),
            )

        # ── 0b. Dynamically apply PM credentials if provided by workspace ───
        if self._identity_client and id_result and hasattr(self.pm, "configure"):
            try:
                taiga_creds = self._identity_client.get_taiga_credentials(id_result)
                if taiga_creds:
                    current_pm_cfg = dict(getattr(self.pm, "_config", {}))
                    current_pm_cfg["url"] = (
                        taiga_creds.get("instance_url")
                        or taiga_creds.get("url")
                        or current_pm_cfg.get("url")
                        or "https://api.taiga.io/api/v1"
                    )
                    if taiga_creds.get("username"):
                        current_pm_cfg["username"] = taiga_creds["username"]
                    if taiga_creds.get("password"):
                        current_pm_cfg["password"] = taiga_creds["password"]
                    if taiga_creds.get("access_token"):
                        current_pm_cfg["token"] = taiga_creds["access_token"]
                    self.pm.configure(current_pm_cfg)
                    logger.info("Bound workspace '%s' Taiga credentials dynamically", id_result.company_name)
            except Exception as e:
                logger.warning(
                    "Could not apply dynamic Taiga credentials from workspace '%s': %s (using local PM configuration)",
                    getattr(id_result, "company_name", "Unknown"),
                    e,
                )

        # ── 1. Resolve project ───────────────────────────────────────────────
        project_key = None
        if id_result and id_result.project_slug:
            project_key = id_result.project_slug
            logger.info("Dynamically resolved project slug '%s' from root backend identity", project_key)
        elif self._identity_client and id_result:
            discovered = self._identity_client.discover_active_project(id_result)
            if discovered:
                project_key = discovered.get("project_slug") or discovered.get("project_id")
                logger.info("Dynamically discovered Taiga project '%s' via Taiga API", project_key)

        if not project_key:
            project_key = self.comm.resolve_project_key(
                incoming.server_id, incoming.channel_id)
        if not project_key:
            return OutgoingMessage(
                channel_id=incoming.channel_id,
                content=(
                    "⚠️ This channel is not linked to a Taiga project.\n"
                    "Ask an admin to configure it in the Agent Bridge dashboard.\n"
                    f"Channel ID: `{incoming.channel_id}` | Server ID: `{incoming.server_id}`"
                ),
            )

        project_id = project_key
        pm_available = True
        try:
            project_id = self._get_project_id(project_key)
        except Exception as e:
            logger.warning(
                "Could not resolve PM platform project '%s': %s — PM tools may be unavailable, but meeting, scheduling, and memory tools will function.",
                project_key, e,
            )
            pm_available = False

        # ── 2. RBAC ──────────────────────────────────────────────────────────
        tier = self.comm.get_permission_tier(incoming.author_roles)
        logger.info("User %s roles=%s → tier=%s", incoming.author_name, incoming.author_roles, tier)

        if tier == "none":
            return OutgoingMessage(
                channel_id=incoming.channel_id,
                content="🚫 You don't have permission to use this bot. Contact your Project Manager.",
            )

        # ── 3. Intent routing ────────────────────────────────────────────────
        intent = self._router.classify(incoming.content)
        logger.info("Intent: %s | resource: %s | needs_write: %s | confidence: %s",
                    intent.get("intent"), intent.get("resource"),
                    intent.get("needs_write"), intent.get("confidence"))

        if intent.get("needs_write") and tier == "read":
            return OutgoingMessage(
                channel_id=incoming.channel_id,
                content="🚫 You have **read-only** access and cannot create, update, or close items.",
            )

        # ── 4. Project context ───────────────────────────────────────────────
        ctx: ProjectContext | None = None
        if pm_available:
            try:
                ctx = self.pm.get_project_context(project_id)
            except Exception as e:
                logger.warning("Could not fetch project context: %s", e)

        # ── 5. Build tools and LLM ───────────────────────────────────────────
        org_id = (
            (id_result.org_id if id_result else None)
            or (incoming.metadata.get("org_id") if incoming.metadata else None)
            or "default"
        )
        tools = build_tools(
            self.pm,
            project_id,
            tier,
            memory_store=self._memory,
            project_key=project_key,
            guild_id=incoming.server_id,
            channel_id=incoming.channel_id,
            channel_name=incoming.channel_name,
            org_id=org_id,
        )
        try:
            from agent.mcp_client import build_mcp_tools
            auth_context = {
                "user_id": incoming.author_id,
                "role": tier,
                "org_id": org_id,
                "guild_id": incoming.server_id,
                "channel_id": incoming.channel_id,
                "project_key": project_key,
            }
            mcp_tools = build_mcp_tools(auth_context)
            tools = mcp_tools + tools
        except Exception as e:
            logger.warning("Could not initialize MCP tools: %s", e)
        tools_by_name = {t.name: t for t in tools}
        llm_with_tools = self._llm.bind_tools(tools)

        member_list = ", ".join(
            f"{m['username']} ({m.get('role', '')})"
            for m in (ctx.members if ctx else [])
        ) or "No member data available"

        # Query-aware: rank meeting summaries by relevance to what the user
        # actually asked, instead of always injecting the last 3 regardless
        # of topic. Falls back to recency automatically when embeddings
        # aren't configured or nothing scores well.
        candidate_meetings = self._memory.get_relevant_meeting_context(
            incoming.channel_id, incoming.content, project_key=project_key, top_k=3
        )

        # ── 6. Retrieve channel memory ───────────────────────────────────────
        history = self._memory.get(incoming.channel_id)
        # Meeting transcripts are surfaced through the system prompt section
        # above — drop the full SystemMessage copies from history so the same
        # transcript isn't fed through twice.
        history = [
            m for m in history
            if not (isinstance(m, SystemMessage)
                    and m.content.startswith("[MEETING CONTEXT"))
        ]

        # Fit meeting context + history into the configured token budget
        # (memory_max_tokens) instead of trusting message-count truncation
        # alone to keep the prompt under the model's context window.
        assembled = self._context.assemble(candidate_meetings, history)
        if assembled.meetings_dropped or assembled.history_dropped:
            logger.info(
                "[%s] Context budget trimmed %d meeting summar(y/ies), %d history message(s) "
                "(meeting_tokens=%d history_tokens=%d available=%d)",
                incoming.channel_id, assembled.meetings_dropped, assembled.history_dropped,
                assembled.meeting_tokens, assembled.history_tokens, self._context.available_tokens,
            )

        meetings_text = "\n\n".join(assembled.meeting_summaries) or \
            "No meeting context recorded yet for this channel."

        system_text = SYSTEM_PROMPT.format(
            comm_platform  = self.comm.display_name,
            pm_platform    = self.pm.display_name,
            project_name   = ctx.project_name if ctx else project_key,
            active_sprint  = (ctx.active_sprint or "None") if ctx else "Unknown",
            sprint_end     = (ctx.sprint_end_date or "—") if ctx else "—",
            open_tasks     = ctx.open_task_count  if ctx else "?",
            open_issues    = ctx.open_issue_count if ctx else "?",
            open_stories   = ctx.open_story_count if ctx else "?",
            members        = member_list,
            meetings       = meetings_text,
            author_name    = incoming.author_name,
            tier           = tier,
        )

        # Full message list: system + budgeted history + new user message
        all_messages: list[BaseMessage] = (
            [SystemMessage(content=system_text)]
            + assembled.history
            + [HumanMessage(content=incoming.content)]
        )

        # ── 7. Run agent loop (in worker thread to avoid blocking asyncio event loop & Discord heartbeats) ───
        try:
            reply, new_msgs = await asyncio.to_thread(
                _run_agent_loop,
                llm_with_tools, tools_by_name, all_messages, self._max_iter
            )
        except Exception as e:
            logger.exception("Agent loop failed")
            reply = f"❌ An error occurred while processing your request: {e}"
            new_msgs = []

        # ── 8. Save to memory ────────────────────────────────────────────────
        # Store user message + all agent loop messages (tool calls + final answer)
        self._memory.append(incoming.channel_id, [
            HumanMessage(content=incoming.content),
            *new_msgs,
        ])

        return OutgoingMessage(
            channel_id          = incoming.channel_id,
            content             = reply,
            reply_to_message_id = incoming.platform_message_id,
        )

    def _get_project_id(self, key: str) -> str:
        if key not in self._project_id_cache:
            self._project_id_cache[key] = self.pm.get_project_id(key)
        return self._project_id_cache[key]
