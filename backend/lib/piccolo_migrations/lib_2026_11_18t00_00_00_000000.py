"""Make project channel ownership global across workspaces."""

from piccolo.apps.migrations.auto.migration_manager import MigrationManager

ID = "2026-11-18T00:00:00:000000"
VERSION = "1.36.0"
DESCRIPTION = "make project channel ownership global"


async def forwards():
    manager = MigrationManager(
        migration_id=ID, app_name="lib", description=DESCRIPTION
    )

    async def drop_workspace_channel_index():
        from lib.db import DB
        from piccolo.querystring import QueryString

        await DB.run_querystring(
            QueryString(
                'DROP INDEX IF EXISTS "projects_workspace_comm_channel_idx"'
            )
        )

    async def create_global_channel_index():
        from lib.db import DB
        from piccolo.querystring import QueryString

        # Existing installations may contain duplicate active mappings from
        # before channel ownership became global. Preserve the newest mapping
        # and deactivate older duplicates before adding the constraint.
        await DB.run_querystring(
            QueryString(
                'WITH ranked AS ('
                ' SELECT "id", ROW_NUMBER() OVER ('
                ' PARTITION BY "comm_provider", "channel_id" '
                ' ORDER BY "updated_on" DESC, "id" DESC'
                ' ) AS "rank" FROM "projects" WHERE "active" = TRUE'
                ' ) UPDATE "projects" SET "active" = FALSE, '
                ' "updated_on" = CURRENT_TIMESTAMP '
                ' WHERE "id" IN (SELECT "id" FROM ranked WHERE "rank" > 1)'
            )
        )
        await DB.run_querystring(
            QueryString(
                'CREATE UNIQUE INDEX IF NOT EXISTS "projects_comm_channel_idx" '
                'ON "projects" ("comm_provider", "channel_id") '
                'WHERE "active" = TRUE'
            )
        )

    async def drop_global_channel_index():
        from lib.db import DB
        from piccolo.querystring import QueryString

        await DB.run_querystring(
            QueryString(
                'DROP INDEX IF EXISTS "projects_comm_channel_idx"'
            )
        )

    async def restore_workspace_channel_index():
        from lib.db import DB
        from piccolo.querystring import QueryString

        await DB.run_querystring(
            QueryString(
                'CREATE UNIQUE INDEX IF NOT EXISTS "projects_workspace_comm_channel_idx" '
                'ON "projects" ("workspace_id", "comm_provider", "channel_id") '
                'WHERE "active" = TRUE'
            )
        )

    manager.add_raw(drop_workspace_channel_index)
    manager.add_raw(create_global_channel_index)
    manager.add_raw_backwards(drop_global_channel_index)
    manager.add_raw_backwards(restore_workspace_channel_index)
    return manager
