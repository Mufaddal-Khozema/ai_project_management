from datetime import datetime, timezone
from typing import Any

from lib.tables import Workspace, WorkspaceMember


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def find_by_user_id(user_id: int) -> dict[str, Any] | None:
    rows = Workspace.select().where(Workspace.user_id == user_id).run_sync()
    return rows[0] if rows else None


def find_by_member_id(member_user_id: int) -> dict[str, Any] | None:
    """Return the workspace a member belongs to via ``workspace_members``.

    This is the member-side counterpart of :func:`find_by_user_id`, which
    only finds workspaces a user owns. Returns None when the user is not a
    member of any workspace.
    """
    memberships = (
        WorkspaceMember.select(WorkspaceMember.workspace_id)
        .where(WorkspaceMember.user_id == member_user_id)
        .run_sync()
    )
    if not memberships:
        return None
    rows = (
        Workspace.select()
        .where(Workspace.id == memberships[0]["workspace_id"])
        .run_sync()
    )
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
