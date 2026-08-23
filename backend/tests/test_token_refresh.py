from datetime import datetime, timedelta
from types import SimpleNamespace

from lib import token_refresh
from lib.tables import IntegrationStatus


def _row(iid=1, provider="clickup"):
    return {
        "id": iid,
        "workspace_id": 5,
        "provider": provider,
        "token_encrypted": "enc",
        "status": IntegrationStatus.connected.value,
        "expires_at": datetime(2024, 1, 1),
        "uuid": "123e4567-e89b-12d3-a456-426614174000",
        "account_name": "Acme",
        "scopes": None,
        "last_synced_at": None,
        "created_on": datetime(2024, 1, 1),
        "updated_on": datetime(2024, 1, 1),
    }


def _app():
    return SimpleNamespace(emit=lambda event, **kwargs: None)


async def test_refresh_due_tokens_refreshes_due(monkeypatch):
    rows = [_row(1), _row(2)]
    monkeypatch.setattr(token_refresh.integration_repo, "list_refreshable", lambda cutoff: rows)
    called = []

    async def fake_refresh_row(row, app):
        called.append(row["id"])
        return {"status": IntegrationStatus.connected.value}

    monkeypatch.setattr(token_refresh, "_refresh_row", fake_refresh_row)
    processed = await token_refresh.refresh_due_tokens(_app())
    assert processed == 2
    assert called == [1, 2]


async def test_refresh_due_tokens_skips_rows_without_refresh_token(monkeypatch):
    rows = [_row(1), _row(2)]
    monkeypatch.setattr(token_refresh.integration_repo, "list_refreshable", lambda cutoff: rows)
    called = []

    async def fake_refresh_row(row, app):
        called.append(row["id"])
        return None

    monkeypatch.setattr(token_refresh, "_refresh_row", fake_refresh_row)
    processed = await token_refresh.refresh_due_tokens(_app())
    assert processed == 0
    assert called == [1, 2]


async def test_refresh_due_tokens_counts_only_successes(monkeypatch):
    rows = [_row(1), _row(2)]
    monkeypatch.setattr(token_refresh.integration_repo, "list_refreshable", lambda cutoff: rows)

    async def fake_refresh_row(row, app):
        if row["id"] == 1:
            raise RuntimeError("boom")
        return {"status": IntegrationStatus.connected.value}

    monkeypatch.setattr(token_refresh, "_refresh_row", fake_refresh_row)
    processed = await token_refresh.refresh_due_tokens(_app())
    assert processed == 1


async def test_refresh_due_tokens_queries_with_lead_time(monkeypatch):
    captured = {}

    def fake_list_refreshable(cutoff):
        captured["cutoff"] = cutoff
        return []

    monkeypatch.setattr(token_refresh.integration_repo, "list_refreshable", fake_list_refreshable)
    await token_refresh.refresh_due_tokens(_app())
    assert captured["cutoff"] >= token_refresh._utc_now() + timedelta(
        minutes=token_refresh.settings.integration_token_refresh_lead_minutes
    ) - timedelta(seconds=5)