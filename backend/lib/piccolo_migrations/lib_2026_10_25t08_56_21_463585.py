from piccolo.apps.migrations.auto.migration_manager import MigrationManager
from piccolo.columns.base import OnDelete
from piccolo.columns.base import OnUpdate
from piccolo.columns.column_types import Boolean
from piccolo.columns.column_types import ForeignKey
from piccolo.columns.column_types import Serial
from piccolo.columns.column_types import Timestamp
from piccolo.columns.column_types import UUID
from piccolo.columns.column_types import Varchar
from piccolo.columns.defaults.timestamp import TimestampNow
from piccolo.columns.defaults.uuid import UUID4
from piccolo.columns.indexes import IndexMethod
from piccolo.table import Table


class Workspace(Table, tablename="workspace", schema=None):
    id = Serial(
        null=False,
        primary_key=True,
        unique=False,
        index=False,
        index_method=IndexMethod.btree,
        choices=None,
        db_column_name="id",
        secret=False,
    )


ID = "2026-10-25T08:56:21:463585"
VERSION = "1.36.0"
DESCRIPTION = "add missing project and service api key tables"


async def forwards():
    manager = MigrationManager(
        migration_id=ID, app_name="lib", description=DESCRIPTION
    )

    manager.add_table(
        class_name="Project", tablename="projects", schema=None, columns=None
    )

    manager.add_table(
        class_name="ServiceApiKey",
        tablename="service_api_keys",
        schema=None,
        columns=None,
    )

    manager.add_column(
        table_class_name="Project",
        tablename="projects",
        column_name="uuid",
        db_column_name="uuid",
        column_class_name="UUID",
        column_class=UUID,
        params={
            "default": UUID4(),
            "null": False,
            "primary_key": False,
            "unique": True,
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
        column_name="workspace_id",
        db_column_name="workspace_id",
        column_class_name="ForeignKey",
        column_class=ForeignKey,
        params={
            "references": Workspace,
            "on_delete": OnDelete.cascade,
            "on_update": OnUpdate.no_action,
            "target_column": None,
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
        column_name="pm_provider",
        db_column_name="pm_provider",
        column_class_name="Varchar",
        column_class=Varchar,
        params={
            "length": 50,
            "default": "taiga",
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
        column_name="project_id",
        db_column_name="project_id",
        column_class_name="Varchar",
        column_class=Varchar,
        params={
            "length": 255,
            "default": "",
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
        column_name="project_name",
        db_column_name="project_name",
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

    manager.add_column(
        table_class_name="Project",
        tablename="projects",
        column_name="project_slug",
        db_column_name="project_slug",
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

    manager.add_column(
        table_class_name="Project",
        tablename="projects",
        column_name="comm_provider",
        db_column_name="comm_provider",
        column_class_name="Varchar",
        column_class=Varchar,
        params={
            "length": 50,
            "default": "discord",
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
        column_name="guild_id",
        db_column_name="guild_id",
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

    manager.add_column(
        table_class_name="Project",
        tablename="projects",
        column_name="channel_id",
        db_column_name="channel_id",
        column_class_name="Varchar",
        column_class=Varchar,
        params={
            "length": 255,
            "default": "",
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
        column_name="active",
        db_column_name="active",
        column_class_name="Boolean",
        column_class=Boolean,
        params={
            "default": True,
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
        column_name="created_on",
        db_column_name="created_on",
        column_class_name="Timestamp",
        column_class=Timestamp,
        params={
            "default": TimestampNow(),
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
        column_name="updated_on",
        db_column_name="updated_on",
        column_class_name="Timestamp",
        column_class=Timestamp,
        params={
            "default": TimestampNow(),
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
        table_class_name="ServiceApiKey",
        tablename="service_api_keys",
        column_name="uuid",
        db_column_name="uuid",
        column_class_name="UUID",
        column_class=UUID,
        params={
            "default": UUID4(),
            "null": False,
            "primary_key": False,
            "unique": True,
            "index": False,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
        schema=None,
    )

    manager.add_column(
        table_class_name="ServiceApiKey",
        tablename="service_api_keys",
        column_name="service_name",
        db_column_name="service_name",
        column_class_name="Varchar",
        column_class=Varchar,
        params={
            "length": 100,
            "default": "",
            "null": False,
            "primary_key": False,
            "unique": True,
            "index": False,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
        schema=None,
    )

    manager.add_column(
        table_class_name="ServiceApiKey",
        tablename="service_api_keys",
        column_name="key_hash",
        db_column_name="key_hash",
        column_class_name="Varchar",
        column_class=Varchar,
        params={
            "length": 64,
            "default": "",
            "null": False,
            "primary_key": False,
            "unique": True,
            "index": False,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
        schema=None,
    )

    manager.add_column(
        table_class_name="ServiceApiKey",
        tablename="service_api_keys",
        column_name="created_on",
        db_column_name="created_on",
        column_class_name="Timestamp",
        column_class=Timestamp,
        params={
            "default": TimestampNow(),
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
