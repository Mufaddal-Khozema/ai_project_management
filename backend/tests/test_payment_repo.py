import pytest
from piccolo.query.base import Query

from repositories import payment_repo


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


def test_find_by_user_id_filters(capture_run_sync):
    capture_run_sync["result"] = [{"id": 1, "user_id": 7}]
    row = payment_repo.find_by_user_id(7)
    assert row == {"id": 1, "user_id": 7}
    sql = _sql(capture_run_sync)
    assert "FROM \"subscription\"" in sql
    assert "\"user_id\" = 7" in sql


def test_find_by_user_id_missing_returns_none(capture_run_sync):
    assert payment_repo.find_by_user_id(7) is None


def test_find_by_subscription_id_filters(capture_run_sync):
    capture_run_sync["result"] = [{"id": 1, "stripe_subscription_id": "sub_123"}]
    row = payment_repo.find_by_subscription_id("sub_123")
    assert row["id"] == 1
    sql = _sql(capture_run_sync)
    assert "FROM \"subscription\"" in sql
    assert "\"stripe_subscription_id\" = 'sub_123'" in sql


def test_update_writes_fields(capture_run_sync):
    capture_run_sync["result"] = [{"id": 1, "status": "canceled", "cancel_at_period_end": True}]
    row = payment_repo.update("sub_123", {"status": "canceled", "cancel_at_period_end": True})
    assert row["status"] == "canceled"
    sql = _sql(capture_run_sync)
    assert "UPDATE \"subscription\"" in sql
    assert "\"stripe_subscription_id\" = 'sub_123'" in sql
    assert "\"status\"" in sql
    assert "\"cancel_at_period_end\"" in sql


def test_upsert_inserts_when_missing(capture_run_sync, monkeypatch):
    capture_run_sync["result"] = [{"id": 1, "user_id": 7, "stripe_subscription_id": "sub_123"}]
    monkeypatch.setattr(payment_repo, "find_by_subscription_id", lambda sid: None)
    row = payment_repo.upsert(
        7,
        {
            "stripe_customer_id": "cus_1",
            "stripe_subscription_id": "sub_123",
            "price_id": "price_1",
            "plan_id": "professional",
            "billing_interval": "monthly",
            "status": "active",
            "cancel_at_period_end": False,
        },
    )
    assert row["user_id"] == 7
    sql = _sql(capture_run_sync)
    assert "INSERT INTO \"subscription\"" in sql


def test_upsert_updates_when_exists(capture_run_sync, monkeypatch):
    existing = {"id": 1, "stripe_subscription_id": "sub_123"}
    monkeypatch.setattr(payment_repo, "find_by_subscription_id", lambda sid: existing)
    updated = {"id": 1, "status": "canceled"}
    monkeypatch.setattr(payment_repo, "update", lambda sid, values: updated)
    row = payment_repo.upsert(7, {"stripe_subscription_id": "sub_123", "status": "canceled"})
    assert row == updated