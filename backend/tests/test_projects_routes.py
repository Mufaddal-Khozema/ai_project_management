from datetime import datetime, timedelta

import pytest
from litestar.testing import TestClient

import main as main_module
from lib.auth import jwt_auth
from services import projects as project_service

TEST_UUID = "123e4567-e89b-12d3-a456-426614174000"


def _auth_headers():
    token = jwt_auth.create_token(
        identifier="test@example.com",
        token_expiration=timedelta(minutes=15),
    )
    return {"Authorization": f"Bearer {token}"}


def _row(**overrides):
    row = {
        "uuid": TEST_UUID,
        "pm_provider": "taiga",
        "project_id": "10",
        "project_name": "Website Redesign",
        "project_slug": "website-redesign",
        "comm_provider": "discord",
        "guild_id": "200",
        "channel_id": "300",
        "active": True,
        "created_on": datetime(2024, 1, 1),
        "updated_on": datetime(2024, 1, 1),
    }
    row.update(overrides)
    return row


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setattr(main_module, "create_all_tables", lambda: None)
    monkeypatch.setattr(main_module, "start_background_tasks", lambda app: None)
    app = main_module.create_app()
    with TestClient(app) as test_client:
        yield test_client


def test_list_projects_returns_mappings(client, monkeypatch):
    async def fake_list(email):
        return [_row()]

    monkeypatch.setattr(project_service, "list_mappings", fake_list)
    r = client.get("/api/projects", headers=_auth_headers())
    assert r.status_code == 200, r.text
    body = r.json()
    assert body[0]["project_id"] == "10"
    assert body[0]["project_slug"] == "website-redesign"
    assert body[0]["channel_id"] == "300"


def test_upsert_project_returns_mapping(client, monkeypatch):
    async def fake_upsert(email, data):
        return _row(project_id=data.project_id, channel_id=data.channel_id)

    monkeypatch.setattr(project_service, "upsert_mapping", fake_upsert)
    r = client.put(
        "/api/projects",
        headers=_auth_headers(),
        json={
            "pm_provider": "taiga",
            "project_id": "10",
            "comm_provider": "discord",
            "channel_id": "300",
        },
    )
    assert r.status_code == 200, r.text
    assert r.json()["project_id"] == "10"


def test_upsert_project_validates_body(client):
    r = client.put(
        "/api/projects",
        headers=_auth_headers(),
        json={"pm_provider": "taiga", "project_id": "10"},
    )
    assert r.status_code == 400


def test_delete_project_returns_message(client, monkeypatch):
    async def fake_delete(email, uuid):
        return None

    monkeypatch.setattr(project_service, "delete_mapping", fake_delete)
    r = client.delete(f"/api/projects/{TEST_UUID}", headers=_auth_headers())
    assert r.status_code == 200, r.text
    assert r.json()["message"] == "deleted"


def test_projects_require_auth(client):
    assert client.get("/api/projects").status_code == 401
