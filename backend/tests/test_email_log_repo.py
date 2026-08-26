import pytest
from piccolo.query.base import Query

from repositories import email_log_repo


@pytest.fixture
def capture_run_sync(monkeypatch):
    captured = {}

    def fake_run_sync(self, *args, **kwargs):
        captured["query"] = self
        return captured.get("result", [])

    monkeypatch.setattr(Query, "run_sync", fake_run_sync)
    return captured


def _sql(captured) -> str:
    return str(captured["query"].default_querystrings[0])


def test_exists_filters_on_all_keys(capture_run_sync):
    capture_run_sync["result"] = [{"id": 1}]
    assert email_log_repo.exists(7, "trial_expiry_3", 42) is True
    sql = _sql(capture_run_sync)
    assert "FROM \"email_log\"" in sql
    assert "\"user_id\" = 7" in sql
    assert "\"email_type\" = 'trial_expiry_3'" in sql
    assert "\"entity_id\" = 42" in sql


def test_exists_returns_false_when_missing(capture_run_sync):
    assert email_log_repo.exists(7, "trial_expiry_3", 42) is False


def test_insert_writes_audit_row(capture_run_sync):
    capture_run_sync["result"] = [{"id": 1, "user_id": 7, "email_type": "trial_expiry_3"}]
    row = email_log_repo.insert(7, "trial_expiry_3", 42, "subscription")
    assert row["user_id"] == 7
    sql = _sql(capture_run_sync)
    assert "INSERT INTO \"email_log\"" in sql
    assert "\"email_type\"" in sql
    assert "\"entity_type\"" in sql