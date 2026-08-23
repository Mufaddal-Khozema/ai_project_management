from __future__ import annotations

import base64
import json
from typing import Any
from urllib.parse import urlencode

import httpx
from httpx_oauth.clients.discord import DiscordOAuth2
from httpx_oauth.clients.github import GitHubOAuth2
from httpx_oauth.clients.google import GoogleOAuth2
from httpx_oauth.clients.microsoft import MicrosoftGraphOAuth2
from httpx_oauth.oauth2 import BaseOAuth2, OAuth2RequestError, OAuth2Token

from config import settings

INTEGRATION_PROVIDERS = frozenset({"slack", "teams", "discord", "jira", "clickup", "taiga"})

REFRESH_SUPPORTED_PROVIDERS = frozenset({"teams", "discord", "jira", "clickup", "taiga"})

SLACK_SCOPES = "channels:read,channels:history,groups:read,users:read,team:read,chat:write"
TEAMS_SCOPES = [
    "offline_access",
    "User.Read",
    "Team.ReadBasic.All",
    "Channel.ReadBasic.All",
    "ChannelMessage.Send",
]
DISCORD_SCOPES = [
    "identify",
    "guilds",
    "guilds.members.read",
    "bot",
    "applications.commands",
]
DISCORD_PERMISSIONS = 0x10C00  # View Channels | Send Messages | Read Message History
JIRA_SCOPES = ["read:jira-user", "read:jira-work", "write:jira-work", "offline_access"]
CLICKUP_SCOPES = ["tasks:read", "tasks:write", "spaces:read", "folders:read", "lists:read", "teams:read"]


class ProviderNotConfiguredError(Exception):
    """Raised when a provider's OAuth client credentials are not set."""


class UnsupportedProviderError(Exception):
    """Raised when an unknown OAuth provider is requested."""


class TaigaAuthError(Exception):
    """Raised when Taiga rejects the supplied credentials."""


def is_provider_configured(provider: str) -> bool:
    if provider in INTEGRATION_PROVIDERS:
        return _integration_credentials(provider) is not None
    return True


def _integration_credentials(provider: str) -> tuple[str, str] | None:
    mapping = {
        "slack": (settings.slack_oauth_client_id, settings.slack_oauth_client_secret),
        "teams": (settings.microsoft_oauth_client_id, settings.microsoft_oauth_client_secret),
        "discord": (settings.discord_oauth_client_id, settings.discord_oauth_client_secret),
        "jira": (settings.atlassian_oauth_client_id, settings.atlassian_oauth_client_secret),
        "clickup": (settings.clickup_oauth_client_id, settings.clickup_oauth_client_secret),
    }
    creds = mapping.get(provider)
    if creds is None:
        raise UnsupportedProviderError(f"Unsupported OAuth provider: {provider}")
    client_id, client_secret = creds
    if not client_id or not client_secret:
        return None
    return client_id, client_secret


def _get_client(provider: str) -> BaseOAuth2:
    if provider == "google":
        return GoogleOAuth2(
            settings.google_oauth_client_id,
            settings.google_oauth_client_secret,
        )
    if provider == "github":
        return GitHubOAuth2(
            settings.github_oauth_client_id,
            settings.github_oauth_client_secret,
        )
    if provider in INTEGRATION_PROVIDERS:
        return _get_integration_client(provider)
    raise UnsupportedProviderError(f"Unsupported OAuth provider: {provider}")


def _get_integration_client(provider: str) -> BaseOAuth2:
    client_id, client_secret = _require_credentials(provider)
    if provider == "teams":
        return MicrosoftGraphOAuth2(
            client_id,
            client_secret,
            tenant=settings.microsoft_oauth_tenant,
            scopes=TEAMS_SCOPES,
        )
    if provider == "discord":
        return DiscordOAuth2(client_id, client_secret, scopes=DISCORD_SCOPES)
    raise UnsupportedProviderError(f"Unsupported OAuth provider: {provider}")


def _require_credentials(provider: str) -> tuple[str, str]:
    creds = _integration_credentials(provider)
    if creds is None:
        raise ProviderNotConfiguredError(f"OAuth provider not configured: {provider}")
    return creds


async def get_authorization_url(provider: str, redirect_uri: str, state: str) -> str:
    if provider in INTEGRATION_PROVIDERS:
        return await _integration_authorization_url(provider, redirect_uri, state)
    client = _get_client(provider)
    return await client.get_authorization_url(redirect_uri, state=state)


async def get_access_token(provider: str, code: str, redirect_uri: str) -> OAuth2Token:
    if provider in INTEGRATION_PROVIDERS:
        return await _integration_access_token(provider, code, redirect_uri)
    client = _get_client(provider)
    try:
        return await client.get_access_token(code, redirect_uri)
    except OAuth2RequestError as e:
        if e.response is not None:
            raise OAuth2RequestError(f"{e}: {e.response.text}", e.response) from e
        raise


async def get_user_info(provider: str, token: OAuth2Token) -> dict[str, Any]:
    client = _get_client(provider)
    access_token = token["access_token"]
    user_id, email = await client.get_id_email(access_token)

    if isinstance(client, GoogleOAuth2):
        async with httpx.AsyncClient() as http:
            resp = await http.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            resp.raise_for_status()
            data = resp.json()
            return {
                "sub": user_id,
                "email": email or data.get("email", ""),
                "name": data.get("name", ""),
            }

    if isinstance(client, GitHubOAuth2):
        profile = await client.get_profile(access_token)
        return {
            "sub": user_id,
            "email": email or "",
            "name": profile.get("name", "") or profile.get("login", ""),
        }

    raise UnsupportedProviderError(f"Unsupported OAuth provider: {provider}")


async def _integration_authorization_url(provider: str, redirect_uri: str, state: str) -> str:
    if provider == "slack":
        return _slack_authorization_url(redirect_uri, state)
    if provider == "jira":
        return _jira_authorization_url(redirect_uri, state)
    if provider == "clickup":
        return _clickup_authorization_url(redirect_uri, state)
    if provider == "discord":
        return _discord_authorization_url(redirect_uri, state)
    client = _get_integration_client(provider)
    return await client.get_authorization_url(redirect_uri, state=state)


def _slack_authorization_url(redirect_uri: str, state: str) -> str:
    client_id, _ = _require_credentials("slack")
    params = {
        "client_id": client_id,
        "scope": SLACK_SCOPES,
        "user_scope": SLACK_SCOPES,
        "redirect_uri": redirect_uri,
        "state": state,
    }
    return f"https://slack.com/oauth/v2/authorize?{urlencode(params)}"


def _jira_authorization_url(redirect_uri: str, state: str) -> str:
    client_id, _ = _require_credentials("jira")
    params = {
        "audience": "api.atlassian.com",
        "client_id": client_id,
        "scope": " ".join(JIRA_SCOPES),
        "redirect_uri": redirect_uri,
        "state": state,
        "response_type": "code",
        "prompt": "consent",
    }
    return f"https://auth.atlassian.com/authorize?{urlencode(params)}"


def _clickup_authorization_url(redirect_uri: str, state: str) -> str:
    client_id, _ = _require_credentials("clickup")
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "state": state,
    }
    return f"https://app.clickup.com/api?{urlencode(params)}"


def _discord_authorization_url(redirect_uri: str, state: str) -> str:
    """Build a Discord OAuth2 install URL that also adds the bot to the server.

    Keeps the existing authorize-with-code flow but requests the ``bot`` scope so
    the Discord application (bot) is installed on the chosen server in the same
    step. ``permissions`` controls what the bot can do in that server.
    """
    client_id, _ = _require_credentials("discord")
    params = {
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "scope": " ".join(DISCORD_SCOPES),
        "permissions": str(DISCORD_PERMISSIONS),
        "state": state,
    }
    return f"https://discord.com/oauth2/authorize?{urlencode(params)}"


async def _integration_access_token(provider: str, code: str, redirect_uri: str) -> OAuth2Token:
    if provider == "slack":
        return await _slack_access_token(code, redirect_uri)
    if provider == "jira":
        return await _jira_access_token(code, redirect_uri)
    if provider == "clickup":
        return await _clickup_access_token(code, redirect_uri)
    client = _get_integration_client(provider)
    return await client.get_access_token(code, redirect_uri)


async def _slack_access_token(code: str, redirect_uri: str) -> OAuth2Token:
    client_id, client_secret = _require_credentials("slack")
    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "redirect_uri": redirect_uri,
    }
    token = await _token_exchange("https://slack.com/api/oauth.v2.access", data)
    if not token.get("ok", True):
        raise OAuth2RequestError(f"Slack OAuth error: {token.get('error')}", None)
    authed = token.get("authed_user") or {}
    return OAuth2Token(
        {
            "access_token": authed.get("access_token") or token.get("access_token", ""),
            "scope": authed.get("scope") or token.get("scope", ""),
            "account_name": (token.get("team") or {}).get("name", ""),
        }
    )


async def _jira_access_token(code: str, redirect_uri: str) -> OAuth2Token:
    client_id, client_secret = _require_credentials("jira")
    data = {
        "grant_type": "authorization_code",
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "redirect_uri": redirect_uri,
    }
    token = await _token_exchange("https://auth.atlassian.com/oauth/token", data)
    return _normalize_token(token)


async def _clickup_access_token(code: str, redirect_uri: str) -> OAuth2Token:
    client_id, client_secret = _require_credentials("clickup")
    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "grant_type": "authorization_code",
    }
    token = await _token_exchange("https://api.clickup.com/api/v2/oauth/token", data)
    return _normalize_token(token)


async def _token_exchange(url: str, data: dict[str, str]) -> dict[str, Any]:
    async with httpx.AsyncClient() as http:
        resp = await http.post(url, data=data)
        resp.raise_for_status()
        return resp.json()


def _jwt_exp(access_token: str) -> float | None:
    try:
        payload = access_token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        data = json.loads(base64.urlsafe_b64decode(payload))
        return data.get("exp")
    except Exception:
        return None


def _taiga_token(token_data: dict[str, Any], username: str | None = None) -> OAuth2Token:
    access_token = token_data.get("token") or token_data.get("auth_token") or ""
    token: dict[str, Any] = {
        "access_token": access_token,
        "refresh_token": token_data.get("refresh"),
        "account_name": username,
        "user_id": token_data.get("id"),
    }
    access_exp = _jwt_exp(access_token)
    refresh_exp = _jwt_exp(token_data.get("refresh")) if token_data.get("refresh") else None
    expires = [e for e in (access_exp, refresh_exp) if e]
    if expires:
        token["expires_at"] = int(min(expires))
    return OAuth2Token(token)


async def taiga_authenticate(username: str, password: str) -> OAuth2Token:
    """Exchange Taiga credentials for an access + refresh token.

    Taiga 6 exposes no OAuth2 server, so we authenticate against its own
    token endpoint (``POST {base}/api/v1/auth``) instead.
    """
    url = f"{settings.taiga_base_url}/api/v1/auth"
    async with httpx.AsyncClient() as http:
        resp = await http.post(url, json={"username": username, "password": password, "type": "normal"})
        if resp.status_code in (400, 401, 403):
            raise TaigaAuthError("Invalid Taiga credentials")
        resp.raise_for_status()
        return _taiga_token(resp.json(), username=username)


async def _taiga_refresh_token(refresh_token: str) -> OAuth2Token:
    url = f"{settings.taiga_base_url}/api/v1/auth/token/refresh"
    async with httpx.AsyncClient() as http:
        resp = await http.post(url, json={"refresh": refresh_token})
        resp.raise_for_status()
        return _taiga_token(resp.json())


def _normalize_token(token: dict[str, Any]) -> OAuth2Token:
    return OAuth2Token(token)


async def refresh_access_token(provider: str, refresh_token: str) -> OAuth2Token:
    if provider not in REFRESH_SUPPORTED_PROVIDERS:
        raise UnsupportedProviderError(f"Provider does not support token refresh: {provider}")
    if provider in ("teams", "discord"):
        client = _get_integration_client(provider)
        return await client.refresh_token(refresh_token)
    if provider == "jira":
        client_id, client_secret = _require_credentials("jira")
        data = {
            "grant_type": "refresh_token",
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
        }
        token = await _token_exchange("https://auth.atlassian.com/oauth/token", data)
        return _normalize_token(token)
    if provider == "clickup":
        client_id, client_secret = _require_credentials("clickup")
        data = {
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }
        token = await _token_exchange("https://api.clickup.com/api/v2/oauth/token", data)
        return _normalize_token(token)
    if provider == "taiga":
        return await _taiga_refresh_token(refresh_token)
    raise UnsupportedProviderError(f"Unsupported OAuth provider: {provider}")


async def revoke_access_token(provider: str, access_token: str) -> None:
    if provider == "slack":
        async with httpx.AsyncClient() as http:
            await http.post("https://slack.com/api/auth.revoke", data={"token": access_token})
        return
    # Best-effort only: other providers lack a simple revoke endpoint; skip silently.
    return


def _discord_avatar_url(user: dict[str, Any]) -> str:
    avatar = user.get("avatar")
    user_id = user.get("id")
    if not avatar or not user_id:
        return ""
    return f"https://cdn.discordapp.com/avatars/{user_id}/{avatar}.png"


def _taiga_member(member: dict[str, Any]) -> dict[str, Any]:
    member_id = member.get("id")
    return {
        "id": str(member_id),
        "name": member.get("full_name") or member.get("username") or "",
        "username": member.get("username") or "",
        "email": member.get("email") or "",
        "avatar": member.get("photo") or "",
    }


async def list_taiga_projects(
    access_token: str, base_url: str, user_id: str | int | None = None
) -> list[dict[str, Any]]:
    """Return the Taiga projects the authenticated user is a member of."""
    headers = {"Authorization": f"Bearer {access_token}"}
    async with httpx.AsyncClient(headers=headers) as http:
        resp = await http.get(f"{base_url}/api/v1/projects", params={"member": user_id})
        resp.raise_for_status()
        projects = resp.json()
    return [
        {"id": str(p.get("id")), "name": p.get("name") or ""}
        for p in projects
        if p.get("id") is not None
    ]


async def list_taiga_project_members(
    access_token: str, base_url: str, project_id: str | int
) -> list[dict[str, Any]]:
    """Return deduplicated members of a single Taiga project."""
    headers = {"Authorization": f"Bearer {access_token}"}
    async with httpx.AsyncClient(headers=headers) as http:
        detail_resp = await http.get(f"{base_url}/api/v1/projects/{project_id}")
        if detail_resp.status_code != 200:
            return []
        members_raw = detail_resp.json().get("members", [])

    members: dict[str, dict[str, Any]] = {}
    for member in members_raw:
        member_id = member.get("id")
        if member_id is None:
            continue
        members[str(member_id)] = _taiga_member(member)
    return list(members.values())


async def list_taiga_members(
    access_token: str, base_url: str, user_id: str | int | None = None
) -> list[dict[str, Any]]:
    """Return deduplicated project members for the authenticated Taiga user.

    Projects are filtered by ``member=<user_id>`` (falls back to ``member=me``)
    and their full project detail (which includes the ``members`` array) is used
    to avoid N+1 lookups per membership.
    """
    projects = await list_taiga_projects(access_token, base_url, user_id)
    members: dict[str, dict[str, Any]] = {}
    for project in projects:
        for member in await list_taiga_project_members(access_token, base_url, project["id"]):
            members[member["id"]] = member
    return list(members.values())


async def get_discord_self(access_token: str) -> dict[str, Any]:
    """Return the authenticated Discord user's own profile."""
    async with httpx.AsyncClient(
        headers={"Authorization": f"Bearer {access_token}"}
    ) as http:
        resp = await http.get("https://discord.com/api/users/@me")
        resp.raise_for_status()
        return resp.json()


async def list_discord_guilds(
    access_token: str, bot_token: str | None = None
) -> list[dict[str, Any]]:
    """Return the Discord servers the authenticated user belongs to.

    When a bot token is supplied, only servers where the bot has been installed
    are returned (the user's guilds intersected with the bot's guilds).
    """
    async with httpx.AsyncClient(
        headers={"Authorization": f"Bearer {access_token}"}
    ) as http:
        resp = await http.get("https://discord.com/api/users/@me/guilds")
        resp.raise_for_status()
        user_guilds = resp.json()

    if not bot_token:
        return [
            {"id": str(g.get("id")), "name": g.get("name") or ""}
            for g in user_guilds
            if g.get("id")
        ]

    async with httpx.AsyncClient(
        headers={"Authorization": f"Bot {bot_token}"}
    ) as http:
        bot_resp = await http.get("https://discord.com/api/users/@me/guilds")
        if bot_resp.status_code != 200:
            bot_guild_ids: set[str] = set()
        else:
            bot_guild_ids = {
                str(g.get("id"))
                for g in bot_resp.json()
                if g.get("id")
            }

    return [
        {"id": str(g.get("id")), "name": g.get("name") or ""}
        for g in user_guilds
        if g.get("id") and str(g.get("id")) in bot_guild_ids
    ]


async def list_discord_channels(
    access_token: str, bot_token: str | None
) -> list[dict[str, Any]]:
    """Return text chat rooms across the guilds (preferring bot guilds)."""
    guilds = await list_discord_guilds(access_token, bot_token)
    channel_headers = (
        {"Authorization": f"Bot {bot_token}"}
        if bot_token
        else {"Authorization": f"Bearer {access_token}"}
    )
    channels: list[dict[str, Any]] = []
    async with httpx.AsyncClient(headers=channel_headers) as http:
        for guild in guilds:
            guild_id = guild["id"]
            resp = await http.get(
                f"https://discord.com/api/guilds/{guild_id}/channels"
            )
            if resp.status_code != 200:
                continue
            for channel in resp.json():
                if channel.get("type") != 0:
                    continue
                channel_id = channel.get("id")
                if channel_id is None:
                    continue
                channels.append(
                    {
                        "id": str(channel_id),
                        "name": channel.get("name") or "",
                        "guild_id": guild_id,
                    }
                )
    return channels


async def get_discord_channel_guild(
    access_token: str, bot_token: str | None, channel_id: str | int
) -> str | None:
    """Return the guild id a Discord chat room belongs to."""
    headers = (
        {"Authorization": f"Bot {bot_token}"}
        if bot_token
        else {"Authorization": f"Bearer {access_token}"}
    )
    async with httpx.AsyncClient(headers=headers) as http:
        resp = await http.get(f"https://discord.com/api/channels/{channel_id}")
        if resp.status_code != 200:
            return None
        guild_id = resp.json().get("guild_id")
        return str(guild_id) if guild_id else None


async def list_discord_guild_members(
    access_token: str, bot_token: str | None, guild_id: str | int
) -> list[dict[str, Any]]:
    """Return deduplicated members of a single Discord server."""
    member_headers = (
        {"Authorization": f"Bot {bot_token}"}
        if bot_token
        else {"Authorization": f"Bearer {access_token}"}
    )
    members: dict[str, dict[str, Any]] = {}
    async with httpx.AsyncClient(headers=member_headers) as http:
        resp = await http.get(
            f"https://discord.com/api/guilds/{guild_id}/members",
            params={"limit": 100},
        )
        if resp.status_code != 200:
            return []
        for member in resp.json():
            user = member.get("user") or {}
            user_id = user.get("id")
            if user_id is None:
                continue
            members[str(user_id)] = {
                "id": str(user_id),
                "name": user.get("global_name") or user.get("username") or "",
                "username": user.get("username") or "",
                "email": "",
                "avatar": _discord_avatar_url(user),
            }
    return list(members.values())


async def list_discord_members(access_token: str, bot_token: str | None) -> list[dict[str, Any]]:
    """Return deduplicated members across the servers the user belongs to.

    Guilds are listed with the user token. Members are then fetched per guild —
    preferring the bot token (most reliable) and falling back to the user token
    when the bot is not configured.
    """
    guilds = await list_discord_guilds(access_token)
    members: dict[str, dict[str, Any]] = {}
    for guild in guilds:
        for member in await list_discord_guild_members(access_token, bot_token, guild["id"]):
            members[member["id"]] = member
    return list(members.values())
