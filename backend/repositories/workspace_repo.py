from datetime import datetime, timezone
from typing import Any

from lib.tables import Workspace


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def find_by_user_id(user_id: int) -> dict[str, Any] | None:
    rows = Workspace.select().where(Workspace.user_id == user_id).run_sync()
    return rows[0] if rows else None


def create(user_id: int, values: dict[str, Any]) -> dict[str, Any]:
    row = (
        Workspace.insert(Workspace(user_id=user_id, **values))
        .returning(*Workspace.all_columns())
        .run_sync()
    )
    return row[0]


def update(workspace_id: int, values: dict[str, Any]) -> dict[str, Any]:
    updates: dict[Any, Any] = dict(values)
    updates[Workspace.updated_on] = utc_now()
    row = (
        Workspace.update(updates)
        .where(Workspace.id == workspace_id)
        .returning(*Workspace.all_columns())
        .run_sync()
    )
    return row[0]
