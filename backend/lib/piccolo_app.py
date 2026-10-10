"""Piccolo app registration for the backend tables.

All Table subclasses live in ``lib.tables``. Registering them here lets
``piccolo migrations new lib --auto`` detect schema changes.
"""

import os

from piccolo.conf.apps import AppConfig, table_finder

CURRENT_DIRECTORY = os.path.dirname(os.path.abspath(__file__))

APP_CONFIG = AppConfig(
    app_name="lib",
    migrations_folder_path=os.path.join(
        CURRENT_DIRECTORY,
        "piccolo_migrations",
    ),
    table_classes=table_finder(
        modules=["lib.tables"],
        exclude_imported=True,
    ),
    migration_dependencies=[],
    commands=[],
)
