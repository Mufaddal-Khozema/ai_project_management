from __future__ import annotations

import json
from typing import Any

import redis.asyncio as redis
import structlog

from config import settings

logger = structlog.get_logger(__name__)

CACHE_PREFIX = "identity:resolve"

_redis_client: redis.Redis | None = None


def make_identity_key(
    provider: str,
    external_id: str,
    guild_id: str | None = None,
    channel_id: str | None = None,
) -> str:
    key = f"{CACHE_PREFIX}:{provider}:{external_id}"
    if channel_id:
        key = f"{key}:{guild_id or '-'}:{channel_id}"
    return key


async def _get_redis() -> redis.Redis | None:
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
        await client.ping()
    except redis.RedisError:
        logger.warning("redis unreachable — identity resolve running uncached")
        return None

    _redis_client = client
    return _redis_client


def reset_client() -> None:
    """Drop the shared client. Used by tests when settings change."""
    global _redis_client
    _redis_client = None


async def cache_get(key: str) -> dict[str, Any] | None:
    client = await _get_redis()
    if client is None:
        return None
    try:
        raw = await client.get(key)
    except redis.RedisError:
        logger.warning("redis get failed — identity resolve running uncached")
        return None
    if raw is None:
        return None
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    return json.loads(raw)


async def cache_set(key: str, value: dict[str, Any], ttl_seconds: int | None = None) -> None:
    client = await _get_redis()
    if client is None:
        return
    ttl = ttl_seconds if ttl_seconds is not None else settings.identity_cache_ttl_seconds
    try:
        await client.set(key, json.dumps(value, default=str), ex=ttl)
    except redis.RedisError:
        logger.warning("redis set failed — identity resolve running uncached")


async def cache_invalidate(provider: str, external_id: str) -> None:
    """Drop cached resolve responses for this identity, across channel variants."""
    client = await _get_redis()
    if client is None:
        return
    try:
        pattern = f"{make_identity_key(provider, external_id)}*"
        async for key in client.scan_iter(match=pattern):
            await client.delete(key)
    except redis.RedisError:
        logger.warning("redis delete failed")
