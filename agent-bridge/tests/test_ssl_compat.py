import os
import tempfile
import certifi
import pytest

from core.ssl_compat import sanitize_ssl_environment


def test_sanitize_ssl_environment_with_clean_env():
    # Should run cleanly without throwing
    sanitize_ssl_environment()
    assert os.environ.get("SSL_CERT_FILE") is None or os.path.isfile(os.environ.get("SSL_CERT_FILE"))


def test_sanitize_ssl_environment_with_corrupt_ssl_cert_file(monkeypatch):
    bad_pem = tempfile.NamedTemporaryFile(delete=False, mode="w")
    bad_pem.write("-----BEGIN CERTIFICATE-----\ncorrupt_data\n-----END CERTIFICATE-----")
    bad_pem.close()

    try:
        monkeypatch.setenv("SSL_CERT_FILE", bad_pem.name)
        sanitize_ssl_environment()
        assert os.environ.get("SSL_CERT_FILE") == certifi.where()
    finally:
        if os.path.exists(bad_pem.name):
            os.remove(bad_pem.name)


def test_sanitize_ssl_environment_with_nonexistent_file(monkeypatch):
    monkeypatch.setenv("SSL_CERT_FILE", "C:/non_existent_cert_file_12345.pem")
    sanitize_ssl_environment()
    assert os.environ.get("SSL_CERT_FILE") == certifi.where()
