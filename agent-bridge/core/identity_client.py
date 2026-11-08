"""
core/identity_client.py — Client for root backend's identity & authorization resolution API.

Replaces the duplicate auth-service with calls to the canonical root backend
(Litestar on port 8000) at:
    POST /api/identity/resolve

Authenticates with a service-to-service key (Authorization: Bearer svc_...)
and decrypts integration credentials via Fernet (INTEGRATION_TOKEN_ENCRYPTION_KEY).
"""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any

import requests
from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger("agent_bridge.identity_client")


@dataclass
class IdentityResult:
    linked: bool
    user: dict[str, Any] = field(default_factory=dict)
    workspace: dict[str, Any] | None = None
    project: dict[str, Any] | None = None
    entitlements: dict[str, Any] = field(default_factory=dict)
    integrations: list[dict[str, Any]] = field(default_factory=list)
    error_detail: str | None = None

    @property
    def has_subscription(self) -> bool:
        return bool(self.entitlements.get("has_subscription", False))

    @property
    def user_name(self) -> str:
        return self.user.get("name") or self.user.get("email") or "Unknown"

    @property
    def company_name(self) -> str:
        return self.workspace.get("company_name", "") if self.workspace else ""

    @property
    def workspace_uuid(self) -> str | None:
        if self.workspace and "uuid" in self.workspace:
            return str(self.workspace["uuid"])
        return None

    @property
    def org_id(self) -> str | None:
        return self.workspace_uuid

    @property
    def project_slug(self) -> str | None:
        if self.project:
            return self.project.get("project_slug") or self.project.get("project_id")
        return None


class IdentityClient:
    def __init__(
        self,
        backend_url: str = "http://127.0.0.1:8000",
        service_api_key: str = "",
        fernet_key: str = "",
        cache_ttl_seconds: float = 30.0,
    ):
        self.backend_url = backend_url.rstrip("/")
        self.service_api_key = service_api_key
        self.fernet_key = fernet_key
        self.cache_ttl_seconds = cache_ttl_seconds
        self._cache: dict[tuple[str, str], tuple[IdentityResult, float]] = {}
        self._fernet: Fernet | None = None

        if self.fernet_key:
            try:
                self._fernet = Fernet(self.fernet_key.encode())
            except Exception as e:
                logger.warning("Could not initialize Fernet with provided key: %s", e)

    def is_configured(self) -> bool:
        """True if the backend URL and service key are set."""
        return bool(self.backend_url and self.service_api_key)

    def decrypt_token(self, token_encrypted: str) -> dict[str, Any]:
        """Decrypt a Fernet-encrypted integration token payload."""
        if not self._fernet:
            if not self.fernet_key:
                raise ValueError("INTEGRATION_TOKEN_ENCRYPTION_KEY is not configured on IdentityClient")
            self._fernet = Fernet(self.fernet_key.encode())

        try:
            raw = self._fernet.decrypt(token_encrypted.encode("utf-8"))
            return json.loads(raw.decode("utf-8"))
        except InvalidToken as e:
            logger.error("Failed to decrypt integration token payload: InvalidToken")
            raise ValueError("Invalid integration token payload") from e
        except Exception as e:
            logger.exception("Unexpected error decrypting integration token payload")
            raise ValueError(f"Failed to decrypt token: {e}") from e

    def resolve_identity(
        self,
        provider: str,
        external_id: str,
        guild_id: str | None = None,
        channel_id: str | None = None,
    ) -> IdentityResult:
        """Resolve any chat provider (Discord, Slack) user ID against the root backend."""
        clean_provider = provider.lower().strip()
        cache_key = (clean_provider, str(external_id))
        cached = self._cache.get(cache_key)
        if cached and (time.monotonic() - cached[1]) < self.cache_ttl_seconds:
            return cached[0]

        url = f"{self.backend_url}/api/identity/resolve"
        headers = {
            "Authorization": f"Bearer {self.service_api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        payload = {
            "provider": clean_provider,
            "external_id": str(external_id),
            "guild_id": str(guild_id) if guild_id else None,
            "channel_id": str(channel_id) if channel_id else None,
        }

        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=30)
        except requests.RequestException as e:
            logger.error("Root backend identity service unreachable: %s", e)
            raise RuntimeError(f"Backend identity service unreachable: {e}") from e

        if resp.status_code == 200:
            data = resp.json()
            result = IdentityResult(
                linked=data.get("linked", True),
                user=data.get("user") or {},
                workspace=data.get("workspace"),
                project=data.get("project"),
                entitlements=data.get("entitlements") or {},
                integrations=data.get("integrations") or [],
            )
            self._cache[cache_key] = (result, time.monotonic())
            return result

        if resp.status_code == 404:
            detail = resp.json().get("detail", "Identity not linked.")
            result = IdentityResult(linked=False, error_detail=detail)
            self._cache[cache_key] = (result, time.monotonic())
            return result

        if resp.status_code == 401:
            logger.error("Root backend rejected service API key: 401 Unauthorized")
            raise PermissionError("Invalid service API key for root backend")

        raise RuntimeError(f"Root backend identity resolve failed ({resp.status_code}): {resp.text[:200]}")

    def resolve_discord_identity(
        self,
        external_id: str,
        guild_id: str | None = None,
        channel_id: str | None = None,
    ) -> IdentityResult:
        """Resolve a Discord user ID against the root backend."""
        return self.resolve_identity("discord", external_id, guild_id, channel_id)

    def resolve_slack_identity(
        self,
        external_id: str,
        team_id: str | None = None,
        channel_id: str | None = None,
    ) -> IdentityResult:
        """Resolve a Slack user ID against the root backend."""
        return self.resolve_identity("slack", external_id, team_id, channel_id)

    def get_integration_credentials(self, result: IdentityResult, provider: str) -> dict[str, Any] | None:
        """Helper to find any integration by provider from an IdentityResult and decrypt it."""
        clean_provider = provider.lower().strip()
        for integration in result.integrations:
            if integration.get("provider", "").lower() == clean_provider:
                token_encrypted = integration.get("token_encrypted")
                if token_encrypted:
                    try:
                        return self.decrypt_token(token_encrypted)
                    except Exception as e:
                        logger.warning("Could not decrypt %s token for workspace: %s", clean_provider, e)
        return None

    def get_taiga_credentials(self, result: IdentityResult) -> dict[str, Any] | None:
        """Helper to find Taiga integration from an IdentityResult and decrypt it."""
        return self.get_integration_credentials(result, "taiga")

    def get_jira_credentials(self, result: IdentityResult) -> dict[str, Any] | None:
        """Helper to find Jira integration from an IdentityResult and decrypt it."""
        return self.get_integration_credentials(result, "jira")

    def list_taiga_projects(self, taiga_creds: dict[str, Any]) -> list[dict[str, Any]]:
        """Fetch accessible projects from Taiga using the user's decrypted access token."""
        access_token = taiga_creds.get("access_token")
        if not access_token:
            return []

        base_url = (
            taiga_creds.get("instance_url")
            or taiga_creds.get("url")
            or "https://api.taiga.io/api/v1"
        ).rstrip("/")

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        user_id = taiga_creds.get("user_id")
        url = f"{base_url}/projects"
        params = {"member": str(user_id)} if user_id else {}

        try:
            resp = requests.get(url, params=params, headers=headers, timeout=10)
            if resp.status_code == 200:
                projects = resp.json()
                if isinstance(projects, list) and projects:
                    return projects
            if params:
                resp2 = requests.get(url, headers=headers, timeout=10)
                if resp2.status_code == 200:
                    projects2 = resp2.json()
                    if isinstance(projects2, list) and projects2:
                        return projects2
        except Exception as e:
            logger.warning("Could not list Taiga projects via OAuth token: %s", e)

        return []

    def list_jira_projects(self, jira_creds: dict[str, Any]) -> list[dict[str, Any]]:
        """Fetch accessible projects from Jira using decrypted credentials."""
        token = jira_creds.get("access_token") or jira_creds.get("token")
        base_url = (jira_creds.get("url") or jira_creds.get("site_url") or "https://api.atlassian.com").rstrip("/")
        cloud_id = jira_creds.get("cloud_id")

        if cloud_id and "api.atlassian.com" in base_url:
            base_url = f"https://api.atlassian.com/ex/jira/{cloud_id}"

        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        elif jira_creds.get("email") and jira_creds.get("api_token"):
            import base64
            auth_str = f"{jira_creds['email']}:{jira_creds['api_token']}"
            encoded = base64.b64encode(auth_str.encode("utf-8")).decode("utf-8")
            headers["Authorization"] = f"Basic {encoded}"
        else:
            return []

        try:
            resp = requests.get(f"{base_url}/rest/api/3/project", headers=headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list):
                    return data
        except Exception as e:
            logger.warning("Could not list Jira projects via credentials: %s", e)
        return []

    def discover_active_project(self, result: IdentityResult) -> dict[str, Any] | None:
        """Dynamically resolve the active PM project from the user's decrypted integrations."""
        if result.project and (result.project.get("project_slug") or result.project.get("project_id")):
            return result.project

        # Check Taiga
        taiga_creds = self.get_taiga_credentials(result)
        if taiga_creds:
            projects = self.list_taiga_projects(taiga_creds)
            if projects:
                first = projects[0]
                project_dict = {
                    "provider": "taiga",
                    "project_id": str(first.get("id")),
                    "project_name": first.get("name"),
                    "project_slug": first.get("slug"),
                }
                result.project = project_dict
                logger.info(
                    "Dynamically discovered Taiga project '%s' (id: %s) for workspace '%s'",
                    project_dict["project_slug"],
                    project_dict["project_id"],
                    result.company_name,
                )
                return project_dict

        # Check Jira
        jira_creds = self.get_jira_credentials(result)
        if jira_creds:
            jira_projects = self.list_jira_projects(jira_creds)
            if jira_projects:
                first = jira_projects[0]
                project_dict = {
                    "provider": "jira",
                    "project_id": str(first.get("key") or first.get("id")),
                    "project_name": first.get("name"),
                    "project_slug": first.get("key"),
                }
                result.project = project_dict
                logger.info(
                    "Dynamically discovered Jira project '%s' (key: %s) for workspace '%s'",
                    project_dict["project_name"],
                    project_dict["project_slug"],
                    result.company_name,
                )
                return project_dict

        return None
