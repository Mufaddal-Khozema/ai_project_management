from __future__ import annotations

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