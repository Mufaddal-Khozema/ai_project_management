import json
import time

import pytest
import redis

from lib import identity_cache


class FakeRedis:
    """Minimal Redis double supporting get/set/delete with expiry."""

    def __init__(self):
        self.store = {}

    def get(self, key):
        entry = self.store.get(key)
        if entry is None:
            return None
        expires_at, raw = entry
        if time.monotonic() >= expires_at:
            self.store.pop(key, None)
            return None
        return raw

    def set(self, key, value, ex=None):
        self.store[key] = (time.monotonic() + (ex if ex is not None else 60), value)

    def delete(self, key):
        self.store.pop(key, None)


@pytest.fixture()
def fake_redis(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr(identity_cache, "_redis_client", fake)
    return fake


def test_cache_round_trip(fake_redis):
    key = identity_cache.make_identity_key("discord", "123")
    assert identity_cache.cache_get(key) is None
    identity_cache.cache_set(key, {"linked": True})
    assert identity_cache.cache_get(key) == {"linked": True}


def test_cache_key_namespaces_provider_and_id(fake_redis):
    identity_cache.cache_set(identity_cache.make_identity_key("discord", "1"), {"n": 1})
    assert identity_cache.cache_get(identity_cache.make_identity_key("discord", "2")) is None
    assert identity_cache.cache_get(identity_cache.make_identity_key("taiga", "1")) is None


def test_cache_invalidate(fake_redis):
    key = identity_cache.make_identity_key("discord", "123")
    identity_cache.cache_set(key, {"linked": True})
    identity_cache.cache_invalidate("discord", "123")
    assert identity_cache.cache_get(key) is None


def test_cache_expiry(fake_redis):
    key = identity_cache.make_identity_key("discord", "123")
    identity_cache.cache_set(key, {"linked": True}, ttl_seconds=0)
    assert identity_cache.cache_get(key) is None


def test_cache_miss_without_redis_url(monkeypatch):
    monkeypatch.setattr(identity_cache, "_redis_client", None)
    monkeypatch.setattr(identity_cache.settings, "redis_url", "")
    key = identity_cache.make_identity_key("discord", "123")
    identity_cache.cache_set(key, {"linked": True})
    assert identity_cache.cache_get(key) is None


def test_cache_miss_when_redis_unreachable(monkeypatch):
    monkeypatch.setattr(identity_cache, "_redis_client", None)

    def boom(*args, **kwargs):
        raise redis.ConnectionError("down")

    monkeypatch.setattr(redis, "from_url", boom)
    key = identity_cache.make_identity_key("discord", "123")
    identity_cache.cache_set(key, {"linked": True})
    assert identity_cache.cache_get(key) is None
