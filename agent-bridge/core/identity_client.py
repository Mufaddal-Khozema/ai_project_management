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

    def resolve_discord_identity(
        self,
        external_id: str,
        guild_id: str | None = None,
        channel_id: str | None = None,
    ) -> IdentityResult:
        """Resolve a Discord user ID against the root backend.

        Returns an IdentityResult. When linked=False, the user has not connected
        their Discord account to a workspace in the root dashboard.
        """
        provider = "discord"
        cache_key = (provider, str(external_id))
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
            "provider": provider,
            "external_id": str(external_id),
            "guild_id": str(guild_id) if guild_id else None,
            "channel_id": str(channel_id) if channel_id else None,
        }

        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=300)
        except requests.RequestException as e:
            logger.error("Root backend identity service unreachable: %s", e)
            raise RuntimeError(f"Backend identity service unreachable: {e}") from e

        if resp.status_code == 200:
            data = resp.json()
            result = IdentityResult(
                linked=data.get("linked", True),
                user=data.get("user") or {},
                workspace=data.get("workspace"),
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

    def get_taiga_credentials(self, result: IdentityResult) -> dict[str, Any] | None:
        """Helper to find Taiga integration from an IdentityResult and decrypt it."""
        for integration in result.integrations:
            if integration.get("provider") == "taiga":
                token_encrypted = integration.get("token_encrypted")
                if token_encrypted:
                    try:
                        return self.decrypt_token(token_encrypted)
                    except Exception as e:
                        logger.warning("Could not decrypt Taiga token for workspace: %s", e)
        return None
