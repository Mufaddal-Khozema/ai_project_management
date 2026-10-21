from datetime import datetime

import pytest
from piccolo.query.base import Query

from repositories import integration_repo


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


async def test_find_by_workspace_provider_filters(capture_run):
    capture_run["result"] = [{"id": 1}]
    row = await integration_repo.find_by_workspace_provider(7, "slack")
    assert row == {"id": 1}
    sql = _sql(capture_run)
    assert "FROM \"integrations\"" in sql
    assert "\"workspace_id\" = 7" in sql
    assert "\"provider\" = 'slack'" in sql


async def test_find_by_workspace_provider_missing_returns_none(capture_run):
    capture_run["result"] = []
    assert await integration_repo.find_by_workspace_provider(7, "slack") is None


async def test_list_by_workspace_filters(capture_run):
    capture_run["result"] = [{"id": 1}]
    rows = await integration_repo.list_by_workspace(7)
    assert rows == [{"id": 1}]
    sql = _sql(capture_run)
    assert "FROM \"integrations\"" in sql
    assert "\"workspace_id\" = 7" in sql


async def test_create_inserts_row(capture_run):
    capture_run["result"] = [{"id": 1, "provider": "slack"}]
    row = await integration_repo.create(
        workspace_id=7,
        provider="slack",
        token_encrypted="enc",
        account_name="Acme",
        scopes="channels:read",
        status="connected",
    )
    assert row == {"id": 1, "provider": "slack"}
    sql = _sql(capture_run)
    assert "INSERT INTO \"integrations\"" in sql
    assert "\"workspace_id\"" in sql
    assert "\"token_encrypted\"" in sql
    assert "\"status\"" in sql


async def test_update_token_updates_fields(capture_run):
    capture_run["result"] = [{"id": 1, "status": "connected"}]
    row = await integration_repo.update_token(
        integration_id=1,
        token_encrypted="enc2",
        account_name="Acme",
        expires_at=datetime(2099, 1, 1),
        status="connected",
        last_synced_at=None,
    )
    assert row == {"id": 1, "status": "connected"}
    sql = _sql(capture_run)
    assert "UPDATE \"integrations\"" in sql
    assert "\"token_encrypted\"" in sql
    assert "\"status\"" in sql
    assert "\"id\" = 1" in sql


async def test_update_status_updates_only_status(capture_run):
    capture_run["result"] = [{"id": 1, "status": "expired"}]
    row = await integration_repo.update_status(1, "expired")
    assert row == {"id": 1, "status": "expired"}
    sql = _sql(capture_run)
    assert "UPDATE \"integrations\"" in sql
    assert "\"status\"" in sql
    assert "token_encrypted" not in sql.split("RETURNING")[0]


async def test_delete_by_workspace_provider(capture_run):
    capture_run["result"] = [{"id": 1}]
    assert await integration_repo.delete_by_workspace_provider(7, "slack") is True
    sql = _sql(capture_run)
    assert "DELETE FROM \"integrations\"" in sql
    assert "\"workspace_id\" = 7" in sql
    assert "\"provider\" = 'slack'" in sql


async def test_delete_by_workspace_provider_missing_returns_false(capture_run):
    capture_run["result"] = []
    assert await integration_repo.delete_by_workspace_provider(7, "slack") is False


async def test_list_refreshable_filters(capture_run):
    cutoff = datetime(2024, 6, 1)
    capture_run["result"] = [{"id": 1}]
    rows = await integration_repo.list_refreshable(cutoff)
    assert rows == [{"id": 1}]
    sql = _sql(capture_run)
    assert "FROM \"integrations\"" in sql
    assert "\"expires_at\" <= " in sql
    assert "\"status\" != 'error'" in sql
