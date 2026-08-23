import pytest
from litestar.exceptions import HTTPException

from lib.crypto import encrypt_token_payload
from services import members as svc

PM_MEMBER = {
    "id": "1",
    "name": "Ada Lovelace",
    "username": "ada",
    "email": "ada@example.com",
    "avatar": "http://img/ada.png",
}
COMM_MEMBER = {
    "id": "100",
    "name": "Ada",
    "username": "ada",
    "email": "",
    "avatar": "",
}


def _row(provider):
    return {
        "id": 1,
        "workspace_id": 5,
        "provider": provider,
        "token_encrypted": encrypt_token_payload({"access_token": "tok", "user_id": 99}),
        "status": "connected",
        "expires_at": None,
    }


@pytest.fixture
def stub_fetchers(monkeypatch):
    async def fake_taiga(access_token, base_url, project_id):
        return [PM_MEMBER]

    async def fake_channel_guild(access_token, bot_token, channel_id):
        return "200"

    async def fake_discord(access_token, bot_token, guild_id):
        return [COMM_MEMBER]

    monkeypatch.setattr(svc.oauth, "list_taiga_project_members", fake_taiga)
    monkeypatch.setattr(svc.oauth, "get_discord_channel_guild", fake_channel_guild)
    monkeypatch.setattr(svc.oauth, "list_discord_guild_members", fake_discord)


@pytest.fixture
def stub_credentials(monkeypatch):
    monkeypatch.setattr(svc.user_repo, "find_by_email", lambda email: {"id": 1})
    monkeypatch.setattr(svc.workspace_repo, "find_by_user_id", lambda uid: {"id": 5})
    monkeypatch.setattr(
        svc.integration_repo, "find_by_workspace_provider", lambda ws, p: _row(p)
    )
    monkeypatch.setattr(svc.workspace_member_repo, "add", lambda *a, **k: {"id": 1})


async def test_create_matched_users_creates_pending_user(stub_fetchers, stub_credentials, monkeypatch):
    created_users = []

    def fake_create_pending_user(email, name=None, avatar=None):
        created_users.append({"email": email, "name": name, "avatar": avatar})
        return {"id": 42, "email": email}

    def fake_find_identity(provider, external_id):
        return None

    def fake_find_user_by_email(email):
        if email == "ada@example.com":
            return None
        return {"id": 1}

    identities = []

    def fake_create_identity(user_id, provider, external_id, email, name, username, avatar):
        identities.append((provider, external_id, user_id))
        return {"id": 1}

    monkeypatch.setattr(svc.user_repo, "create_pending_user", fake_create_pending_user)
    monkeypatch.setattr(svc.external_identity_repo, "find_by_provider_external_id", fake_find_identity)
    monkeypatch.setattr(svc.user_repo, "find_by_email", fake_find_user_by_email)
    monkeypatch.setattr(svc.external_identity_repo, "create", fake_create_identity)

    result = await svc.create_matched_users(
        email="owner@example.com",
        pm_provider="taiga",
        comm_provider="discord",
        project_id="10",
        channel_id="20",
        matches=[{"pm_member_id": "1", "comm_member_id": "100"}],
    )

    assert result == [{"user_id": 42, "pm_member_id": "1", "comm_member_id": "100"}]
    assert created_users == [
        {"email": "ada@example.com", "name": "Ada Lovelace", "avatar": "http://img/ada.png"}
    ]
    assert ("taiga", "1", 42) in identities
    assert ("discord", "100", 42) in identities


async def test_create_matched_users_reuses_existing_identity(stub_fetchers, stub_credentials, monkeypatch):
    called = {"create_pending": False, "create_identity": 0}

    def fake_find_identity(provider, external_id):
        if provider == "taiga":
            return {"id": 1, "user_id": 7}
        return None

    def fake_create_pending_user(email, name=None, avatar=None):
        called["create_pending"] = True
        return {"id": 999}

    def fake_create_identity(user_id, provider, external_id, email, name, username, avatar):
        called["create_identity"] += 1
        return {"id": 1}

    monkeypatch.setattr(svc.external_identity_repo, "find_by_provider_external_id", fake_find_identity)
    monkeypatch.setattr(svc.user_repo, "create_pending_user", fake_create_pending_user)
    monkeypatch.setattr(svc.external_identity_repo, "create", fake_create_identity)

    result = await svc.create_matched_users(
        email="owner@example.com",
        pm_provider="taiga",
        comm_provider="discord",
        project_id="10",
        channel_id="20",
        matches=[{"pm_member_id": "1", "comm_member_id": "100"}],
    )

    assert result == [{"user_id": 7, "pm_member_id": "1", "comm_member_id": "100"}]
    assert called["create_pending"] is False
    assert called["create_identity"] == 1  # only the discord identity is new


async def test_create_matched_users_rejects_unknown_member(stub_fetchers, stub_credentials):
    with pytest.raises(HTTPException) as exc:
        await svc.create_matched_users(
            email="owner@example.com",
            pm_provider="taiga",
            comm_provider="discord",
            project_id="10",
            channel_id="20",
            matches=[{"pm_member_id": "999", "comm_member_id": "100"}],
        )
    assert exc.value.status_code == 400
    assert "outside the selected scope" in exc.value.detail


async def test_create_matched_users_recognizes_owner(
    stub_fetchers, stub_credentials, monkeypatch
):
    members = []
    pending = {"called": False}

    def fake_add(workspace_id, user_id, role="member", status="pending"):
        members.append({"user_id": user_id, "role": role, "status": status})
        return {"id": 1}

    def fake_create_pending_user(email, name=None, avatar=None):
        pending["called"] = True
        return {"id": 999, "email": email}

    def fake_scope_payload(workspace_id, provider):
        return {"user_id": "1" if provider == "taiga" else "100"}

    monkeypatch.setattr(svc.workspace_member_repo, "add", fake_add)
    monkeypatch.setattr(svc.user_repo, "create_pending_user", fake_create_pending_user)
    monkeypatch.setattr(svc.external_identity_repo, "find_by_provider_external_id", lambda p, e: None)
    monkeypatch.setattr(svc.external_identity_repo, "create", lambda *a, **k: {"id": 1})
    monkeypatch.setattr(svc, "_scope_payload", fake_scope_payload)

    result = await svc.create_matched_users(
        email="owner@example.com",
        pm_provider="taiga",
        comm_provider="discord",
        project_id="10",
        channel_id="20",
        matches=[{"pm_member_id": "1", "comm_member_id": "100"}],
    )

    assert result == [{"user_id": 1, "pm_member_id": "1", "comm_member_id": "100"}]
    assert pending["called"] is False
    assert members == [{"user_id": 1, "role": "owner", "status": "active"}]


async def test_create_matched_users_links_workspace_member(
    stub_fetchers, stub_credentials, monkeypatch
):
    members = []

    def fake_add(workspace_id, user_id, role="member", status="pending"):
        members.append({"workspace_id": workspace_id, "user_id": user_id, "role": role, "status": status})
        return {"id": 1}

    monkeypatch.setattr(svc.workspace_member_repo, "add", fake_add)
    monkeypatch.setattr(svc.user_repo, "create_pending_user", lambda email, name=None, avatar=None: {"id": 42, "email": email})
    monkeypatch.setattr(svc.external_identity_repo, "find_by_provider_external_id", lambda p, e: None)
    monkeypatch.setattr(svc.user_repo, "find_by_email", lambda email: None if email == "ada@example.com" else {"id": 1})
    monkeypatch.setattr(svc.external_identity_repo, "create", lambda *a, **k: {"id": 1})

    await svc.create_matched_users(
        email="owner@example.com",
        pm_provider="taiga",
        comm_provider="discord",
        project_id="10",
        channel_id="20",
        matches=[{"pm_member_id": "1", "comm_member_id": "100"}],
    )

    assert members == [
        {"workspace_id": 5, "user_id": 42, "role": "member", "status": "pending"}
    ]


async def test_fetch_scope_members_requires_connected(stub_credentials, monkeypatch):
    monkeypatch.setattr(
        svc.integration_repo, "find_by_workspace_provider", lambda ws, p: None
    )
    with pytest.raises(HTTPException) as exc:
        await svc._fetch_scope_members(
            5, "owner@example.com", "taiga", "10", is_project=True
        )
    assert exc.value.status_code == 404
