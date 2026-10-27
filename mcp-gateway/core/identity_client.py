from __future__ import annotations
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any
import httpx
from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger("mcp_gateway.identity_client")

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
    def workspace_uuid(self) -> str | None:
        if self.workspace and "uuid" in self.workspace:
            return str(self.workspace["uuid"])
        return None

    @property
    def org_id(self) -> str | None:
        return self.workspace_uuid

class IdentityClient:
    def __init__(
        self,
        backend_url: str = "http://localhost:8000",
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
                self._fernet = Fernet(self.fernet_key.encode("utf-8"))
            except Exception as e:
                logger.warning("Could not initialize Fernet key: %s", e)

    def decrypt_token(self, token_encrypted: str) -> dict[str, Any]:
        """Decrypt a Fernet-encrypted token into a dict (e.g. {'token': ..., 'refresh': ...})."""
        if not self._fernet:
            if not self.fernet_key:
                raise ValueError("INTEGRATION_TOKEN_ENCRYPTION_KEY is not configured")
            self._fernet = Fernet(self.fernet_key.encode("utf-8"))

        try:
            raw = self._fernet.decrypt(token_encrypted.encode("utf-8"))
            return json.loads(raw.decode("utf-8"))
        except InvalidToken:
            logger.error("Failed to decrypt integration token: InvalidToken")
            raise ValueError("Invalid Fernet token")
        except Exception as e:
            logger.error("Error decrypting token: %s", e)
            raise

    async def resolve_identity(
        self,
        provider: str,
        external_id: str,
        guild_id: str | None = None,
        channel_id: str | None = None,
    ) -> IdentityResult:
        cache_key = (provider, external_id)
        now = time.monotonic()
        if cache_key in self._cache:
            res, expires_at = self._cache[cache_key]
            if now < expires_at:
                return res

        url = f"{self.backend_url}/api/identity/resolve"
        headers = {
            "Authorization": f"Bearer {self.service_api_key}",
            "Content-Type": "application/json",
        }
        body = {
            "provider": provider,
            "external_id": str(external_id),
            "guild_id": str(guild_id) if guild_id else None,
            "channel_id": str(channel_id) if channel_id else None,
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, headers=headers, json=body)
                if resp.status_code == 200:
                    data = resp.json()
                    res = IdentityResult(
                        linked=data.get("linked", True),
                        user=data.get("user") or {},
                        workspace=data.get("workspace"),
                        project=data.get("project"),
                        entitlements=data.get("entitlements") or {},
                        integrations=data.get("integrations") or [],
                    )
                    self._cache[cache_key] = (res, now + self.cache_ttl_seconds)
                    return res
                elif resp.status_code == 404:
                    return IdentityResult(linked=False, error_detail="User not linked")
                else:
                    return IdentityResult(linked=False, error_detail=f"Backend returned HTTP {resp.status_code}")
        except Exception as e:
            logger.exception("Failed to resolve identity: %s", e)
            return IdentityResult(linked=False, error_detail=str(e))
