import pytest
from cryptography.fernet import Fernet

from config import settings
from lib import crypto


def test_round_trip():
    payload = {
        "access_token": "tok123",
        "refresh_token": "rt456",
        "expires_at": 1717000000,
        "instance_url": "https://x.atlassian.net",
        "account_name": "Acme",
        "scopes": ["read:jira-work", "write:jira-work"],
    }
    blob = crypto.encrypt_token_payload(payload)
    assert crypto.decrypt_token_payload(blob) == payload


def test_round_trip_handles_simple_payload():
    payload = {"access_token": "xoxb-abc"}
    blob = crypto.encrypt_token_payload(payload)
    assert crypto.decrypt_token_payload(blob) == payload


def test_wrong_key_fails():
    payload = {"access_token": "tok123"}
    blob = crypto.encrypt_token_payload(payload)
    crypto._fernet.cache_clear()
    settings.integration_token_encryption_key = Fernet.generate_key().decode()
    crypto._fernet.cache_clear()
    try:
        with pytest.raises(crypto.TokenEncryptionError):
            crypto.decrypt_token_payload(blob)
    finally:
        crypto._fernet.cache_clear()


def test_tampered_blob_fails():
    payload = {"access_token": "tok123"}
    blob = crypto.encrypt_token_payload(payload)
    tampered = blob[:10] + ("Q" if blob[10] != "Q" else "R") + blob[11:]
    with pytest.raises(crypto.TokenEncryptionError):
        crypto.decrypt_token_payload(tampered)


def test_missing_key_raises(monkeypatch):
    monkeypatch.setattr(settings, "integration_token_encryption_key", "")
    crypto._fernet.cache_clear()
    try:
        with pytest.raises(crypto.TokenEncryptionError, match="not configured"):
            crypto.encrypt_token_payload({"access_token": "t"})
    finally:
        crypto._fernet.cache_clear()


def test_invalid_key_raises(monkeypatch):
    monkeypatch.setattr(settings, "integration_token_encryption_key", "not-a-fernet-key")
    crypto._fernet.cache_clear()
    try:
        with pytest.raises(crypto.TokenEncryptionError, match="Invalid"):
            crypto.encrypt_token_payload({"access_token": "t"})
    finally:
        crypto._fernet.cache_clear()