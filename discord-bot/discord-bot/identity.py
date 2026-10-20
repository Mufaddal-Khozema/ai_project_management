import os
import time
import logging
from typing import Optional
import requests
from crypto import decrypt_token_payload, TokenEncryptionError
from dotenv import load_dotenv

from schema import Integration,Identity

logger = logging.getLogger("identity_lookup")

load_dotenv()

IDENTITY_URL= os.getenv("IDENTITY_URL")
IDENTITY_TOKEN=os.getenv("IDENTITY_TOKEN")
# IDENTITY_FERNET_KEY = os.getenv("INTEGRATION_TOKEN_ENCRYPTION_KEY")
_TOKEN_KEYS = ("auth_token", "access_token", "token")

_CACHE_TTL=60
_cache: dict = {}


def resolve(external_id, guild_id=None, channel_id=None) -> Identity:
    if not IDENTITY_URL:
        raise RuntimeError("IDENTITY_URL is not configured")
    if not IDENTITY_TOKEN:
        raise RuntimeError("IDENTITY_TOKEN is not configured")
 
    key = str(external_id)
    hit = _cache.get(key)
    if hit and time.time() - hit[0] < _CACHE_TTL:
        return hit[1]

    response = requests.post(
        IDENTITY_URL,
        headers={
            "Authorization": f"Bearer {IDENTITY_TOKEN}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        json={
            "provider": "discord",
            "external_id": key,
            "guild_id": str(guild_id) if guild_id is not None else None,
            "channel_id": str(channel_id) if channel_id is not None else None,
        },
        timeout=(999,999),
    )
    response.raise_for_status()
    identity = Identity.model_validate(response.json())
    # Safe to log: tokens are SecretStr and render masked.
    logger.info("Identity resolved: %s", identity)
    _cache[key] = (time.time(), identity)
    return identity

def get_taiga_integration(identity: Identity) -> Optional[Integration]:
    """Return the Taiga integration, if present."""
    return identity.integration("taiga")

def get_taiga_token(integration: Integration) -> Optional[str]:
    """Return a usable plain-text Taiga token, decrypting it if necessary."""
    if integration.token:
        return integration.token.get_secret_value()
 
    if integration.token_encrypted:
        try:
            payload = decrypt_token_payload(
                integration.token_encrypted.get_secret_value()
            )
        except TokenEncryptionError:
            logger.error("Could not decrypt Taiga token (wrong key?)")
            return None
        print(payload)
        for key in _TOKEN_KEYS:
            if payload.get(key):
                return payload[key]

        logger.error("Decrypted Taiga payload has no token field; keys=%s", list(payload))
        return None

    return None
        
    #     if not IDENTITY_FERNET_KEY:
    #         raise RuntimeError("IDENTITY_FERNET_KEY is not configured")
    #     from cryptography.fernet import Fernet, InvalidToken
 
    #     try:
    #         return (
    #             Fernet(IDENTITY_FERNET_KEY.encode())
    #             .decrypt(integration.token_encrypted.get_secret_value().encode())
    #             .decode()
    #         )
    #     except InvalidToken:
    #         logger.error("Could not decrypt Taiga token (wrong key?)")
    #         return None
 
    # return None
 