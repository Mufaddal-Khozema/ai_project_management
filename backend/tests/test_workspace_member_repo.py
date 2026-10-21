import pytest
from piccolo.query.base import Query

from repositories import workspace_member_repo


@pytest.fixture
def capture_run(monkeypatch):
    """Capture the piccolo query object and short-circuit its execution."""
    captured = {}

    async def fake_run(self, *args, **kwargs):
        captured["query"] = self
        return captured.get("result", [])

    monkeypatch.setattr(Query, "run", fake_run)
    return captured


def _sql(captured) -> str:
    return str(captured["query"].default_querystrings[0])


async def test_find_by_workspace_user_filters(capture_run):
    capture_run["result"] = [{"id": 1}]
    row = await workspace_member_repo.find_by_workspace_user(7, 11)
    assert row == {"id": 1}
    sql = _sql(capture_run)
    assert "FROM \"workspace_members\"" in sql
    assert "\"workspace_id\" = 7" in sql
    assert "\"user_id\" = 11" in sql


async def test_find_by_workspace_user_missing_returns_none(capture_run):
    capture_run["result"] = []
    assert await workspace_member_repo.find_by_workspace_user(7, 11) is None


async def test_add_inserts_row(capture_run, monkeypatch):
    capture_run["result"] = [{"id": 1, "workspace_id": 7, "user_id": 11}]

    async def fake_find(ws, uid):
        return None

    monkeypatch.setattr(workspace_member_repo, "find_by_workspace_user", fake_find)
    row = await workspace_member_repo.add(7, 11, role="owner", status="active")
    assert row == {"id": 1, "workspace_id": 7, "user_id": 11}
    sql = _sql(capture_run)
    assert "INSERT INTO \"workspace_members\"" in sql
    assert "\"workspace_id\"" in sql
    assert "\"user_id\"" in sql
    assert "\"role\"" in sql
    assert "\"status\"" in sql


async def test_add_is_idempotent_returns_existing(capture_run, monkeypatch):
    existing = {"id": 3, "workspace_id": 7, "user_id": 11}

    async def fake_find(ws, uid):
        return existing

    monkeypatch.setattr(workspace_member_repo, "find_by_workspace_user", fake_find)
    row = await workspace_member_repo.add(7, 11, role="owner", status="active")
    assert row == existing


async def test_list_by_workspace_filters(capture_run):
    capture_run["result"] = [{"id": 1}]
    rows = await workspace_member_repo.list_by_workspace(7)
    assert rows == [{"id": 1}]
    sql = _sql(capture_run)
    assert "FROM \"workspace_members\"" in sql
    assert "\"workspace_id\" = 7" in sql


async def test_remove_deletes(capture_run):
    capture_run["result"] = [{"id": 1}]
    assert await workspace_member_repo.remove(7, 11) is True
    sql = _sql(capture_run)
    assert "DELETE FROM \"workspace_members\"" in sql
    assert "\"workspace_id\" = 7" in sql
    assert "\"user_id\" = 11" in sql


async def test_remove_missing_returns_false(capture_run):
    capture_run["result"] = []
    assert await workspace_member_repo.remove(7, 11) is False
