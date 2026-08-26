from urllib.parse import parse_qs, urlparse

import base64
import json

import httpx
import pytest

from lib import oauth
from config import settings


def _qs(url: str) -> dict[str, list[str]]:
    return parse_qs(urlparse(url).query)


def _jwt(payload: dict) -> str:
    header = base64.urlsafe_b64encode(json.dumps({"alg": "HS256"}).encode()).rstrip(b"=").decode()
    body = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=").decode()
    return f"{header}.{body}.sig"


def test_slack_authorization_url():
    url = oauth._slack_authorization_url("http://test-api/cb", "state123")
    assert url.startswith("https://slack.com/oauth/v2/authorize?")
    qs = _qs(url)
    assert qs["client_id"] == ["slack-test-id"]
    assert qs["scope"] == [oauth.SLACK_SCOPES]
    assert qs["redirect_uri"] == ["http://test-api/cb"]
    assert qs["state"] == ["state123"]


def test_jira_authorization_url():
    url = oauth._jira_authorization_url("http://test-api/cb", "state123")
    assert url.startswith("https://auth.atlassian.com/authorize?")
    qs = _qs(url)
    assert qs["audience"] == ["api.atlassian.com"]
    assert qs["client_id"] == ["jira-test-id"]
    assert qs["response_type"] == ["code"]
    assert qs["redirect_uri"] == ["http://test-api/cb"]
    assert qs["state"] == ["state123"]


def test_clickup_authorization_url():
    url = oauth._clickup_authorization_url("http://test-api/cb", "state123")
    assert url.startswith("https://app.clickup.com/api?")
    qs = _qs(url)
    assert qs["client_id"] == ["clickup-test-id"]
    assert qs["redirect_uri"] == ["http://test-api/cb"]
    assert qs["state"] == ["state123"]


def test_taiga_authenticate_request_shape(monkeypatch):
    captured = {}

    async def fake_post(self, url, json=None, **kwargs):
        captured["url"] = url
        captured["json"] = json
        return httpx.Response(
            200,
            json={"token": "taiga-tok", "refresh": "taiga-rt"},
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    token = __import__("asyncio").run(oauth.taiga_authenticate("bob", "secret"))
    assert captured["url"] == f"{settings.taiga_base_url}/api/v1/auth"
    assert captured["json"] == {"username": "bob", "password": "secret", "type": "normal"}
    assert token["access_token"] == "taiga-tok"
    assert token["refresh_token"] == "taiga-rt"
    assert token["account_name"] == "bob"


def test_taiga_authenticate_invalid_credentials(monkeypatch):
    async def fake_post(self, url, json=None, **kwargs):
        return httpx.Response(403, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    with pytest.raises(oauth.TaigaAuthError):
        __import__("asyncio").run(oauth.taiga_authenticate("bob", "wrong"))


def test_taiga_token_uses_earliest_expiry():
    access = _jwt({"token_type": "access", "exp": 2000000000})
    refresh = _jwt({"token_type": "refresh", "exp": 1800000000})
    token = oauth._taiga_token({"token": access, "refresh": refresh}, username="bob")
    assert token["expires_at"] == 1800000000


def test_taiga_token_access_only_expiry():
    access = _jwt({"token_type": "access", "exp": 2000000000})
    token = oauth._taiga_token({"token": access})
    assert token["expires_at"] == 2000000000
    assert token.get("refresh_token") is None


def test_taiga_token_no_expiry():
    token = oauth._taiga_token({"token": "not-a-jwt"})
    assert token.get("expires_at") is None


def test_taiga_refresh_request_shape(monkeypatch):
    captured = {}

    async def fake_post(self, url, json=None, **kwargs):
        captured["url"] = url
        captured["json"] = json
        return httpx.Response(
            200,
            json={"token": "new-tok", "refresh": "new-rt"},
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    token = __import__("asyncio").run(oauth.refresh_access_token("taiga", "old-rt"))
    assert captured["url"] == f"{settings.taiga_base_url}/api/v1/auth/token/refresh"
    assert captured["json"] == {"refresh": "old-rt"}
    assert token["access_token"] == "new-tok"
    assert token["refresh_token"] == "new-rt"


async def test_teams_authorization_url():
    url = await oauth.get_authorization_url("teams", "http://test-api/cb", "state123")
    assert url.startswith("https://login.microsoftonline.com/common/oauth2/v2.0/authorize?")
    qs = _qs(url)
    assert qs["client_id"] == ["ms-test-id"]
    assert qs["redirect_uri"] == ["http://test-api/cb"]
    assert qs["state"] == ["state123"]


async def test_discord_authorization_url():
    url = await oauth.get_authorization_url("discord", "http://test-api/cb", "state123")
    assert url.startswith("https://discord.com/api/oauth2/authorize?")
    qs = _qs(url)
    assert qs["client_id"] == ["discord-test-id"]
    assert qs["redirect_uri"] == ["http://test-api/cb"]
    assert qs["state"] == ["state123"]


def test_get_authorization_url_unknown_provider():
    with pytest.raises(oauth.UnsupportedProviderError):
        oauth._get_client("not-a-provider")


def test_clickup_access_token_request_shape(monkeypatch):
    captured = {}

    async def fake_exchange(url, data):
        captured["url"] = url
        captured["data"] = data
        return {"access_token": "tok", "refresh_token": "rt", "expires_in": 3600}

    monkeypatch.setattr(oauth, "_token_exchange", fake_exchange)
    token = __import__("asyncio").run(oauth._clickup_access_token("code1", "http://test-api/cb"))
    assert captured["url"] == "https://api.clickup.com/api/v2/oauth/token"
    assert captured["data"] == {
        "client_id": "clickup-test-id",
        "client_secret": "clickup-test-secret",
        "code": "code1",
        "grant_type": "authorization_code",
    }
    assert token["access_token"] == "tok"


def test_slack_access_token_ok(monkeypatch):
    async def fake_exchange(url, data):
        return {
            "ok": True,
            "access_token": "bot-token",
            "scope": "channels:read",
            "authed_user": {"access_token": "user-token", "scope": "chat:write"},
            "team": {"name": "Acme"},
        }

    monkeypatch.setattr(oauth, "_token_exchange", fake_exchange)
    token = __import__("asyncio").run(oauth._slack_access_token("code1", "http://test-api/cb"))
    assert token["access_token"] == "user-token"
    assert token["scope"] == "chat:write"
    assert token["account_name"] == "Acme"


def test_slack_access_token_error(monkeypatch):
    async def fake_exchange(url, data):
        return {"ok": False, "error": "invalid_code"}

    monkeypatch.setattr(oauth, "_token_exchange", fake_exchange)
    with pytest.raises(oauth.OAuth2RequestError):
        __import__("asyncio").run(oauth._slack_access_token("bad", "http://test-api/cb"))


def test_jira_access_token_request_shape(monkeypatch):
    captured = {}

    async def fake_exchange(url, data):
        captured["url"] = url
        captured["data"] = data
        return {"access_token": "tok", "refresh_token": "rt", "expires_in": 3600}

    monkeypatch.setattr(oauth, "_token_exchange", fake_exchange)
    token = __import__("asyncio").run(oauth._jira_access_token("code1", "http://test-api/cb"))
    assert captured["url"] == "https://auth.atlassian.com/oauth/token"
    assert captured["data"]["grant_type"] == "authorization_code"
    assert captured["data"]["redirect_uri"] == "http://test-api/cb"
    assert token["access_token"] == "tok"


def test_refresh_access_token_unsupported_provider():
    with pytest.raises(oauth.UnsupportedProviderError):
        __import__("asyncio").run(oauth.refresh_access_token("slack", "rt"))


def test_refresh_access_token_clickup_request_shape(monkeypatch):
    captured = {}

    async def fake_exchange(url, data):
        captured["url"] = url
        captured["data"] = data
        return {"access_token": "new-tok", "refresh_token": "new-rt", "expires_in": 3600}

    monkeypatch.setattr(oauth, "_token_exchange", fake_exchange)
    token = __import__("asyncio").run(oauth.refresh_access_token("clickup", "old-rt"))
    assert captured["url"] == "https://api.clickup.com/api/v2/oauth/token"
    assert captured["data"] == {
        "client_id": "clickup-test-id",
        "client_secret": "clickup-test-secret",
        "grant_type": "refresh_token",
        "refresh_token": "old-rt",
    }
    assert token["access_token"] == "new-tok"


async def test_revoke_access_token_slack(monkeypatch):
    calls = []

    async def fake_post(self, url, data=None, **kwargs):
        calls.append((url, data))
        return httpx.Response(200, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    await oauth.revoke_access_token("slack", "tok123")
    assert calls == [("https://slack.com/api/auth.revoke", {"token": "tok123"})]


async def test_revoke_access_token_other_provider_noop(monkeypatch):
    async def fake_post(self, url, data=None, **kwargs):
        raise AssertionError("should not post for non-slack providers")

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    await oauth.revoke_access_token("jira", "tok123")


# ─── Discord guild / channel listing ─────────────────────────────────────────

def _guild(id_, name):
    return {"id": id_, "name": name}


def test_list_discord_guilds_filters_by_bot(monkeypatch):
    async def fake_get(self, url, **kwargs):
        if "Bot " in self.headers.get("Authorization", ""):
            return httpx.Response(
                200, json=[_guild("1", "Bot Server"), _guild("3", "Also Bot")],
                request=httpx.Request("GET", url),
            )
        return httpx.Response(
            200,
            json=[_guild("1", "Shared"), _guild("2", "No Bot"), _guild("3", "Shared 2")],
            request=httpx.Request("GET", url),
        )

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)
    result = __import__("asyncio").run(oauth.list_discord_guilds("user-tok", "bot-tok"))
    assert result == [
        {"id": "1", "name": "Shared"},
        {"id": "3", "name": "Shared 2"},
    ]


def test_list_discord_guilds_no_bot_returns_all(monkeypatch):
    async def fake_get(self, url, **kwargs):
        return httpx.Response(
            200,
            json=[_guild("1", "A"), _guild("2", "B")],
            request=httpx.Request("GET", url),
        )

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)
    result = __import__("asyncio").run(oauth.list_discord_guilds("user-tok"))
    assert result == [{"id": "1", "name": "A"}, {"id": "2", "name": "B"}]


def test_list_discord_channels_only_text_rooms(monkeypatch):
    async def fake_guilds(access_token, bot_token=None):
        return [{"id": "1", "name": "Server"}]

    async def fake_get(self, url, **kwargs):
        return httpx.Response(
            200,
            json=[
                {"id": "10", "name": "general", "type": 0},
                {"id": "11", "name": "voice-room", "type": 2},
                {"id": "12", "name": "announcements", "type": 5},
                {"id": "13", "name": "category", "type": 4},
            ],
            request=httpx.Request("GET", url),
        )

    monkeypatch.setattr(oauth, "list_discord_guilds", fake_guilds)
    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    result = __import__("asyncio").run(
        oauth.list_discord_channels("user-tok", "bot-tok")
    )
    assert result == [
        {"id": "10", "name": "general", "guild_id": "1"},
    ]


def test_get_discord_channel_guild_returns_guild(monkeypatch):
    async def fake_get(self, url, **kwargs):
        return httpx.Response(
            200, json={"id": "10", "guild_id": "1"}, request=httpx.Request("GET", url)
        )

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)
    result = __import__("asyncio").run(
        oauth.get_discord_channel_guild("user-tok", "bot-tok", "10")
    )
    assert result == "1"


def test_get_discord_channel_guild_missing_returns_none(monkeypatch):
    async def fake_get(self, url, **kwargs):
        return httpx.Response(404, json={}, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)
    result = __import__("asyncio").run(
        oauth.get_discord_channel_guild("user-tok", "bot-tok", "10")
    )
    assert result is None