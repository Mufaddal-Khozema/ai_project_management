from datetime import datetime, timezone
from typing import Any

from lib.tables import Project


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


async def find_by_workspace_channel(
    workspace_id: int, comm_provider: str, channel_id: str
) -> dict[str, Any] | None:
    rows = await (
        Project.select()
        .where(
            Project.workspace_id == workspace_id,
            Project.comm_provider == comm_provider,
            Project.channel_id == channel_id,
        )
        .run()
    )
    return rows[0] if rows else None


async def find_by_uuid(workspace_id: int, uuid: str) -> dict[str, Any] | None:
    rows = await (
        Project.select()
        .where(
            Project.workspace_id == workspace_id,
            Project.uuid == uuid,
        )
        .run()
    )
    return rows[0] if rows else None


async def find_by_channel(
    workspace_id: int,
    comm_provider: str,
    channel_id: str,
    guild_id: str | None = None,
) -> Project | None:
    """Return the active mapping for a channel within a workspace.

    When ``guild_id`` is supplied, mappings that record a different guild are
    excluded. Mappings with no guild recorded still match.
    """
    where = (
        (Project.workspace_id == workspace_id)
        & (Project.comm_provider == comm_provider)
        & (Project.channel_id == channel_id)
        & (Project.active == True)  # noqa: E712 - Piccolo needs the comparison
    )
    if guild_id:
        where &= (Project.guild_id == guild_id) | Project.guild_id.is_null()
    return await Project.objects().get(where).run()


async def list_by_workspace(workspace_id: int) -> list[dict[str, Any]]:
    return await (
        Project.select()
        .where(Project.workspace_id == workspace_id)
        .order_by(Project.updated_on, descending=True)
        .run()
    )


async def upsert(
    workspace_id: int,
    pm_provider: str,
    project_id: str,
    project_name: str | None,
    project_slug: str | None,
    comm_provider: str,
    channel_id: str,
    guild_id: str | None,
    active: bool = True,
) -> dict[str, Any]:
    existing = await find_by_workspace_channel(
        workspace_id, comm_provider, channel_id
    )
    if existing:
        row = await (
            Project.update(
                {
                    Project.pm_provider: pm_provider,
                    Project.project_id: project_id,
                    Project.project_name: project_name,
                    Project.project_slug: project_slug,
                    Project.guild_id: guild_id,
                    Project.active: active,
                    Project.updated_on: utc_now(),
                }
            )
            .where(Project.id == existing["id"])
            .returning(*Project.all_columns())
            .run()
        )
        return row[0]

    row = await (
        Project.insert(
            Project(
                workspace_id=workspace_id,
                pm_provider=pm_provider,
                project_id=project_id,
                project_name=project_name,
                project_slug=project_slug,
                comm_provider=comm_provider,
                channel_id=channel_id,
                guild_id=guild_id,
                active=active,
                created_on=utc_now(),
                updated_on=utc_now(),
            )
        )
        .returning(*Project.all_columns())
        .run()
    )
    return row[0]


async def delete_by_uuid(workspace_id: int, uuid: str) -> bool:
    rows = await (
        Project.delete()
        .where(
            Project.workspace_id == workspace_id,
            Project.uuid == uuid,
        )
        .run()
    )
    return bool(rows)


async def delete_by_workspace(workspace_id: int) -> bool:
    rows = await (
        Project.delete()
        .where(Project.workspace_id == workspace_id)
        .run()
    )
    return bool(rows)
