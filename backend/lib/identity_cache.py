from __future__ import annotations

import json
from typing import Any

import redis
import structlog

from config import settings

logger = structlog.get_logger(__name__)

CACHE_PREFIX = "identity:resolve"

_redis_client: redis.Redis | None = None


def make_identity_key(provider: str, external_id: str) -> str:
    return f"{CACHE_PREFIX}:{provider}:{external_id}"


def _get_redis() -> redis.Redis | None:
    """Return the shared Redis client, or None when Redis is not usable.

    Never raises — when Redis is unconfigured or unreachable, resolution
    degrades to a database lookup on every call instead of failing.
    """
    global _redis_client

    if not settings.redis_url:
        return None
    if _redis_client is not None:
        return _redis_client

    try:
        client = redis.from_url(settings.redis_url, socket_connect_timeout=2, socket_timeout=2)
        client.ping()
    except redis.RedisError:
        logger.warning("redis unreachable — identity resolve running uncached")
        return None

    _redis_client = client
    return _redis_client


def reset_client() -> None:
    """Drop the shared client. Used by tests when settings change."""
    global _redis_client
    _redis_client = None


def cache_get(key: str) -> dict[str, Any] | None:
    client = _get_redis()
    if client is None:
        return None
    try:
        raw = client.get(key)
    except redis.RedisError:
        logger.warning("redis get failed — identity resolve running uncached")
        return None
    if raw is None:
        return None
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    return json.loads(raw)


def cache_set(key: str, value: dict[str, Any], ttl_seconds: int | None = None) -> None:
    client = _get_redis()
    if client is None:
        return
    ttl = ttl_seconds if ttl_seconds is not None else settings.identity_cache_ttl_seconds
    try:
        client.set(key, json.dumps(value, default=str), ex=ttl)
    except redis.RedisError:
        logger.warning("redis set failed — identity resolve running uncached")


def cache_invalidate(provider: str, external_id: str) -> None:
    """Drop a cached resolve response (call after link/unlink in Phase 2)."""
    client = _get_redis()
    if client is None:
        return
    try:
        client.delete(make_identity_key(provider, external_id))
    except redis.RedisError:
        logger.warning("redis delete failed")
