#!/usr/bin/env python3
"""
scripts/decrypt_token.py — Utility to decrypt Fernet-encrypted integration tokens.

Usage:
    python scripts/decrypt_token.py
    python scripts/decrypt_token.py "gAAAAABqw..."
    python scripts/decrypt_token.py --key "your_fernet_key" "gAAAAABqw..."
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import sys
from pathlib import Path

# Force UTF-8 on Windows stdout/stderr to support emojis/unicode
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from cryptography.fernet import Fernet, InvalidToken
from dotenv import load_dotenv

# Try loading from backend/.env or agent-bridge/.env
ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / "backend" / ".env")
load_dotenv(ROOT_DIR / "agent-bridge" / ".env")


def decode_jwt_payload(jwt_str: str) -> dict | None:
    """Attempt to decode JWT payload without verification for inspection."""
    parts = jwt_str.split(".")
    if len(parts) != 3:
        return None
    try:
        # Add base64 padding if needed
        payload_b64 = parts[1]
        padded = payload_b64 + "=" * (-len(payload_b64) % 4)
        decoded = base64.urlsafe_b64decode(padded)
        return json.loads(decoded.decode("utf-8"))
    except Exception:
        return None


def decrypt_integration_token(token_encrypted: str, fernet_key: str) -> dict:
    f = Fernet(fernet_key.encode("utf-8"))
    decrypted_bytes = f.decrypt(token_encrypted.strip().encode("utf-8"))
    return json.loads(decrypted_bytes.decode("utf-8"))


def main():
    parser = argparse.ArgumentParser(description="Decrypt Fernet-encrypted integration tokens.")
    parser.add_argument("token", nargs="?", help="Encrypted token string (starts with gAAAAAB...)")
    parser.add_argument("--key", help="Fernet key (defaults to INTEGRATION_TOKEN_ENCRYPTION_KEY from .env)")
    args = parser.parse_args()

    key = args.key or os.environ.get("INTEGRATION_TOKEN_ENCRYPTION_KEY")
    if not key:
        print("[!] Error: INTEGRATION_TOKEN_ENCRYPTION_KEY not found in environment or arguments.", file=sys.stderr)
        print("Please specify with --key or ensure backend/.env exists.", file=sys.stderr)
        sys.exit(1)

    token = args.token
    if not token:
        print("Enter the encrypted token (paste and press Enter):")
        token = input().strip()

    if not token:
        print("[!] Error: No token provided.", file=sys.stderr)
        sys.exit(1)

    try:
        data = decrypt_integration_token(token, key)
        print("\n" + "=" * 60)
        print("[*] DECRYPTED INTEGRATION TOKEN")
        print("=" * 60)
        print(json.dumps(data, indent=2))
        print("=" * 60)

        # Inspect nested JWT tokens if present (common in Taiga & Discord)
        for field in ("access_token", "refresh_token"):
            val = data.get(field)
            if isinstance(val, str):
                jwt_payload = decode_jwt_payload(val)
                if jwt_payload:
                    print(f"\n[*] Decoded JWT Claims for `{field}`:")
                    print(json.dumps(jwt_payload, indent=2))

    except InvalidToken:
        print("[!] Error: Invalid token or key mismatch. Could not decrypt payload.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"[!] Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
