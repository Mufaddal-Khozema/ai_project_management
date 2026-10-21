from datetime import datetime, timezone
from typing import Any

from lib.tables import Integration


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


async def find_by_workspace_provider(workspace_id: int, provider: str) -> dict[str, Any] | None:
    rows = await (
        Integration.select()
        .where(Integration.workspace_id == workspace_id, Integration.provider == provider)
        .run()
    )
    return rows[0] if rows else None


async def list_by_workspace(workspace_id: int) -> list[dict[str, Any]]:
    return await Integration.select().where(Integration.workspace_id == workspace_id).run()


async def create(
    workspace_id: int,
    provider: str,
    token_encrypted: str,
    account_name: str | None,
    scopes: str | None,
    status: str,
    expires_at: datetime | None = None,
) -> dict[str, Any]:
    row = await (
        Integration.insert(
            Integration(
                workspace_id=workspace_id,
                provider=provider,
                token_encrypted=token_encrypted,
                account_name=account_name,
                scopes=scopes,
                status=status,
                expires_at=expires_at,
                created_on=utc_now(),
                updated_on=utc_now(),
            )
        )
        .returning(*Integration.all_columns())
        .run()
    )
    return row[0]


async def update_token(
    integration_id: int,
    token_encrypted: str,
    account_name: str | None,
    expires_at: datetime | None,
    status: str,
    last_synced_at: datetime | None,
) -> dict[str, Any]:
    row = await (
        Integration.update(
            {
                Integration.token_encrypted: token_encrypted,
                Integration.account_name: account_name,
                Integration.expires_at: expires_at,
                Integration.status: status,
                Integration.last_synced_at: last_synced_at,
                Integration.updated_on: utc_now(),
            }
        )
        .where(Integration.id == integration_id)
        .returning(*Integration.all_columns())
        .run()
    )
    return row[0]


async def update_status(integration_id: int, status: str) -> dict[str, Any]:
    row = await (
        Integration.update(
            {
                Integration.status: status,
                Integration.updated_on: utc_now(),
            }
        )
        .where(Integration.id == integration_id)
        .returning(*Integration.all_columns())
        .run()
    )
    return row[0]


async def delete_by_workspace_provider(workspace_id: int, provider: str) -> bool:
    rows = await (
        Integration.delete()
        .where(Integration.workspace_id == workspace_id, Integration.provider == provider)
        .run()
    )
    return bool(rows)


async def list_refreshable(refresh_before: datetime) -> list[dict[str, Any]]:
    return await (
        Integration.select()
        .where(
            Integration.expires_at <= refresh_before,
            Integration.status != "error",
        )
        .run()
    )
