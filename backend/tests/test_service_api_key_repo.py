from piccolo.query.base import Query

from repositories import service_api_key_repo


async def test_find_by_key_hash_filters(monkeypatch):
    captured = {}

    async def fake_run(self, *args, **kwargs):
        captured["query"] = self
        return [{"id": 1, "service_name": "discord-bot"}]

    monkeypatch.setattr(Query, "run", fake_run)
    row = await service_api_key_repo.find_by_key_hash("abc123")
    assert row == {"id": 1, "service_name": "discord-bot"}
    sql = str(captured["query"].default_querystrings[0])
    assert "FROM \"service_api_keys\"" in sql
    assert "\"key_hash\" = 'abc123'" in sql


async def test_find_by_key_hash_missing_returns_none(monkeypatch):
    async def fake_run(self, *args, **kwargs):
        return []

    monkeypatch.setattr(Query, "run", fake_run)
    assert await service_api_key_repo.find_by_key_hash("nope") is None


async def test_create_inserts_row(monkeypatch):
    captured = {}

    async def fake_run(self, *args, **kwargs):
        captured["query"] = self
        return [{"id": 1, "service_name": "discord-bot"}]

    monkeypatch.setattr(Query, "run", fake_run)
    row = await service_api_key_repo.create("discord-bot", "deadbeef")
    assert row == {"id": 1, "service_name": "discord-bot"}
    sql = str(captured["query"].default_querystrings[0])
    assert "INSERT INTO \"service_api_keys\"" in sql
    assert "\"service_name\"" in sql
    assert "\"key_hash\"" in sql
