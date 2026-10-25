from piccolo.query.base import Query

from repositories import project_repo


def _capture(monkeypatch, results):
    captured = {"n": 0, "queries": []}

    async def fake_run(self, *args, **kwargs):
        captured["queries"].append(self)
        index = min(captured["n"], len(results) - 1)
        captured["n"] += 1
        return results[index]

    monkeypatch.setattr(Query, "run", fake_run)
    return captured


def _sql(captured) -> str:
    return str(captured["queries"][-1].default_querystrings[0])


def _row(**overrides):
    row = {
        "id": 1,
        "uuid": "123e4567-e89b-12d3-a456-426614174000",
        "workspace_id": 5,
        "pm_provider": "taiga",
        "project_id": "10",
        "project_name": "Website Redesign",
        "project_slug": "website-redesign",
        "comm_provider": "discord",
        "guild_id": "200",
        "channel_id": "300",
        "active": True,
    }
    row.update(overrides)
    return row


async def test_upsert_creates_row(monkeypatch):
    created = _row()
    captured = _capture(monkeypatch, results=[[], [created]])
    row = await project_repo.upsert(
        workspace_id=5,
        pm_provider="taiga",
        project_id="10",
        project_name="Website Redesign",
        project_slug="website-redesign",
        comm_provider="discord",
        channel_id="300",
        guild_id="200",
    )
    assert row == created
    assert "INSERT INTO \"projects\"" in _sql(captured)


async def test_upsert_updates_existing_row(monkeypatch):
    existing = _row(id=9)
    updated = _row(id=9, project_id="11")
    captured = _capture(monkeypatch, results=[[existing], [updated]])
    row = await project_repo.upsert(
        workspace_id=5,
        pm_provider="taiga",
        project_id="11",
        project_name="Website Redesign",
        project_slug="website-redesign",
        comm_provider="discord",
        channel_id="300",
        guild_id="200",
    )
    assert row == updated
    assert "UPDATE \"projects\"" in _sql(captured)
    assert "\"project_id\" = '11'" in _sql(captured)


async def test_find_by_channel_returns_mapping(monkeypatch):
    mapping = _row()
    captured = _capture(monkeypatch, results=[[mapping]])
    row = await project_repo.find_by_channel(5, "discord", "300")
    assert row == mapping
    sql = _sql(captured)
    assert "FROM \"projects\"" in sql
    assert "\"workspace_id\" = 5" in sql
    assert "\"comm_provider\" = 'discord'" in sql
    assert "\"channel_id\" = '300'" in sql
    assert "\"active\" = True" in sql


async def test_find_by_channel_guild_mismatch_returns_none(monkeypatch):
    captured = _capture(monkeypatch, results=[[]])
    row = await project_repo.find_by_channel(5, "discord", "300", guild_id="999")
    assert row is None
    sql = _sql(captured)
    assert "\"guild_id\" = '999'" in sql
    assert "IS NULL" in sql
