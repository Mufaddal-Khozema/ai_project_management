from datetime import datetime, timedelta

import pytest
from litestar.testing import TestClient

import main as main_module
from config import settings
from lib import oauth
from lib.auth import jwt_auth
from lib.crypto import decrypt_token_payload, encrypt_token_payload
from lib.tables import IntegrationStatus
from services import integrations as integration_service


def _auth_headers():
    token = jwt_auth.create_token(
        identifier="test@example.com",
        token_expiration=timedelta(minutes=15),
    )
    return {"Authorization": f"Bearer {token}"}


TEST_UUID = "123e4567-e89b-12d3-a456-426614174000"


def _row(provider="slack", access_token="tok", refresh_token="rt"):
    return {
        "id": 1,
        "workspace_id": 5,
        "provider": provider,
        "token_encrypted": encrypt_token_payload(
            {"access_token": access_token, "refresh_token": refresh_token}
        ),
        "status": IntegrationStatus.connected.value,
        "expires_at": datetime(2099, 1, 1),
        "uuid": TEST_UUID,
        "account_name": "Acme",
        "scopes": None,
        "last_synced_at": None,
        "created_on": datetime(2024, 1, 1),
        "updated_on": datetime(2024, 1, 1),
    }


PROVIDER_TOKENS = {
    "slack": {
        "access_token": "xoxp-user",
        "scope": "channels:read",
        "account_name": "Acme",
    },
    "teams": {
        "access_token": "msteams-tok",
        "refresh_token": "msteams-rt",
        "expires_at": 1717000000,
        "scope": ["User.Read"],
        "account_name": "Acme",
    },
    "discord": {
        "access_token": "disc-tok",
        "refresh_token": "disc-rt",
        "expires_at": 1717000000,
        "scope": ["identify"],
        "account_name": "Acme",
    },
    "jira": {
        "access_token": "jira-tok",
        "refresh_token": "jira-rt",
        "expires_at": 1717000000,
        "scope": ["read:jira-work"],
        "instance_url": "https://acme.atlassian.net",
        "account_name": "Acme",
    },
    "clickup": {
        "access_token": "cu-tok",
        "refresh_token": "cu-rt",
        "expires_at": 1717000000,
        "scope": ["tasks:read"],
        "account_name": "Acme",
    },
}


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setattr(main_module, "create_all_tables", lambda: None)
    monkeypatch.setattr(main_module, "start_background_tasks", lambda app: None)
    app = main_module.create_app()
    with TestClient(app) as test_client:
        yield test_client


# ─── JWT protection ───────────────────────────────────────────────────────────

def test_integrations_endpoints_require_jwt(client):
    assert client.get("/api/integrations").status_code == 401
    assert (
        client.post("/api/integrations/slack/auth", json={"redirect_source": "settings"}).status_code
        == 401
    )
    assert client.post("/api/integrations/slack/disconnect").status_code == 401
    assert client.post("/api/integrations/slack/refresh").status_code == 401


def test_oauth_callback_is_public(client):
    r = client.get("/api/integrations/oauth/slack/callback?code=x&state=y", follow_redirects=False)
    assert r.status_code == 302


# ─── GET /api/integrations ────────────────────────────────────────────────────

def test_list_integrations_returns_metadata_only(client, monkeypatch):
    monkeypatch.setattr(integration_service.user_repo, "find_by_email", lambda email: {"id": 1})
    monkeypatch.setattr(integration_service.workspace_repo, "find_by_user_id", lambda uid: {"id": 5})
    row = {
        "uuid": TEST_UUID,
        "provider": "slack",
        "account_name": "Acme",
        "status": "connected",
        "expires_at": datetime(2099, 1, 1),
        "last_synced_at": None,
        "created_on": datetime(2024, 1, 1),
        "updated_on": datetime(2024, 1, 1),
        "token_encrypted": "should-not-leak",
        "scopes": "should-not-leak",
    }
    monkeypatch.setattr(integration_service.integration_repo, "list_by_workspace", lambda ws: [row])

    r = client.get("/api/integrations", headers=_auth_headers())
    assert r.status_code == 200
    body = r.json()
    item = body["integrations"][0]
    assert item["provider"] == "slack"
    assert item["status"] == "connected"
    assert "token_encrypted" not in item
    assert "scopes" not in item


# ─── POST /api/integrations/{provider}/auth ───────────────────────────────────

def test_initiate_auth_returns_authorization_url(client, monkeypatch):
    monkeypatch.setattr(integration_service.user_repo, "find_by_email", lambda email: {"id": 1})
    monkeypatch.setattr(integration_service.workspace_repo, "find_by_user_id", lambda uid: {"id": 5})

    async def fake_get_authorization_url(provider, redirect_uri, state):
        return "https://auth.example/start"

    monkeypatch.setattr(oauth, "get_authorization_url", fake_get_authorization_url)

    r = client.post(
        "/api/integrations/slack/auth",
        json={"redirect_source": "settings", "company_name": "Acme"},
        headers=_auth_headers(),
    )
    assert r.status_code == 200
    assert r.json() == {"authorization_url": "https://auth.example/start"}


def test_initiate_auth_unsupported_provider(client):
    r = client.post(
        "/api/integrations/not-real/auth",
        json={"redirect_source": "settings"},
        headers=_auth_headers(),
    )
    assert r.status_code == 400


# ─── POST /api/integrations/taiga/connect ─────────────────────────────────────

def test_taiga_connect_success(client, monkeypatch):
    monkeypatch.setattr(integration_service.user_repo, "find_by_email", lambda email: {"id": 1})
    monkeypatch.setattr(integration_service.workspace_repo, "find_by_user_id", lambda uid: {"id": 5})

    async def fake_authenticate(username, password):
        return {
            "access_token": "taiga-tok",
            "refresh_token": "taiga-rt",
            "account_name": username,
            "user_id": 42,
        }

    monkeypatch.setattr(oauth, "taiga_authenticate", fake_authenticate)
    monkeypatch.setattr(
        integration_service.integration_repo, "find_by_workspace_provider", lambda ws, p: None
    )
    captured = {}

    def fake_create(ws, p, token_encrypted, account_name, scopes, status, expires_at=None):
        captured.update(
            provider=p,
            token_encrypted=token_encrypted,
            account_name=account_name,
            status=status,
        )
        return {
            "uuid": TEST_UUID,
            "provider": p,
            "account_name": account_name,
            "status": status,
            "expires_at": expires_at,
            "last_synced_at": None,
            "created_on": datetime(2024, 1, 1),
            "updated_on": datetime(2024, 1, 1),
        }

    monkeypatch.setattr(integration_service.integration_repo, "create", fake_create)

    r = client.post(
        "/api/integrations/taiga/connect",
        json={"username": "bob", "password": "secret"},
        headers=_auth_headers(),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["provider"] == "taiga"
    assert body["status"] == IntegrationStatus.connected.value
    assert body["account_name"] == "bob"
    assert "token_encrypted" not in body
    decrypted = decrypt_token_payload(captured["token_encrypted"])
    assert decrypted["access_token"] == "taiga-tok"
    assert decrypted["refresh_token"] == "taiga-rt"
    assert decrypted["user_id"] == 42


def test_taiga_connect_invalid_credentials(client, monkeypatch):
    monkeypatch.setattr(integration_service.user_repo, "find_by_email", lambda email: {"id": 1})
    monkeypatch.setattr(integration_service.workspace_repo, "find_by_user_id", lambda uid: {"id": 5})

    async def fake_authenticate(username, password):
        raise oauth.TaigaAuthError("nope")

    monkeypatch.setattr(oauth, "taiga_authenticate", fake_authenticate)

    r = client.post(
        "/api/integrations/taiga/connect",
        json={"username": "bob", "password": "wrong"},
        headers=_auth_headers(),
    )
    assert r.status_code == 400
    assert "Invalid Taiga credentials" in r.json()["title"]


def test_taiga_connect_requires_jwt(client):
    r = client.post(
        "/api/integrations/taiga/connect",
        json={"username": "bob", "password": "secret"},
    )
    assert r.status_code == 401


# ─── OAuth callback happy path per provider ───────────────────────────────────

@pytest.mark.parametrize("provider", list(PROVIDER_TOKENS))
def test_oauth_callback_connects_provider(client, monkeypatch, provider):
    state = integration_service.store_oauth_state(provider, 5, "settings")
    token = PROVIDER_TOKENS[provider]

    async def fake_get_access_token(p, code, redirect_uri):
        return token

    monkeypatch.setattr(oauth, "get_access_token", fake_get_access_token)
    monkeypatch.setattr(
        integration_service.integration_repo, "find_by_workspace_provider", lambda ws, p: None
    )
    captured = {}

    def fake_create(ws, p, token_encrypted, account_name, scopes, status, expires_at=None):
        captured.update(
            provider=p,
            token_encrypted=token_encrypted,
            account_name=account_name,
            scopes=scopes,
            status=status,
            expires_at=expires_at,
        )
        return {
            "uuid": "u-1",
            "provider": p,
            "account_name": account_name,
            "status": status,
            "expires_at": expires_at,
            "last_synced_at": None,
            "created_on": datetime(2024, 1, 1),
            "updated_on": datetime(2024, 1, 1),
        }

    monkeypatch.setattr(integration_service.integration_repo, "create", fake_create)

    r = client.get(
        f"/api/integrations/oauth/{provider}/callback?code=code123&state={state}",
        follow_redirects=False,
    )
    assert r.status_code == 302
    location = r.headers["location"]
    assert f"provider={provider}" in location
    assert "status=connected" in location
    assert "source=settings" in location
    assert captured["provider"] == provider
    assert captured["status"] == IntegrationStatus.connected.value
    assert captured["account_name"] == "Acme"
    decrypted = decrypt_token_payload(captured["token_encrypted"])
    assert decrypted["access_token"] == token["access_token"]


def test_oauth_callback_missing_params_redirects_error(client):
    r = client.get("/api/integrations/oauth/slack/callback", follow_redirects=False)
    assert r.status_code == 302
    assert "status=error" in r.headers["location"]


def test_oauth_callback_invalid_state_redirects_error(client):
    r = client.get(
        "/api/integrations/oauth/slack/callback?code=code&state=badstate",
        follow_redirects=False,
    )
    assert r.status_code == 302
    assert "status=error" in r.headers["location"]


def test_oauth_callback_overwrites_existing_row(client, monkeypatch):
    state = integration_service.store_oauth_state("slack", 5, "settings")

    async def fake_get_access_token(p, code, redirect_uri):
        return {"access_token": "new-tok", "scope": "channels:read", "account_name": "Acme"}

    monkeypatch.setattr(oauth, "get_access_token", fake_get_access_token)
    existing = _row("slack", "old-tok", "rt")
    monkeypatch.setattr(
        integration_service.integration_repo,
        "find_by_workspace_provider",
        lambda ws, p: existing,
    )
    updated = {}

    def fake_update_token(iid, token_encrypted, account_name, expires_at, status, last_synced_at):
        updated["iid"] = iid
        updated["token_encrypted"] = token_encrypted
        return {
            **existing,
            "status": status,
            "expires_at": expires_at,
            "token_encrypted": token_encrypted,
        }

    monkeypatch.setattr(integration_service.integration_repo, "update_token", fake_update_token)
    created = {"called": False}

    def fake_create(*args, **kwargs):
        created["called"] = True
        return {}

    monkeypatch.setattr(integration_service.integration_repo, "create", fake_create)

    r = client.get(
        f"/api/integrations/oauth/slack/callback?code=code123&state={state}",
        follow_redirects=False,
    )
    assert r.status_code == 302
    assert "status=connected" in r.headers["location"]
    assert updated["iid"] == 1
    assert created["called"] is False
    assert decrypt_token_payload(updated["token_encrypted"])["access_token"] == "new-tok"


# ─── POST /api/integrations/{provider}/disconnect ─────────────────────────────

def test_disconnect_removes_row_and_second_returns_404(client, monkeypatch):
    holder = {"row": _row("slack", "tok", "rt")}
    monkeypatch.setattr(integration_service, "_resolve_workspace_id", lambda email: 5)
    monkeypatch.setattr(
        integration_service.integration_repo,
        "find_by_workspace_provider",
        lambda ws, p: holder["row"],
    )
    deleted = {"count": 0}

    def fake_delete(ws, p):
        deleted["count"] += 1
        return True

    monkeypatch.setattr(integration_service.integration_repo, "delete_by_workspace_provider", fake_delete)

    async def fake_revoke(provider, access_token):
        pass

    monkeypatch.setattr(oauth, "revoke_access_token", fake_revoke)

    r = client.post("/api/integrations/slack/disconnect", headers=_auth_headers())
    assert r.status_code == 200
    assert r.json() == {"message": "disconnected"}
    assert deleted["count"] == 1

    holder["row"] = None
    r = client.post("/api/integrations/slack/disconnect", headers=_auth_headers())
    assert r.status_code == 404


# ─── POST /api/integrations/{provider}/refresh ────────────────────────────────

def test_refresh_success_updates_token(client, monkeypatch):
    row = _row("clickup", "old-tok", "rt")
    holder = {"row": row}
    monkeypatch.setattr(integration_service, "_resolve_workspace_id", lambda email: 5)
    monkeypatch.setattr(
        integration_service.integration_repo,
        "find_by_workspace_provider",
        lambda ws, p: holder["row"],
    )

    async def fake_refresh(provider, refresh_token):
        return {
            "access_token": "new-tok",
            "refresh_token": "new-rt",
            "expires_at": 2000000000,
            "scope": "tasks:read",
        }

    monkeypatch.setattr(oauth, "refresh_access_token", fake_refresh)
    updated = {}

    def fake_update_token(iid, token_encrypted, account_name, expires_at, status, last_synced_at):
        updated["token_encrypted"] = token_encrypted
        updated["expires_at"] = expires_at
        return {
            **row,
            "status": status,
            "expires_at": expires_at,
            "token_encrypted": token_encrypted,
        }

    monkeypatch.setattr(integration_service.integration_repo, "update_token", fake_update_token)

    r = client.post("/api/integrations/clickup/refresh", headers=_auth_headers())
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "connected"
    assert body["provider"] == "clickup"
    assert "token_encrypted" not in body
    assert decrypt_token_payload(updated["token_encrypted"])["access_token"] == "new-tok"


def test_refresh_failure_marks_expired(client, monkeypatch):
    row = _row("clickup", "old-tok", "rt")
    monkeypatch.setattr(integration_service, "_resolve_workspace_id", lambda email: 5)
    monkeypatch.setattr(
        integration_service.integration_repo,
        "find_by_workspace_provider",
        lambda ws, p: row,
    )

    async def fake_refresh(provider, refresh_token):
        raise RuntimeError("token expired")

    monkeypatch.setattr(oauth, "refresh_access_token", fake_refresh)

    def fake_update_status(iid, status):
        return {**row, "status": status}

    monkeypatch.setattr(integration_service.integration_repo, "update_status", fake_update_status)

    r = client.post("/api/integrations/clickup/refresh", headers=_auth_headers())
    assert r.status_code == 200
    assert r.json()["status"] == "expired"


# ─── GET /api/integrations/{provider}/members ─────────────────────────────────

def test_list_members_requires_connected_integration(client, monkeypatch):
    monkeypatch.setattr(integration_service, "_resolve_workspace_id", lambda email: 5)
    monkeypatch.setattr(
        integration_service.integration_repo, "find_by_workspace_provider", lambda ws, p: None
    )

    r = client.get("/api/integrations/taiga/members", headers=_auth_headers())
    assert r.status_code == 404


def test_list_members_unsupported_provider(client, monkeypatch):
    monkeypatch.setattr(integration_service, "_resolve_workspace_id", lambda email: 5)
    monkeypatch.setattr(
        integration_service.integration_repo,
        "find_by_workspace_provider",
        lambda ws, p: _row("slack", "tok", "rt"),
    )

    r = client.get("/api/integrations/slack/members", headers=_auth_headers())
    assert r.status_code == 400


def test_list_members_returns_provider_members(client, monkeypatch):
    row = _row("taiga", "taiga-tok", "rt")
    monkeypatch.setattr(integration_service, "_resolve_workspace_id", lambda email: 5)
    monkeypatch.setattr(
        integration_service.integration_repo, "find_by_workspace_provider", lambda ws, p: row
    )

    captured = {}

    async def fake_list_taiga(access_token, base_url, user_id=None):
        captured["user_id"] = user_id
        return [
            {
                "id": "1",
                "name": "Ada Lovelace",
                "username": "ada",
                "email": "ada@example.com",
                "avatar": "http://img/ada.png",
            }
        ]

    monkeypatch.setattr(oauth, "list_taiga_members", fake_list_taiga)

    r = client.get("/api/integrations/taiga/members", headers=_auth_headers())
    assert r.status_code == 200
    body = r.json()
    assert body["provider"] == "taiga"
    assert body["members"][0]["name"] == "Ada Lovelace"
    assert body["members"][0]["email"] == "ada@example.com"
    assert "token_encrypted" not in body
    # _row() stores no user_id, so the stored fallback (None) is passed through.
    assert captured["user_id"] is None


def test_list_members_requires_jwt(client):
    r = client.get("/api/integrations/taiga/members")
    assert r.status_code == 401