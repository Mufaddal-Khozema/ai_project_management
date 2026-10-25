from datetime import datetime
from types import SimpleNamespace

import pytest
from litestar.exceptions import HTTPException

from lib import identity_cache
from lib.tables import ExternalIdentity, Integration, Project, Workspace
from schemas.identity import ResolveIdentityResponse
from services import identity as identity_service


@pytest.fixture(autouse=True)
def no_cache(monkeypatch):
    store = {}

    async def fake_get(key):
        return store.get(key)

    async def fake_set(key, value, ttl_seconds=None):
        store[key] = value

    async def fake_invalidate(provider, external_id):
        store.pop(identity_cache.make_identity_key(provider, external_id), None)

    monkeypatch.setattr(identity_cache, "cache_get", fake_get)
    monkeypatch.setattr(identity_cache, "cache_set", fake_set)
    monkeypatch.setattr(identity_cache, "cache_invalidate", fake_invalidate)
    return store


def _wire(
    monkeypatch,
    link="default",
    user="default",
    workspace="default",
    integrations=None,
    subscription=None,
):
    calls = {"link": 0}
    if link == "default":
        link = {"id": 1, "user_id": 7, "provider": "discord", "external_id": "123"}
    if user == "default":
        user = {
            "id": 7,
            "uuid": "123e4567-e89b-12d3-a456-426614174000",
            "email": "ada@example.com",
            "status": "email_verified",
            "name": "Ada",
            "avatar": None,
        }
    if workspace == "default":
        workspace = {
            "id": 5,
            "uuid": "223e4567-e89b-12d3-a456-426614174001",
            "user_id": 7,
            "company_name": "Acme",
            "onboarding_completed_at": datetime(2024, 1, 1),
        }

    async def fake_link(provider, external_id):
        calls["link"] += 1
        return ExternalIdentity(**link) if link is not None else None

    async def fake_user(uid):
        return SimpleNamespace(**user) if user is not None else None

    async def fake_workspace_by_user(uid):
        return workspace

    async def fake_workspace_by_member(uid):
        return Workspace(**workspace) if workspace is not None else None

    async def fake_project_mapping(workspace_id, comm_provider, channel_id, guild_id=None):
        return None

    async def fake_integrations(ws):
        return [
            row if isinstance(row, Integration) else Integration(**row)
            for row in (integrations or [])
        ]

    async def fake_subscription(uid):
        return subscription

    monkeypatch.setattr(identity_service.external_identity_repo, "find_by_provider_external_id", fake_link)
    monkeypatch.setattr(identity_service.user_repo, "find_by_id", fake_user)
    monkeypatch.setattr(identity_service.workspace_repo, "find_by_user_id", fake_workspace_by_user)
    monkeypatch.setattr(identity_service.workspace_repo, "find_by_member_id", fake_workspace_by_member)
    monkeypatch.setattr(identity_service.integration_repo, "list_by_workspace", fake_integrations)
    monkeypatch.setattr(identity_service.payment_repo, "find_by_user_id", fake_subscription)
    monkeypatch.setattr(identity_service.project_repo, "find_by_channel", fake_project_mapping)
    return calls


async def test_resolve_happy_path(monkeypatch):
    calls = _wire(
        monkeypatch,
        integrations=[
            {
                "workspace_id": 5,
                "provider": "taiga",
                "account_name": "acme",
                "status": "connected",
                "token_encrypted": "enc-blob",
            }
        ],
        subscription={"id": 9},
    )
    result = await identity_service.resolve_identity("discord", "123", guild_id="g1", channel_id="c1")
    assert isinstance(result, ResolveIdentityResponse)
    assert result.linked is True
    assert result.user.email == "ada@example.com"
    assert result.workspace.company_name == "Acme"
    assert result.entitlements.has_subscription is True
    assert result.entitlements.onboarding_completed is True
    assert [i.provider for i in result.integrations] == ["taiga"]
    assert result.integrations[0].token_encrypted == "enc-blob"
    assert calls["link"] == 1


async def test_resolve_second_call_served_from_cache(monkeypatch, no_cache):
    calls = _wire(monkeypatch)
    first = await identity_service.resolve_identity("discord", "123")
    second = await identity_service.resolve_identity("discord", "123")
    assert calls["link"] == 1
    assert second == first


async def test_resolve_without_workspace_raises_404(monkeypatch):
    _wire(monkeypatch, workspace=None)
    with pytest.raises(HTTPException) as exc:
        await identity_service.resolve_identity("discord", "123")
    assert exc.value.status_code == 404


async def test_resolve_unlinked_raises_404(monkeypatch):
    _wire(monkeypatch, link=None)
    with pytest.raises(HTTPException) as exc:
        await identity_service.resolve_identity("discord", "999")
    assert exc.value.status_code == 404


async def test_resolve_null_user_id_raises_404(monkeypatch):
    _wire(monkeypatch, link={"id": 1, "user_id": None})
    with pytest.raises(HTTPException) as exc:
        await identity_service.resolve_identity("discord", "999")
    assert exc.value.status_code == 404


async def test_resolve_missing_user_raises_404(monkeypatch):
    _wire(monkeypatch, user=None)
    with pytest.raises(HTTPException) as exc:
        await identity_service.resolve_identity("discord", "123")
    assert exc.value.status_code == 404


async def test_resolve_unsupported_provider_raises_400(monkeypatch):
    _wire(monkeypatch)
    with pytest.raises(HTTPException) as exc:
        await identity_service.resolve_identity("carrier-pigeon", "123")
    assert exc.value.status_code == 400


async def test_invalidate_identity_drops_cache(monkeypatch, no_cache):
    calls = _wire(monkeypatch)
    await identity_service.resolve_identity("discord", "123")
    await identity_service.invalidate_identity("discord", "123")
    await identity_service.resolve_identity("discord", "123")
    assert calls["link"] == 2

MAPPING = {
    "workspace_id": 6,
    "pm_provider": "taiga",
    "project_id": "10",
    "project_name": "Website Redesign",
    "project_slug": "website-redesign",
    "comm_provider": "discord",
    "guild_id": "g1",
    "channel_id": "c1",
}


def _map_wire(monkeypatch, mapping=MAPPING, member=True, workspace=None):
    calls = _wire(monkeypatch)
    if workspace is None:
        workspace = Workspace(
            id=6,
            uuid="323e4567-e89b-12d3-a456-426614174002",
            user_id=7,
            company_name="Mapped Co",
            onboarding_completed_at=datetime(2024, 1, 1),
        )

    async def fake_mapping(workspace_id, comm_provider, channel_id, guild_id=None):
        return Project(**mapping) if mapping is not None else None

    async def fake_find_by_member(user_id):
        return workspace if member else None

    monkeypatch.setattr(identity_service.project_repo, "find_by_channel", fake_mapping)
    monkeypatch.setattr(
        identity_service.workspace_repo, "find_by_member_id", fake_find_by_member
    )
    return calls


async def test_resolve_returns_mapped_project(monkeypatch):
    _map_wire(monkeypatch)
    result = await identity_service.resolve_identity(
        "discord", "123", guild_id="g1", channel_id="c1"
    )
    assert result.project is not None
    assert result.project.project_id == "10"
    assert result.project.project_slug == "website-redesign"
    assert result.workspace.company_name == "Mapped Co"


async def test_resolve_unknown_channel_returns_no_project(monkeypatch):
    _map_wire(monkeypatch, mapping=None)
    result = await identity_service.resolve_identity(
        "discord", "123", channel_id="unknown"
    )
    assert result.project is None
    assert result.workspace.company_name == "Mapped Co"


async def test_resolve_non_member_gets_no_project(monkeypatch):
    _map_wire(monkeypatch, member=False)
    with pytest.raises(HTTPException) as exc:
        await identity_service.resolve_identity(
            "discord", "123", guild_id="g1", channel_id="c1"
        )
    assert exc.value.status_code == 404


async def test_resolve_caches_project_per_channel(monkeypatch):
    calls = _map_wire(monkeypatch)
    first = await identity_service.resolve_identity(
        "discord", "123", guild_id="g1", channel_id="c1"
    )
    assert first.project.project_id == "10"

    async def fake_mapping(workspace_id, comm_provider, channel_id, guild_id=None):
        return Project(**{**MAPPING, "channel_id": "c2", "project_id": "11"})

    monkeypatch.setattr(identity_service.project_repo, "find_by_channel", fake_mapping)
    second = await identity_service.resolve_identity(
        "discord", "123", guild_id="g1", channel_id="c2"
    )
    assert second.project.project_id == "11"
    assert calls["link"] == 2
