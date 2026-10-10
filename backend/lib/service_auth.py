from __future__ import annotations

import hashlib
import hmac
import secrets
from typing import Any

import structlog
from litestar.connection import ASGIConnection
from litestar.exceptions import HTTPException

from repositories import service_api_key_repo

logger = structlog.get_logger(__name__)

SERVICE_KEY_PREFIX = "svc_"


def generate_service_key() -> str:
    """Mint a new raw service key. Shown once — only its hash is stored."""
    return SERVICE_KEY_PREFIX + secrets.token_urlsafe(32)


def hash_service_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def _bearer_token(conn: ASGIConnection) -> str | None:
    header = conn.headers.get("authorization")
    if not header:
        return None
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        return None
    return token.strip()


def authenticate_service_key(request: ASGIConnection) -> dict[str, Any]:
    """Validate the caller's service key. Returns the key row on success.

    Raises 401 when the key is missing or unknown. Uses a constant-time
    comparison so key hashes cannot be probed byte-by-byte. Revocation is
    deletion of the row — a deleted key simply stops matching.
    """
    raw_key = _bearer_token(request)
    if not raw_key:
        raise HTTPException(status_code=401, detail="Missing service key")

    candidate_hash = hash_service_key(raw_key)
    row = service_api_key_repo.find_by_key_hash(candidate_hash)
    if row is None or not hmac.compare_digest(row["key_hash"], candidate_hash):
        logger.warning("identity service auth rejected — unknown key")
        raise HTTPException(status_code=401, detail="Invalid service key")

    return row
