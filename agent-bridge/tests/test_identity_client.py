from __future__ import annotations

import json
from unittest.mock import MagicMock, patch
import pytest
from cryptography.fernet import Fernet

from core.identity_client import IdentityClient, IdentityResult


@pytest.fixture
def fernet_key():
    return Fernet.generate_key().decode()


@pytest.fixture
def identity_client(fernet_key):
    return IdentityClient(
        backend_url="http://mock-backend:8000",
        service_api_key="svc_test_key_12345",
        fernet_key=fernet_key,
        cache_ttl_seconds=60.0,
    )


def test_decrypt_token(identity_client, fernet_key):
    f = Fernet(fernet_key.encode())
    payload = {
        "access_token": "mock_taiga_token_xyz",
        "username": "alice",
        "instance_url": "https://tree.taiga.io",
    }
    encrypted = f.encrypt(json.dumps(payload).encode()).decode()

    decrypted = identity_client.decrypt_token(encrypted)
    assert decrypted["access_token"] == "mock_taiga_token_xyz"
    assert decrypted["username"] == "alice"


def test_resolve_discord_identity_success(identity_client, fernet_key):
    f = Fernet(fernet_key.encode())
    taiga_payload = {"access_token": "taiga_tok_999", "url": "https://api.taiga.io"}
    enc_token = f.encrypt(json.dumps(taiga_payload).encode()).decode()

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "linked": True,
        "user": {
            "uuid": "00000000-0000-0000-0000-000000000001",
            "email": "dev@example.com",
            "name": "Dev User",
            "status": "email_verified",
        },
        "workspace": {
            "uuid": "00000000-0000-0000-0000-000000000002",
            "company_name": "Test Company",
        },
        "entitlements": {
            "has_subscription": True,
            "onboarding_completed": True,
        },
        "integrations": [
            {
                "provider": "taiga",
                "account_name": "taiga_dev",
                "status": "connected",
                "token_encrypted": enc_token,
            }
        ],
    }

    with patch("requests.post", return_value=mock_resp) as mock_post:
        result = identity_client.resolve_discord_identity(
            external_id="123456789",
            guild_id="987654321",
            channel_id="555555555",
        )

        assert mock_post.called
        headers = mock_post.call_args[1]["headers"]
        assert headers["Authorization"] == "Bearer svc_test_key_12345"

        assert result.linked is True
        assert result.has_subscription is True
        assert result.user_name == "Dev User"
        assert result.company_name == "Test Company"

        # Taiga credentials extraction
        taiga_creds = identity_client.get_taiga_credentials(result)
        assert taiga_creds is not None
        assert taiga_creds["access_token"] == "taiga_tok_999"


def test_resolve_discord_identity_unlinked(identity_client):
    mock_resp = MagicMock()
    mock_resp.status_code = 404
    mock_resp.json.return_value = {"detail": "Identity not linked."}

    with patch("requests.post", return_value=mock_resp):
        result = identity_client.resolve_discord_identity("999999999")
        assert result.linked is False
        assert "not linked" in (result.error_detail or "").lower()
