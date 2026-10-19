"""
core/embeddings.py — Semantic memory support.

Provides:
  - chunk_text(): sliding-window text chunking by token count
  - EmbeddingProvider: thin wrapper around Gemini embeddings, degrades to
    `None` (disabled) if no API key / package is available so the rest of
    the memory pipeline keeps working with regex-only search.
  - cosine_similarity(): pure-python vector similarity (no numpy dependency)

Vectors are stored as plain float lists directly on Mongo documents (in a
`meeting_chunks` collection). This works with any MongoDB (no Atlas Vector
Search required) — similarity is computed in Python over a pre-filtered
candidate set (scoped by project_key and/or recency), which is the right
tradeoff at the data volumes a single-team PM bot accumulates. If/when this
needs to scale past a few thousand chunks, swap `_brute_force_search` for an
Atlas `$vectorSearch` or an external vector DB — the interface is unchanged.
"""
from __future__ import annotations

import logging
import math
from typing import Any

from core.tokens import count_tokens

logger = logging.getLogger("agent_bridge.embeddings")


def chunk_text(text: str, chunk_tokens: int = 400, overlap_tokens: int = 60) -> list[str]:
    """
    Split text into overlapping chunks, sized by (approximate) token count.
    Splits on paragraph/line boundaries where possible to avoid cutting
    sentences mid-way, which keeps embedded chunks semantically coherent.
    """
    if not text or not text.strip():
        return []
    if count_tokens(text) <= chunk_tokens:
        return [text.strip()]

    lines = [l for l in text.split("\n") if l.strip()]
    chunks: list[str] = []
    current: list[str] = []
    current_tokens = 0

    for line in lines:
        line_tokens = count_tokens(line)
        if current and current_tokens + line_tokens > chunk_tokens:
            chunks.append("\n".join(current))
            # Build overlap from the tail of the previous chunk
            overlap: list[str] = []
            overlap_count = 0
            for prev_line in reversed(current):
                t = count_tokens(prev_line)
                if overlap_count + t > overlap_tokens:
                    break
                overlap.insert(0, prev_line)
                overlap_count += t
            current = overlap
            current_tokens = overlap_count
        current.append(line)
        current_tokens += line_tokens

    if current:
        chunks.append("\n".join(current))

    return chunks


def chunk_chat_messages(
    messages: list[dict[str, Any]],
    max_tokens: int = 350,
    overlap_messages: int = 2,
) -> list[dict[str, Any]]:
    """
    Cluster consecutive chat messages from a channel into conversational chunks.
    Each chunk retains speaker attribution, time range, channel name, and message IDs.
    """
    if not messages:
        return []

    chunks: list[dict[str, Any]] = []
    current_msgs: list[dict[str, Any]] = []
    current_tokens = 0

    for msg in messages:
        author = msg.get("author_name", "User")
        content = msg.get("content", "").strip()
        if not content:
            continue
        line = f"[{author}]: {content}"
        tokens = count_tokens(line)

        if current_msgs and current_tokens + tokens > max_tokens:
            chunk_text_content = "\n".join(f"[{m.get('author_name', 'User')}]: {m.get('content', '')}" for m in current_msgs)
            chunks.append({
                "text": chunk_text_content,
                "message_ids": [m.get("message_id") or str(m.get("_id")) for m in current_msgs],
                "channel_id": current_msgs[0].get("channel_id", ""),
                "channel_name": current_msgs[0].get("channel_name", ""),
                "project_key": current_msgs[0].get("project_key", ""),
                "org_id": current_msgs[0].get("org_id", ""),
                "created_at": current_msgs[0].get("created_at") or current_msgs[-1].get("created_at"),
                "authors": list(set(m.get("author_name", "User") for m in current_msgs)),
            })

            overlap = current_msgs[-overlap_messages:] if overlap_messages > 0 else []
            current_msgs = list(overlap)
            current_tokens = sum(count_tokens(f"[{m.get('author_name', 'User')}]: {m.get('content', '')}") for m in current_msgs)

        current_msgs.append(msg)
        current_tokens += tokens

    if current_msgs:
        chunk_text_content = "\n".join(f"[{m.get('author_name', 'User')}]: {m.get('content', '')}" for m in current_msgs)
        chunks.append({
            "text": chunk_text_content,
            "message_ids": [m.get("message_id") or str(m.get("_id")) for m in current_msgs],
            "channel_id": current_msgs[0].get("channel_id", ""),
            "channel_name": current_msgs[0].get("channel_name", ""),
            "project_key": current_msgs[0].get("project_key", ""),
            "org_id": current_msgs[0].get("org_id", ""),
            "created_at": current_msgs[0].get("created_at") or current_msgs[-1].get("created_at"),
            "authors": list(set(m.get("author_name", "User") for m in current_msgs)),
        })

    return chunks


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Pure-python cosine similarity — avoids a numpy dependency for what's
    typically a few hundred to a few thousand short comparisons per query."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


FALLBACK_MODELS = [
    "models/gemini-embedding-001",
    "gemini-embedding-001",
    "models/text-embedding-004",
    "models/embedding-001",
    "text-embedding-004",
    "embedding-001",
]


class EmbeddingProvider:
    """
    Wraps langchain-google-genai's embeddings client with fallback support.
    Instantiation never raises — call `.available` before use. This keeps semantic
    search purely additive: if GEMINI_API_KEY is unset, or if all candidate
    models fail (e.g. 404 NOT_FOUND on v1beta), every caller falls back to
    regex/keyword search automatically without log spam.
    """

    def __init__(self, api_key: str, model: str = "models/gemini-embedding-001"):
        self.api_key = api_key
        # Deduplicated candidate models starting with the requested one
        self._model_candidates = [model] + [m for m in FALLBACK_MODELS if m != model]
        self._current_model_idx = 0
        self.model = self._model_candidates[0]
        self._client = None
        self.available = False

        if not api_key:
            logger.info("No Gemini API key configured — semantic memory search disabled.")
            return

        self._init_client()

    def _init_client(self) -> bool:
        if self._current_model_idx >= len(self._model_candidates):
            self.available = False
            self._client = None
            return False

        self.model = self._model_candidates[self._current_model_idx]
        try:
            from langchain_google_genai import GoogleGenerativeAIEmbeddings
            self._client = GoogleGenerativeAIEmbeddings(model=self.model, google_api_key=self.api_key)
            self.available = True
            return True
        except Exception as e:
            logger.warning(
                "Embedding provider init failed for model %s (%s) — falling back to keyword search.",
                self.model, e,
            )
            self.available = False
            return False

    def _handle_failure_and_retry(self, fn_name: str, *args, **kwargs) -> Any:
        """Attempt fallback models if the current model returns 404 NOT_FOUND."""
        while self.available and self._current_model_idx < len(self._model_candidates) - 1:
            self._current_model_idx += 1
            next_model = self._model_candidates[self._current_model_idx]
            logger.info("Retrying embeddings with fallback model: %s", next_model)
            if not self._init_client():
                break
            try:
                method = getattr(self._client, fn_name)
                return method(*args, **kwargs)
            except Exception as e:
                err_str = str(e)
                if "404" in err_str or "NOT_FOUND" in err_str or "not found" in err_str:
                    continue
                else:
                    logger.warning("%s failed with model %s: %s", fn_name, self.model, e)
                    break

        logger.warning(
            "Embedding provider disabled (%s failed on all candidate models) — falling back to keyword search.",
            fn_name,
        )
        self.available = False
        return None

    def embed_query(self, text: str) -> list[float] | None:
        if not self.available or not text or not text.strip():
            return None
        try:
            return self._client.embed_query(text)
        except Exception as e:
            err_str = str(e)
            if ("404" in err_str or "NOT_FOUND" in err_str or "not found" in err_str) and self._current_model_idx < len(self._model_candidates) - 1:
                return self._handle_failure_and_retry("embed_query", text)
            logger.warning("embed_query failed: %s — disabling semantic embeddings.", e)
            self.available = False
            return None

    def embed_documents(self, texts: list[str]) -> list[list[float]] | None:
        if not self.available or not texts:
            return None
        try:
            return self._client.embed_documents(texts)
        except Exception as e:
            err_str = str(e)
            if ("404" in err_str or "NOT_FOUND" in err_str or "not found" in err_str) and self._current_model_idx < len(self._model_candidates) - 1:
                return self._handle_failure_and_retry("embed_documents", texts)
            logger.warning("embed_documents failed: %s — disabling semantic embeddings.", e)
            self.available = False
            return None


def rank_by_similarity(
    query_vector: list[float],
    candidates: list[dict[str, Any]],
    vector_field: str = "embedding",
    top_k: int = 5,
) -> list[dict[str, Any]]:
    """
    Score and sort a list of candidate documents (each carrying a stored
    embedding under `vector_field`) against a query vector. Documents missing
    an embedding score 0 and sink to the bottom rather than erroring out —
    lets old pre-embedding records coexist with new ones during rollout.
    """
    scored = []
    for doc in candidates:
        vec = doc.get(vector_field)
        score = cosine_similarity(query_vector, vec) if vec else 0.0
        scored.append((score, doc))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [dict(doc, _score=score) for score, doc in scored[:top_k]]
