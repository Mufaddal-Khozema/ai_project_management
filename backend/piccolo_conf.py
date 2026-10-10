"""Piccolo project configuration.

Enables ``piccolo migrations ...`` commands for this backend.

Usage:
    piccolo migrations new lib --auto
    piccolo migrations forwards lib
    piccolo migrations check
"""

from piccolo.conf.apps import AppRegistry

from lib.db import DB  # noqa: F401  (Piccolo finds the engine as `DB`)

APP_REGISTRY = AppRegistry(apps=["lib.piccolo_app"])
