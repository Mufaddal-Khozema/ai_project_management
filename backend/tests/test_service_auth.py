import pytest
from litestar.exceptions import HTTPException

from lib import service_auth
from lib.service_auth import (
    authenticate_service_key,
    generate_service_key,
    hash_service_key,
)


class _Conn:
    def __init__(self, authorization=None):
        self.headers = {}
        if authorization is not None:
            self.headers["authorization"] = authorization


def test_key_hash_round_trip():
    raw = generate_service_key()
    assert raw.startswith("svc_")
    assert len({generate_service_key() for _ in range(10)}) == 10
    assert hash_service_key(raw) == hash_service_key(raw)
    assert len(hash_service_key(raw)) == 64


def test_authenticate_ok(monkeypatch):
    raw = generate_service_key()
    digest = hash_service_key(raw)
    row = {"id": 1, "service_name": "discord-bot", "key_hash": digest}
    monkeypatch.setattr(
        service_auth.service_api_key_repo, "find_by_key_hash", lambda h: row
    )
    assert authenticate_service_key(_Conn(f"Bearer {raw}")) is row


def test_authenticate_missing_key():
    with pytest.raises(HTTPException) as exc:
        authenticate_service_key(_Conn())
    assert exc.value.status_code == 401


def test_authenticate_unknown_key(monkeypatch):
    monkeypatch.setattr(service_auth.service_api_key_repo, "find_by_key_hash", lambda h: None)
    with pytest.raises(HTTPException) as exc:
        authenticate_service_key(_Conn("Bearer svc_unknown"))
    assert exc.value.status_code == 401


def test_authenticate_tampered_key_rejected(monkeypatch):
    raw = generate_service_key()
    digest = hash_service_key(raw)
    monkeypatch.setattr(
        service_auth.service_api_key_repo,
        "find_by_key_hash",
        lambda h: {"id": 1, "service_name": "x", "key_hash": digest},
    )
    with pytest.raises(HTTPException) as exc:
        authenticate_service_key(_Conn("Bearer svc_something-else-entirely"))
    assert exc.value.status_code == 401
