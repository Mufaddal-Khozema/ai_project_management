from datetime import datetime

import pytest
from piccolo.query.base import Query

from repositories import external_identity_repo


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


def test_find_by_provider_external_id_filters(capture_run_sync):
    capture_run_sync["result"] = [{"id": 1, "user_id": 5}]
    row = external_identity_repo.find_by_provider_external_id("taiga", "42")
    assert row == {"id": 1, "user_id": 5}
    sql = _sql(capture_run_sync)
    assert "FROM \"external_identities\"" in sql
    assert "\"provider\" = 'taiga'" in sql
    assert "\"external_id\" = '42'" in sql


def test_find_by_provider_external_id_missing_returns_none(capture_run_sync):
    capture_run_sync["result"] = []
    assert external_identity_repo.find_by_provider_external_id("taiga", "42") is None


def test_find_user_id_returns_id_when_present(capture_run_sync):
    capture_run_sync["result"] = [{"id": 1, "user_id": 5}]
    assert external_identity_repo.find_user_id_by_provider_external_id("taiga", "42") == 5


def test_find_user_id_returns_none_when_unlinked(capture_run_sync):
    capture_run_sync["result"] = [{"id": 1, "user_id": None}]
    assert external_identity_repo.find_user_id_by_provider_external_id("taiga", "42") is None


def test_find_user_id_returns_none_when_missing(capture_run_sync):
    capture_run_sync["result"] = []
    assert external_identity_repo.find_user_id_by_provider_external_id("taiga", "42") is None


def test_create_inserts_row(capture_run_sync):
    capture_run_sync["result"] = [{"id": 1, "provider": "taiga"}]
    row = external_identity_repo.create(
        user_id=5,
        provider="taiga",
        external_id="42",
        email="ada@example.com",
        name="Ada",
        username="ada",
        avatar="http://img/ada.png",
    )
    assert row == {"id": 1, "provider": "taiga"}
    sql = _sql(capture_run_sync)
    assert "INSERT INTO \"external_identities\"" in sql
    assert "\"user_id\"" in sql
    assert "\"external_id\"" in sql
    assert "\"provider\"" in sql
