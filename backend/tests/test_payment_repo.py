import pytest
from piccolo.query.base import Query

from repositories import payment_repo


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


async def test_find_by_user_id_filters(capture_run):
    capture_run["result"] = [{"id": 1, "user_id": 7}]
    row = await payment_repo.find_by_user_id(7)
    assert row == {"id": 1, "user_id": 7}
    sql = _sql(capture_run)
    assert "FROM \"subscription\"" in sql
    assert "\"user_id\" = 7" in sql


async def test_find_by_user_id_missing_returns_none(capture_run):
    assert await payment_repo.find_by_user_id(7) is None


async def test_find_by_subscription_id_filters(capture_run):
    capture_run["result"] = [{"id": 1, "stripe_subscription_id": "sub_123"}]
    row = await payment_repo.find_by_subscription_id("sub_123")
    assert row["id"] == 1
    sql = _sql(capture_run)
    assert "FROM \"subscription\"" in sql
    assert "\"stripe_subscription_id\" = 'sub_123'" in sql


async def test_update_writes_fields(capture_run):
    capture_run["result"] = [{"id": 1, "status": "canceled", "cancel_at_period_end": True}]
    row = await payment_repo.update("sub_123", {"status": "canceled", "cancel_at_period_end": True})
    assert row["status"] == "canceled"
    sql = _sql(capture_run)
    assert "UPDATE \"subscription\"" in sql
    assert "\"stripe_subscription_id\" = 'sub_123'" in sql
    assert "\"status\"" in sql
    assert "\"cancel_at_period_end\"" in sql


async def test_upsert_inserts_when_missing(capture_run, monkeypatch):
    capture_run["result"] = [{"id": 1, "user_id": 7, "stripe_subscription_id": "sub_123"}]

    async def fake_find(sid):
        return None

    monkeypatch.setattr(payment_repo, "find_by_subscription_id", fake_find)
    row = await payment_repo.upsert(
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
    sql = _sql(capture_run)
    assert "INSERT INTO \"subscription\"" in sql


async def test_upsert_updates_when_exists(capture_run, monkeypatch):
    existing = {"id": 1, "stripe_subscription_id": "sub_123"}

    async def fake_find(sid):
        return existing

    updated = {"id": 1, "status": "canceled"}

    async def fake_update(sid, values):
        return updated

    monkeypatch.setattr(payment_repo, "find_by_subscription_id", fake_find)
    monkeypatch.setattr(payment_repo, "update", fake_update)
    row = await payment_repo.upsert(7, {"stripe_subscription_id": "sub_123", "status": "canceled"})
    assert row == updated
