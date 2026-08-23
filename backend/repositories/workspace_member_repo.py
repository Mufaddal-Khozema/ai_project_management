from datetime import datetime, timezone
from typing import Any

from lib.tables import WorkspaceMember


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def find_by_workspace_user(workspace_id: int, user_id: int) -> dict[str, Any] | None:
    rows = (
        WorkspaceMember.select()
        .where(WorkspaceMember.workspace_id == workspace_id, WorkspaceMember.user_id == user_id)
        .run_sync()
    )
    return rows[0] if rows else None


def add(
    workspace_id: int,
    user_id: int,
    role: str = "member",
    status: str = "pending",
) -> dict[str, Any]:
    existing = find_by_workspace_user(workspace_id, user_id)
    if existing:
        return existing
    row = (
        WorkspaceMember.insert(
            WorkspaceMember(
                workspace_id=workspace_id,
                user_id=user_id,
                role=role,
                status=status,
                created_on=utc_now(),
                updated_on=utc_now(),
            )
        )
        .returning(*WorkspaceMember.all_columns())
        .run_sync()
    )
    return row[0]


def list_by_workspace(workspace_id: int) -> list[dict[str, Any]]:
    return (
        WorkspaceMember.select()
        .where(WorkspaceMember.workspace_id == workspace_id)
        .run_sync()
    )


def remove(workspace_id: int, user_id: int) -> bool:
    rows = (
        WorkspaceMember.delete()
        .where(WorkspaceMember.workspace_id == workspace_id, WorkspaceMember.user_id == user_id)
        .run_sync()
    )
    return bool(rows)