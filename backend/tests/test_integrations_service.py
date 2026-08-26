import time
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from litestar.exceptions import HTTPException

from lib import oauth
from lib.crypto import decrypt_token_payload, encrypt_token_payload
from lib.events import Events
from lib.tables import IntegrationStatus
from services import integrations as svc


def _app():
    emitted = []

    def emit(event, **kwargs):
        emitted.append((event, kwargs))

    return SimpleNamespace(emit=emit), emitted


def _request(app):
    return SimpleNamespace(app=app)


# ─── effective status ─────────────────────────────────────────────────────────

def test_effective_status_connected_no_expiry():
    row = {"status": IntegrationStatus.connected.value, "expires_at": None}
    assert svc._effective_status(row) == IntegrationStatus.connected.value


def test_effective_status_expired():
    row = {"status": IntegrationStatus.connected.value, "expires_at": datetime(2000, 1, 1)}
    assert svc._effective_status(row) == IntegrationStatus.expired.value


def test_effective_status_future_expiry():
    row = {"status": IntegrationStatus.connected.value, "expires_at": datetime(2099, 1, 1)}
    assert svc._effective_status(row) == IntegrationStatus.connected.value


def test_effective_status_error_passthrough():
    row = {"status": IntegrationStatus.error.value, "expires_at": datetime(2000, 1, 1)}
    assert svc._effective_status(row) == IntegrationStatus.error.value


# ─── oauth state store / TTL ──────────────────────────────────────────────────

def test_store_oauth_state_returns_unique():
    svc._oauth_states.clear()
    a = svc.store_oauth_state("slack", 7, "settings")
    b = svc.store_oauth_state("slack", 7, "settings")
    assert a != b
    assert a in svc._oauth_states
    assert b in svc._oauth_states


def test_consume_oauth_state_happy():
    svc._oauth_states.clear()
    state = svc.store_oauth_state("slack", 7, "settings")
    stored = svc.consume_oauth_state(state, "slack")
    assert stored is not None
    assert stored["provider"] == "slack"
    assert stored["workspace_id"] == 7
    assert stored["redirect_source"] == "settings"
    assert state not in svc._oauth_states


def test_consume_oauth_state_stale_returns_none():
    svc._oauth_states.clear()
    state = svc.store_oauth_state("slack", 7, "settings")
    svc._oauth_states[state]["ts"] = time.time() - 601
    assert svc.consume_oauth_state(state, "slack") is None


def test_consume_oauth_state_provider_mismatch():
    svc._oauth_states.clear()
    state = svc.store_oauth_state("slack", 7, "settings")
    assert svc.consume_oauth_state(state, "jira") is None
    assert state not in svc._oauth_states


def test_store_oauth_state_cleans_stale():
    svc._oauth_states.clear()
    svc._oauth_states["stale"] = {
        "provider": "slack",
        "workspace_id": 1,
        "redirect_source": "x",
        "ts": time.time() - 601,
    }
    svc.store_oauth_state("slack", 7, "settings")
    assert "stale" not in svc._oauth_states


# ─── initiate_auth ────────────────────────────────────────────────────────────

async def test_initiate_auth_unsupported_provider():
    with pytest.raises(HTTPException) as exc:
        await svc.initiate_auth("a@b.com", "not-real", "settings")
    assert exc.value.status_code == 400


async def test_initiate_auth_provider_not_configured(monkeypatch):
    monkeypatch.setattr(oauth, "is_provider_configured", lambda provider: False)
    with pytest.raises(HTTPException) as exc:
        await svc.initiate_auth("a@b.com", "slack", "settings")
    assert exc.value.status_code == 400


async def test_initiate_auth_user_not_found(monkeypatch):
    monkeypatch.setattr(svc.user_repo, "find_by_email", lambda email: None)
    with pytest.raises(HTTPException) as exc:
        await svc.initiate_auth("ghost@b.com", "slack", "settings")
    assert exc.value.status_code == 404


async def test_initiate_auth_workspace_auto_create(monkeypatch):
    user = {"id": 1}
    workspace = {"id": 9, "company_name": "My Workspace"}
    monkeypatch.setattr(svc.user_repo, "find_by_email", lambda email: user)
    monkeypatch.setattr(svc.workspace_repo, "find_by_user_id", lambda uid: None)
    created = {}

    def fake_create(uid, data):
        created["uid"], created["data"] = uid, data
        return workspace

    monkeypatch.setattr(svc.workspace_repo, "create", fake_create)

    async def fake_authorization_url(provider, redirect_uri, state):
        return f"https://auth.example/{provider}"

    monkeypatch.setattr(oauth, "get_authorization_url", fake_authorization_url)

    result = await svc.initiate_auth("a@b.com", "slack", "onboarding", company_name="Acme Inc")
    assert created == {"uid": 1, "data": {"company_name": "Acme Inc"}}
    assert result == {"authorization_url": "https://auth.example/slack"}


async def test_initiate_auth_reuses_workspace(monkeypatch):
    user = {"id": 1}
    workspace = {"id": 5}
    monkeypatch.setattr(svc.user_repo, "find_by_email", lambda email: user)
    monkeypatch.setattr(svc.workspace_repo, "find_by_user_id", lambda uid: workspace)
    called = {"create": False}

    def fake_create(uid, data):
        called["create"] = True
        return {}

    monkeypatch.setattr(svc.workspace_repo, "create", fake_create)

    async def fake_authorization_url(provider, redirect_uri, state):
        return "https://auth.example"

    monkeypatch.setattr(oauth, "get_authorization_url", fake_authorization_url)

    result = await svc.initiate_auth("a@b.com", "jira", "settings")
    assert called["create"] is False
    assert result == {"authorization_url": "https://auth.example"}


# ─── list_integrations ────────────────────────────────────────────────────────

async def test_list_integrations_empty_without_workspace(monkeypatch):
    monkeypatch.setattr(svc.user_repo, "find_by_email", lambda email: {"id": 1})
    monkeypatch.setattr(svc.workspace_repo, "find_by_user_id", lambda uid: None)
    assert svc.list_integrations("a@b.com") == []


async def test_list_integrations_maps_rows(monkeypatch):
    monkeypatch.setattr(svc.user_repo, "find_by_email", lambda email: {"id": 1})
    monkeypatch.setattr(svc.workspace_repo, "find_by_user_id", lambda uid: {"id": 5})
    row = {
        "uuid": "u-1",
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
    monkeypatch.setattr(svc.integration_repo, "list_by_workspace", lambda ws: [row])
    result = svc.list_integrations("a@b.com")
    assert result == [
        {
            "uuid": "u-1",
            "provider": "slack",
            "account_name": "Acme",
            "status": "connected",
            "expires_at": datetime(2099, 1, 1, tzinfo=timezone.utc),
            "last_synced_at": None,
            "created_on": datetime(2024, 1, 1, tzinfo=timezone.utc),
            "updated_on": datetime(2024, 1, 1, tzinfo=timezone.utc),
        }
    ]
    assert "token_encrypted" not in result[0]
    assert "scopes" not in result[0]


# ─── disconnect ───────────────────────────────────────────────────────────────

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
        "uuid": "u-1",
        "account_name": "Acme",
        "scopes": None,
        "last_synced_at": None,
        "created_on": datetime(2024, 1, 1),
        "updated_on": datetime(2024, 1, 1),
    }


async def test_disconnect_revokes_and_deletes(monkeypatch):
    monkeypatch.setattr(svc, "_resolve_workspace_id", lambda email: 5)
    monkeypatch.setattr(svc.integration_repo, "find_by_workspace_provider", lambda ws, p: _row())
    revoked = {}

    async def fake_revoke(provider, access_token):
        revoked["provider"], revoked["token"] = provider, access_token

    monkeypatch.setattr(oauth, "revoke_access_token", fake_revoke)
    deleted = {"called": False}

    def fake_delete(ws, p):
        deleted["called"] = True
        return True

    monkeypatch.setattr(svc.integration_repo, "delete_by_workspace_provider", fake_delete)
    app, emitted = _app()
    await svc.disconnect("a@b.com", "slack", _request(app))
    assert revoked == {"provider": "slack", "token": "tok"}
    assert deleted["called"] is True
    assert emitted == [(Events.INTEGRATION_DISCONNECTED, {"provider": "slack", "workspace_id": 5})]


async def test_disconnect_revoke_failure_tolerated(monkeypatch):
    monkeypatch.setattr(svc, "_resolve_workspace_id", lambda email: 5)
    monkeypatch.setattr(svc.integration_repo, "find_by_workspace_provider", lambda ws, p: _row())

    async def fake_revoke(provider, access_token):
        raise RuntimeError("revoke failed")

    monkeypatch.setattr(oauth, "revoke_access_token", fake_revoke)
    deleted = {"called": False}

    def fake_delete(ws, p):
        deleted["called"] = True
        return True

    monkeypatch.setattr(svc.integration_repo, "delete_by_workspace_provider", fake_delete)
    app, emitted = _app()
    await svc.disconnect("a@b.com", "slack", _request(app))
    assert deleted["called"] is True
    assert emitted == [(Events.INTEGRATION_DISCONNECTED, {"provider": "slack", "workspace_id": 5})]


async def test_disconnect_no_workspace(monkeypatch):
    monkeypatch.setattr(svc, "_resolve_workspace_id", lambda email: None)
    app, _ = _app()
    with pytest.raises(HTTPException) as exc:
        await svc.disconnect("a@b.com", "slack", _request(app))
    assert exc.value.status_code == 404


async def test_disconnect_not_connected(monkeypatch):
    monkeypatch.setattr(svc, "_resolve_workspace_id", lambda email: 5)
    monkeypatch.setattr(svc.integration_repo, "find_by_workspace_provider", lambda ws, p: None)
    app, _ = _app()
    with pytest.raises(HTTPException) as exc:
        await svc.disconnect("a@b.com", "slack", _request(app))
    assert exc.value.status_code == 404


# ─── refresh transitions ──────────────────────────────────────────────────────

async def test_refresh_row_success(monkeypatch):
    row = _row(provider="clickup")
    row["expires_at"] = datetime(2000, 1, 1)

    async def fake_refresh(provider, refresh_token):
        return {
            "access_token": "new-tok",
            "refresh_token": "new-rt",
            "expires_at": 2000000000,
            "scope": "tasks:read tasks:write",
        }

    monkeypatch.setattr(oauth, "refresh_access_token", fake_refresh)
    updated_args = {}

    def fake_update_token(iid, token_encrypted, account_name, expires_at, status, last_synced_at):
        updated_args.update(
            {
                "iid": iid,
                "token_encrypted": token_encrypted,
                "account_name": account_name,
                "expires_at": expires_at,
                "status": status,
                "last_synced_at": last_synced_at,
            }
        )
        return {**row, "status": status, "expires_at": expires_at}

    monkeypatch.setattr(svc.integration_repo, "update_token", fake_update_token)
    app, emitted = _app()
    result = await svc._refresh_row(row, app)
    assert updated_args["iid"] == 1
    assert updated_args["status"] == IntegrationStatus.connected.value
    assert updated_args["account_name"] == "Acme"
    assert updated_args["last_synced_at"] is None
    decrypted = decrypt_token_payload(updated_args["token_encrypted"])
    assert decrypted["access_token"] == "new-tok"
    assert decrypted["refresh_token"] == "new-rt"
    assert updated_args["expires_at"] == datetime.fromtimestamp(2000000000, tz=timezone.utc).replace(tzinfo=None)
    assert emitted == [
        (
            Events.INTEGRATION_TOKEN_REFRESHED,
            {"provider": "clickup", "workspace_id": 5, "status": IntegrationStatus.connected.value},
        )
    ]
    assert result["status"] == IntegrationStatus.connected.value


async def test_refresh_row_failure_marks_expired(monkeypatch):
    row = _row(provider="clickup")

    async def fake_refresh(provider, refresh_token):
        raise RuntimeError("token expired")

    monkeypatch.setattr(oauth, "refresh_access_token", fake_refresh)
    updated_status = {}

    def fake_update_status(iid, status):
        updated_status["iid"], updated_status["status"] = iid, status
        return {**row, "status": status}

    monkeypatch.setattr(svc.integration_repo, "update_status", fake_update_status)
    app, emitted = _app()
    result = await svc._refresh_row(row, app)
    assert updated_status == {"iid": 1, "status": IntegrationStatus.expired.value}
    assert emitted == [
        (
            Events.INTEGRATION_TOKEN_REFRESHED,
            {"provider": "clickup", "workspace_id": 5, "status": IntegrationStatus.expired.value},
        )
    ]
    assert result["status"] == IntegrationStatus.expired.value


async def test_refresh_row_no_refresh_token(monkeypatch):
    row = _row()
    row["token_encrypted"] = encrypt_token_payload({"access_token": "tok"})
    app, _ = _app()
    result = await svc._refresh_row(row, app)
    assert result is None


async def test_refresh_integration_no_refresh_token(monkeypatch):
    row = _row()
    row["token_encrypted"] = encrypt_token_payload({"access_token": "tok"})
    monkeypatch.setattr(svc, "_resolve_workspace_id", lambda email: 5)
    monkeypatch.setattr(svc.integration_repo, "find_by_workspace_provider", lambda ws, p: row)
    app, _ = _app()
    with pytest.raises(HTTPException) as exc:
        await svc.refresh_integration("a@b.com", "slack", _request(app))
    assert exc.value.status_code == 400
    assert "no refresh token" in exc.value.detail


async def test_refresh_integration_not_found(monkeypatch):
    monkeypatch.setattr(svc, "_resolve_workspace_id", lambda email: 5)
    monkeypatch.setattr(svc.integration_repo, "find_by_workspace_provider", lambda ws, p: None)
    app, _ = _app()
    with pytest.raises(HTTPException) as exc:
        await svc.refresh_integration("a@b.com", "slack", _request(app))
    assert exc.value.status_code == 404


# ─── provider call guard (network failures → 502) ─────────────────────────────

async def test_provider_call_wraps_network_error():
    import httpx

    async def boom():
        raise httpx.ConnectTimeout("timed out")

    with pytest.raises(HTTPException) as exc:
        await svc._provider_call("discord", boom())
    assert exc.value.status_code == 502
    assert "discord" in exc.value.detail


async def test_provider_call_passes_through_success():
    result = await svc._provider_call("taiga", _async_return([{"id": "1"}]))
    assert result == [{"id": "1"}]


async def _async_return(value):
    return value