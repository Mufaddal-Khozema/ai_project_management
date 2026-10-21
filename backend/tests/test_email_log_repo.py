import pytest
from piccolo.query.base import Query

from repositories import email_log_repo


@pytest.fixture
def capture_run(monkeypatch):
    captured = {}

    async def fake_run(self, *args, **kwargs):
        captured["query"] = self
        return captured.get("result", [])

    monkeypatch.setattr(Query, "run", fake_run)
    return captured


def _sql(captured) -> str:
    return str(captured["query"].default_querystrings[0])


async def test_exists_filters_on_all_keys(capture_run):
    capture_run["result"] = [{"id": 1}]
    assert await email_log_repo.exists(7, "trial_expiry_3", 42) is True
    sql = _sql(capture_run)
    assert "FROM \"email_log\"" in sql
    assert "\"user_id\" = 7" in sql
    assert "\"email_type\" = 'trial_expiry_3'" in sql
    assert "\"entity_id\" = 42" in sql


async def test_exists_returns_false_when_missing(capture_run):
    assert await email_log_repo.exists(7, "trial_expiry_3", 42) is False


async def test_insert_writes_audit_row(capture_run):
    capture_run["result"] = [{"id": 1, "user_id": 7, "email_type": "trial_expiry_3"}]
    row = await email_log_repo.insert(7, "trial_expiry_3", 42, "subscription")
    assert row["user_id"] == 7
    sql = _sql(capture_run)
    assert "INSERT INTO \"email_log\"" in sql
    assert "\"email_type\"" in sql
    assert "\"entity_type\"" in sql
