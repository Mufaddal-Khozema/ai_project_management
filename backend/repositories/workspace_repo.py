from datetime import datetime, timezone
from typing import Any

from lib.tables import Workspace, WorkspaceMember


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


async def find_by_user_id(user_id: int) -> dict[str, Any] | None:
    rows = await Workspace.select().where(Workspace.user_id == user_id).run()
    return rows[0] if rows else None


async def find_by_member_id(member_user_id: int) -> dict[str, Any] | None:
    """Return the workspace a member belongs to via ``workspace_members``.

    This is the member-side counterpart of :func:`find_by_user_id`, which
    only finds workspaces a user owns. Returns None when the user is not a
    member of any workspace.
    """
    memberships = await (
        WorkspaceMember.select(WorkspaceMember.workspace_id)
        .where(WorkspaceMember.user_id == member_user_id)
        .run()
    )
    if not memberships:
        return None
    rows = await (
        Workspace.select()
        .where(Workspace.id == memberships[0]["workspace_id"])
        .run()
    )
    return rows[0] if rows else None


async def create(user_id: int, values: dict[str, Any]) -> dict[str, Any]:
    row = await (
        Workspace.insert(Workspace(user_id=user_id, **values))
        .returning(*Workspace.all_columns())
        .run()
    )
    return row[0]


async def update(workspace_id: int, values: dict[str, Any]) -> dict[str, Any]:
    updates: dict[Any, Any] = dict(values)
    updates[Workspace.updated_on] = utc_now()
    row = await (
        Workspace.update(updates)
        .where(Workspace.id == workspace_id)
        .returning(*Workspace.all_columns())
        .run()
    )
    return row[0]
