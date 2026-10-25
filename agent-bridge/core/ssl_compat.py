"""
core/ssl_compat.py — SSL environment verification and repair for Windows/dev setups.
Detects corrupted or invalid SSL_CERT_FILE / SSL_CERT_DIR environment variables
that trigger `ssl.SSLError: [X509] PEM lib (_ssl.c:4154)` and falls back to certifi.
"""
from __future__ import annotations

import logging
import os
import ssl

logger = logging.getLogger("agent_bridge.ssl_compat")


def sanitize_ssl_environment() -> None:
    """
    Ensure the SSL certificate environment is healthy.
    On Windows environments, corrupted or misconfigured SSL_CERT_FILE / SSL_CERT_DIR
    variables can trigger OpenSSL errors (e.g. ssl.SSLError: [X509] PEM lib (_ssl.c:4154)).
    This routine detects such issues and safely resets the SSL bundle to certifi.
    """
    try:
        import certifi
        cert_bundle = certifi.where()
    except Exception:
        cert_bundle = None

    cert_file = os.environ.get("SSL_CERT_FILE")
    cert_dir = os.environ.get("SSL_CERT_DIR")

    needs_fix = False
    if cert_file or cert_dir:
        try:
            ssl.create_default_context(cafile=cert_file, capath=cert_dir)
        except Exception as e:
            logger.warning(
                "SSL certificate path check failed (SSL_CERT_FILE=%r, SSL_CERT_DIR=%r: %s).",
                cert_file, cert_dir, e,
            )
            needs_fix = True

    if not needs_fix:
        try:
            ssl.create_default_context(cafile=cert_file or cert_bundle)
        except Exception as e:
            logger.warning("Default SSL context creation failed: %s", e)
            needs_fix = True

    if needs_fix and cert_bundle and os.path.isfile(cert_bundle):
        for var in ("SSL_CERT_FILE", "SSL_CERT_DIR", "REQUESTS_CA_BUNDLE", "CURL_CA_BUNDLE"):
            os.environ.pop(var, None)
        os.environ["SSL_CERT_FILE"] = cert_bundle
        os.environ["REQUESTS_CA_BUNDLE"] = cert_bundle
        logger.info("SSL environment sanitized — using certifi bundle: %s", cert_bundle)
