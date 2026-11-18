from datetime import timedelta

import pytest
from litestar.testing import TestClient

import main as main_module
from lib.auth import jwt_auth
from services import workspaces as workspace_service


def _auth_headers():
    token = jwt_auth.create_token(
        identifier="test@example.com",
        token_expiration=timedelta(minutes=15),
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setattr(main_module, "create_all_tables", lambda: None)
    monkeypatch.setattr(main_module, "start_background_tasks", lambda app: None)
    app = main_module.create_app()
    with TestClient(app) as test_client:
        yield test_client


def test_delete_workspace_requires_confirmation(client):
    r = client.request(
        "DELETE",
        "/api/workspace",
        headers=_auth_headers(),
        json={"confirmation": "nope"},
    )
    assert r.status_code == 400


def test_delete_workspace_returns_deleted(client, monkeypatch):
    deleted = {}

    async def fake_delete(email, confirmation):
        deleted["value"] = (email, confirmation)

    monkeypatch.setattr(workspace_service, "delete_workspace", fake_delete)
    r = client.request(
        "DELETE",
        "/api/workspace",
        headers=_auth_headers(),
        json={"confirmation": "DELETE"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["message"] == "deleted"
    assert deleted["value"] == ("test@example.com", "DELETE")


def test_delete_workspace_requires_auth(client):
    assert client.request("DELETE", "/api/workspace", json={"confirmation": "DELETE"}).status_code == 401
