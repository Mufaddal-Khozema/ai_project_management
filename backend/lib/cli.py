from __future__ import annotations

import asyncio
import json

import click
from litestar.plugins import CLIPluginProtocol

from lib.crypto import TokenEncryptionError, decrypt_token_payload


class TokenCliPlugin(CLIPluginProtocol):
    """Registers CLI commands for inspecting stored integration tokens."""

    def on_cli_init(self, cli: click.Group) -> None:
        @cli.command("decode-token")
        @click.argument("token")
        @click.option(
            "--raw",
            is_flag=True,
            help="Print the raw JSON payload instead of formatted output.",
        )
        def decode_token(token: str, raw: bool) -> None:
            """Decrypt a fernet-encrypted integration token and print its payload."""
            try:
                payload = decrypt_token_payload(token)
            except TokenEncryptionError as e:
                raise click.ClickException(str(e))

            text = json.dumps(payload, indent=2, default=str)
            if raw:
                click.echo(text)
                return

            click.echo(click.style("Token payload:", bold=True))
            click.echo(text)

        @cli.command("create-service-key")
        @click.argument("service_name")
        def create_service_key(service_name: str) -> None:
            """Mint a service key for a headless identity consumer.

            The raw key is printed once — only its hash is stored, so it
            cannot be recovered afterwards. Example:

                litestar create-service-key discord-bot
            """
            from lib.service_auth import generate_service_key, hash_service_key
            from repositories import service_api_key_repo

            raw_key = generate_service_key()
            try:
                asyncio.run(
                    service_api_key_repo.create(service_name, hash_service_key(raw_key))
                )
            except Exception as e:
                raise click.ClickException(
                    f"Could not create a key for '{service_name}' "
                    f"(it may already have one): {e}"
                )
            click.echo(click.style("Service key (shown once — store it now):", bold=True))
            click.echo(raw_key)