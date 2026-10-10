"""Fix drift: ``workspace.onboarding_completed_at`` missing in live DB.

Root cause: new column added to ``lib.tables.Workspace`` but existing
databases were created via ``create_all_tables(if_not_exists=True)``,
which never alters existing tables.

This migration converges drifted databases. It is idempotent
(``IF NOT EXISTS``), so it is a safe no-op on fresh databases where
``create_all_tables`` already created the column, and on re-runs.

Verified drift (code vs ``information_schema.columns``):
    * ``workspace.onboarding_completed_at`` -- MISSING IN DB
    * all other tables/columns match; indexes and constraints match.

Apply with:
    piccolo migrations forwards lib
"""

from piccolo.apps.migrations.auto.migration_manager import MigrationManager

ID = "2026-10-03T11:30:37:448890"
VERSION = "1.36.0"
DESCRIPTION = "add workspace.onboarding_completed_at (drift fix)"


async def forwards():
    manager = MigrationManager(
        migration_id=ID, app_name="lib", description=DESCRIPTION
    )

    async def add_onboarding_completed_at():
        from lib.db import DB
        from piccolo.querystring import QueryString

        await DB.run_querystring(
            QueryString(
                'ALTER TABLE "workspace" '
                'ADD COLUMN IF NOT EXISTS "onboarding_completed_at" '
                "TIMESTAMP DEFAULT null"
            )
        )

    async def drop_onboarding_completed_at():
        from lib.db import DB
        from piccolo.querystring import QueryString

        await DB.run_querystring(
            QueryString(
                'ALTER TABLE "workspace" '
                'DROP COLUMN IF EXISTS "onboarding_completed_at"'
            )
        )

    manager.add_raw(add_onboarding_completed_at)
    manager.add_raw_backwards(drop_onboarding_completed_at)

    return manager
