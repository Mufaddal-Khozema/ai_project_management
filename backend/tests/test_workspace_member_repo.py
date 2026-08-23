import pytest
from piccolo.query.base import Query

from repositories import workspace_member_repo


@pytest.fixture
def capture_run_sync(monkeypatch):
    """Capture the piccolo query object and short-circuit its execution."""
    captured = {}

    def fake_run_sync(self, *args, **kwargs):
        captured["query"] = self
        return captured.get("result", [])

    monkeypatch.setattr(Query, "run_sync", fake_run_sync)
    return captured


def _sql(captured) -> str:
    return str(captured["query"].default_querystrings[0])


def test_find_by_workspace_user_filters(capture_run_sync):
    capture_run_sync["result"] = [{"id": 1}]
    row = workspace_member_repo.find_by_workspace_user(7, 11)
    assert row == {"id": 1}
    sql = _sql(capture_run_sync)
    assert "FROM \"workspace_members\"" in sql
    assert "\"workspace_id\" = 7" in sql
    assert "\"user_id\" = 11" in sql


def test_find_by_workspace_user_missing_returns_none(capture_run_sync):
    capture_run_sync["result"] = []
    assert workspace_member_repo.find_by_workspace_user(7, 11) is None


def test_add_inserts_row(capture_run_sync, monkeypatch):
    capture_run_sync["result"] = [{"id": 1, "workspace_id": 7, "user_id": 11}]
    monkeypatch.setattr(
        workspace_member_repo, "find_by_workspace_user", lambda ws, uid: None
    )
    row = workspace_member_repo.add(7, 11, role="owner", status="active")
    assert row == {"id": 1, "workspace_id": 7, "user_id": 11}
    sql = _sql(capture_run_sync)
    assert "INSERT INTO \"workspace_members\"" in sql
    assert "\"workspace_id\"" in sql
    assert "\"user_id\"" in sql
    assert "\"role\"" in sql
    assert "\"status\"" in sql


def test_add_is_idempotent_returns_existing(capture_run_sync, monkeypatch):
    existing = {"id": 3, "workspace_id": 7, "user_id": 11}
    monkeypatch.setattr(
        workspace_member_repo, "find_by_workspace_user", lambda ws, uid: existing
    )
    row = workspace_member_repo.add(7, 11, role="owner", status="active")
    assert row == existing


def test_list_by_workspace_filters(capture_run_sync):
    capture_run_sync["result"] = [{"id": 1}]
    rows = workspace_member_repo.list_by_workspace(7)
    assert rows == [{"id": 1}]
    sql = _sql(capture_run_sync)
    assert "FROM \"workspace_members\"" in sql
    assert "\"workspace_id\" = 7" in sql


def test_remove_deletes(capture_run_sync):
    capture_run_sync["result"] = [{"id": 1}]
    assert workspace_member_repo.remove(7, 11) is True
    sql = _sql(capture_run_sync)
    assert "DELETE FROM \"workspace_members\"" in sql
    assert "\"workspace_id\" = 7" in sql
    assert "\"user_id\" = 11" in sql


def test_remove_missing_returns_false(capture_run_sync):
    capture_run_sync["result"] = []
    assert workspace_member_repo.remove(7, 11) is False