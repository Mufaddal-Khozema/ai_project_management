from piccolo.apps.migrations.auto.migration_manager import MigrationManager
from piccolo.columns.column_types import Boolean
from piccolo.columns.column_types import Varchar
from piccolo.columns.indexes import IndexMethod

ID = "2026-11-19T08:40:40:918850"
VERSION = "1.36.0"
DESCRIPTION = "True"


async def forwards():
    manager = MigrationManager(
        migration_id=ID, app_name="lib", description=DESCRIPTION
    )

    manager.add_column(
        table_class_name="Project",
        tablename="projects",
        column_name="ambient_enabled",
        db_column_name="ambient_enabled",
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

    manager.add_column(
        table_class_name="Project",
        tablename="projects",
        column_name="voice_channel_id",
        db_column_name="voice_channel_id",
        column_class_name="Varchar",
        column_class=Varchar,
        params={
            "length": 255,
            "default": None,
            "null": True,
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
