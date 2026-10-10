from piccolo.query.base import Query

from repositories import workspace_repo


def _capture(monkeypatch, results):
    calls = {"n": 0}

    def fake_run_sync(self, *args, **kwargs):
        result = results[min(calls["n"], len(results) - 1)]
        calls["n"] += 1
        return result

    monkeypatch.setattr(Query, "run_sync", fake_run_sync)
    return calls


def test_find_by_member_id_returns_workspace(monkeypatch):
    calls = _capture(
        monkeypatch,
        results=[[{"workspace_id": 5}], [{"id": 5, "company_name": "Acme"}]],
    )
    row = workspace_repo.find_by_member_id(7)
    assert row == {"id": 5, "company_name": "Acme"}
    assert calls["n"] == 2


def test_find_by_member_id_without_membership_returns_none(monkeypatch):
    calls = _capture(monkeypatch, results=[[]])
    assert workspace_repo.find_by_member_id(7) is None
    assert calls["n"] == 1


def test_find_by_member_id_dangling_membership_returns_none(monkeypatch):
    _capture(monkeypatch, results=[[{"workspace_id": 5}], []])
    assert workspace_repo.find_by_member_id(7) is None
