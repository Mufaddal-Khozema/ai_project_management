"""Add soft-delete timestamps to the workspace graph."""

from piccolo.apps.migrations.auto.migration_manager import MigrationManager

ID = "2026-11-18T01:00:00:000000"
VERSION = "1.37.0"
DESCRIPTION = "add workspace graph deleted_at timestamps"


async def forwards():
    manager = MigrationManager(migration_id=ID, app_name="lib", description=DESCRIPTION)

    async def add_columns():
        from lib.db import DB
        from piccolo.querystring import QueryString

        for statement in (
            'ALTER TABLE "workspace" ADD COLUMN IF NOT EXISTS "deleted_at" TIMESTAMP NULL',
            'ALTER TABLE "projects" ADD COLUMN IF NOT EXISTS "deleted_at" TIMESTAMP NULL',
            'ALTER TABLE "workspace_members" ADD COLUMN IF NOT EXISTS "deleted_at" TIMESTAMP NULL',
            'ALTER TABLE "integrations" ADD COLUMN IF NOT EXISTS "deleted_at" TIMESTAMP NULL',
            'UPDATE "workspace" SET "deleted_at" = CURRENT_TIMESTAMP '
            'WHERE "is_deleted" = TRUE AND "deleted_at" IS NULL',
        ):
            await DB.run_querystring(QueryString(statement))

    async def remove_columns():
        from lib.db import DB
        from piccolo.querystring import QueryString

        for statement in (
            'ALTER TABLE "integrations" DROP COLUMN IF EXISTS "deleted_at"',
            'ALTER TABLE "workspace_members" DROP COLUMN IF EXISTS "deleted_at"',
            'ALTER TABLE "projects" DROP COLUMN IF EXISTS "deleted_at"',
            'ALTER TABLE "workspace" DROP COLUMN IF EXISTS "deleted_at"',
        ):
            await DB.run_querystring(QueryString(statement))

    manager.add_raw(add_columns)
    manager.add_raw_backwards(remove_columns)
    return manager
