"""
Security utilities: JWT creation/verification, password hashing, token hashing.
"""
import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from passlib.context import CryptContext

from app.core.config import get_settings

settings = get_settings()

# ── Password hashing (bcrypt) ──────────────────────────────────────────────────
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    """Return bcrypt hash of *plain* password."""
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Return True when *plain* matches *hashed*."""
    return _pwd_context.verify(plain, hashed)


# ── Refresh-token helpers ──────────────────────────────────────────────────────

def generate_refresh_token() -> str:
    """Generate a cryptographically-secure random refresh token (hex string)."""
    return secrets.token_hex(64)


def hash_refresh_token(token: str) -> str:
    """SHA-256 hash a refresh token before storing it in the database."""
    return hashlib.sha256(token.encode()).hexdigest()


# ── JWT ────────────────────────────────────────────────────────────────────────

def create_access_token(
    user_id: uuid.UUID,
    roles: list[str],
    org_id: uuid.UUID | None = None,
) -> str:
    """
    Mint a signed JWT access token.

    Args:
        user_id: The authenticated user's UUID (becomes ``sub`` claim).
        roles:   List of role names assigned to the user.
        org_id:  Optional organisation UUID.

    Returns:
        Encoded JWT string.
    """
    now = datetime.now(tz=timezone.utc)
    expire = now + timedelta(minutes=settings.jwt_access_token_expire_minutes)

    payload: dict[str, Any] = {
        "sub": str(user_id),
        "roles": roles,
        "org_id": str(org_id) if org_id else None,
        "iat": now,
        "exp": expire,
        "jti": str(uuid.uuid4()),  # unique token id — useful for future blocklisting
    }

    return jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def decode_access_token(token: str) -> dict[str, Any]:
    """
    Decode and verify a JWT access token.

    Raises:
        jwt.ExpiredSignatureError: Token has expired.
        jwt.InvalidTokenError:    Token is invalid.
    """
    return jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
    )
