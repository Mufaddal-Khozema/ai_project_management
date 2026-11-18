from datetime import datetime, timezone
from typing import Any

from lib.tables import Integration, Project, Workspace, WorkspaceMember


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


async def find_by_user_id(user_id: int, *, include_deleted: bool = False) -> dict[str, Any] | None:
    where = Workspace.user_id == user_id
    if not include_deleted:
        where &= Workspace.deleted_at.is_null()
    rows = await Workspace.select().where(where).run()
    return rows[0] if rows else None


async def find_by_id(workspace_id: int) -> Workspace | None:
    return await (Workspace.objects().get(
        (Workspace.id == workspace_id) & Workspace.deleted_at.is_null()
    ).run())


async def find_by_member_id(member_user_id: int) -> Workspace | None:
    memberships = await (WorkspaceMember.select(WorkspaceMember.workspace_id)
        .where(WorkspaceMember.user_id == member_user_id, WorkspaceMember.deleted_at.is_null())
        .run())
    if not memberships:
        return None
    return await (Workspace.objects().get(
        (Workspace.id == memberships[0]["workspace_id"]) & Workspace.deleted_at.is_null()
    ).run())


async def create(user_id: int, values: dict[str, Any]) -> dict[str, Any]:
    row = await (Workspace.insert(Workspace(user_id=user_id, **values))
        .returning(*Workspace.all_columns()).run())
    return row[0]


async def update(workspace_id: int, values: dict[str, Any]) -> dict[str, Any]:
    updates: dict[Any, Any] = dict(values)
    updates[Workspace.updated_on] = utc_now()
    row = await (Workspace.update(updates)
        .where((Workspace.id == workspace_id) & Workspace.deleted_at.is_null())
        .returning(*Workspace.all_columns()).run())
    return row[0]


async def soft_delete(workspace_id: int, deleted_at: datetime) -> bool:
    await Project.update({Project.deleted_at: deleted_at, Project.active: False}).where(
        Project.workspace_id == workspace_id
    ).run()
    await WorkspaceMember.update({WorkspaceMember.deleted_at: deleted_at}).where(
        WorkspaceMember.workspace_id == workspace_id
    ).run()
    await Integration.update({
        Integration.deleted_at: deleted_at,
        Integration.token_encrypted: "",
    }).where(Integration.workspace_id == workspace_id).run()
    rows = await (Workspace.update({
        Workspace.deleted_at: deleted_at,
        Workspace.is_deleted: True,
        Workspace.updated_on: deleted_at,
    }).where(Workspace.id == workspace_id, Workspace.deleted_at.is_null()).run())
    return bool(rows)


async def restore(workspace_id: int, values: dict[str, Any]) -> dict[str, Any]:
    updates: dict[Any, Any] = dict(values)
    updates[Workspace.deleted_at] = None
    updates[Workspace.is_deleted] = False
    updates[Workspace.updated_on] = utc_now()
    row = await (Workspace.update(updates).where(Workspace.id == workspace_id)
        .returning(*Workspace.all_columns()).run())
    return row[0]
