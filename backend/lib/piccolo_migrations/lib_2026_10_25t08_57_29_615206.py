from piccolo.apps.migrations.auto.migration_manager import MigrationManager
from piccolo.columns.column_types import Boolean
from piccolo.columns.indexes import IndexMethod

ID = "2026-10-25T08:57:29:615206"
VERSION = "1.36.0"
DESCRIPTION = "add workspace.is_deleted"


async def forwards():
    manager = MigrationManager(
        migration_id=ID, app_name="lib", description=DESCRIPTION
    )

    manager.add_column(
        table_class_name="Workspace",
        tablename="workspace",
        column_name="is_deleted",
        db_column_name="is_deleted",
        column_class_name="Boolean",
        column_class=Boolean,
        params={
            "default": False,
            "null": False,
            "primary_key": False,
            "unique": False,
            "index": False,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
        schema=None,
    )

    return manager
