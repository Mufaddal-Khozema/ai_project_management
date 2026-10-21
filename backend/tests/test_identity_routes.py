from datetime import datetime, timedelta

import pytest
from litestar.exceptions import HTTPException
from litestar.testing import TestClient

import main as main_module
from lib import service_auth
from lib.service_auth import hash_service_key
from schemas.identity import (
    IdentityEntitlements,
    IdentityIntegration,
    IdentityUser,
    IdentityWorkspace,
    ResolveIdentityResponse,
)
from services import identity as identity_service


RAW_KEY = "svc_test-key-for-identity-resolve"


def _service_headers(raw_key=RAW_KEY):
    return {"Authorization": f"Bearer {raw_key}"}


def _user_jwt_headers():
    from lib.auth import jwt_auth

    token = jwt_auth.create_token(
        identifier="test@example.com",
        token_expiration=timedelta(minutes=15),
    )
    return {"Authorization": f"Bearer {token}"}


def _payload():
    return ResolveIdentityResponse(
        linked=True,
        user=IdentityUser(
            uuid="123e4567-e89b-12d3-a456-426614174000",
            email="ada@example.com",
            status="email_verified",
            name="Ada",
            avatar=None,
        ),
        workspace=IdentityWorkspace(
            uuid="223e4567-e89b-12d3-a456-426614174001",
            company_name="Acme",
        ),
        entitlements=IdentityEntitlements(has_subscription=True, onboarding_completed=True),
        integrations=[
            IdentityIntegration(
                provider="taiga",
                account_name="acme",
                status="connected",
                token_encrypted="enc-blob",
            )
        ],
        cached_at=datetime(2024, 1, 1),
    )


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setattr(main_module, "create_all_tables", lambda: None)
    monkeypatch.setattr(main_module, "start_background_tasks", lambda app: None)

    async def fake_find_by_key_hash(key_hash):
        if key_hash == hash_service_key(RAW_KEY):
            return {"id": 1, "service_name": "discord-bot", "key_hash": key_hash}
        return None

    monkeypatch.setattr(
        service_auth.service_api_key_repo,
        "find_by_key_hash",
        fake_find_by_key_hash,
    )
    app = main_module.create_app()
    with TestClient(app) as test_client:
        yield test_client


def _body():
    return {"provider": "discord", "external_id": "123", "guild_id": "g1", "channel_id": "c1"}


def test_resolve_returns_servicing_context(client, monkeypatch):
    async def fake_resolve(**kwargs):
        return _payload()

    monkeypatch.setattr(identity_service, "resolve_identity", fake_resolve)
    r = client.post("/api/identity/resolve", json=_body(), headers=_service_headers())
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["linked"] is True
    assert body["user"]["email"] == "ada@example.com"
    assert body["workspace"]["company_name"] == "Acme"
    assert body["entitlements"]["has_subscription"] is True
    assert body["integrations"][0]["provider"] == "taiga"


def test_resolve_requires_service_key(client):
    assert client.post("/api/identity/resolve", json=_body()).status_code == 401


def test_resolve_rejects_unknown_key(client):
    r = client.post("/api/identity/resolve", json=_body(), headers=_service_headers("svc_bogus"))
    assert r.status_code == 401


def test_resolve_rejects_user_jwt_without_service_key(client, monkeypatch):
    async def fake_resolve(**kwargs):
        return _payload()

    monkeypatch.setattr(identity_service, "resolve_identity", fake_resolve)
    r = client.post("/api/identity/resolve", json=_body(), headers=_user_jwt_headers())
    assert r.status_code == 401


def test_resolve_unlinked_maps_to_404(client, monkeypatch):
    async def boom(**kwargs):
        raise HTTPException(status_code=404, detail="Identity not linked.")

    monkeypatch.setattr(identity_service, "resolve_identity", boom)
    r = client.post("/api/identity/resolve", json=_body(), headers=_service_headers())
    assert r.status_code == 404


def test_resolve_validates_request_body(client):
    r = client.post(
        "/api/identity/resolve", json={"provider": "", "external_id": ""}, headers=_service_headers()
    )
    assert r.status_code == 400
