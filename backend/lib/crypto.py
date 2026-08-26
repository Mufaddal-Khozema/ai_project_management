from __future__ import annotations

import json
from functools import cache
from typing import Any

import structlog
from cryptography.fernet import Fernet, InvalidToken

from config import settings

logger = structlog.get_logger(__name__)


class TokenEncryptionError(Exception):
    """Raised when an integration token payload cannot be encrypted or decrypted."""


@cache
def _fernet() -> Fernet:
    key = settings.integration_token_encryption_key
    if not key:
        raise TokenEncryptionError("INTEGRATION_TOKEN_ENCRYPTION_KEY is not configured")
    try:
        return Fernet(key.encode())
    except (ValueError, TypeError) as e:
        raise TokenEncryptionError("Invalid INTEGRATION_TOKEN_ENCRYPTION_KEY") from e


def encrypt_token_payload(data: dict[str, Any]) -> str:
    raw = json.dumps(data, separators=(",", ":")).encode("utf-8")
    return _fernet().encrypt(raw).decode("utf-8")


def decrypt_token_payload(blob: str) -> dict[str, Any]:
    try:
        raw = _fernet().decrypt(blob.encode("utf-8"))
    except InvalidToken as e:
        logger.error("failed to decrypt integration token payload")
        raise TokenEncryptionError("Failed to decrypt integration token payload") from e
    return json.loads(raw.decode("utf-8"))