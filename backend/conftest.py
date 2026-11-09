import os
import sys
import asyncio

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

os.environ.setdefault("INTEGRATION_TOKEN_ENCRYPTION_KEY", "DfIS1CpII3-YczI7_kOCRQLzqksNl9lAsTDv2b285Fc=")
os.environ.setdefault("SLACK_OAUTH_CLIENT_ID", "slack-test-id")
os.environ.setdefault("SLACK_OAUTH_CLIENT_SECRET", "slack-test-secret")
os.environ.setdefault("MICROSOFT_OAUTH_CLIENT_ID", "ms-test-id")
os.environ.setdefault("MICROSOFT_OAUTH_CLIENT_SECRET", "ms-test-secret")
os.environ.setdefault("MICROSOFT_OAUTH_TENANT", "common")
os.environ.setdefault("DISCORD_OAUTH_CLIENT_ID", "discord-test-id")
os.environ.setdefault("DISCORD_OAUTH_CLIENT_SECRET", "discord-test-secret")
os.environ.setdefault("ATLASSIAN_OAUTH_CLIENT_ID", "jira-test-id")
os.environ.setdefault("ATLASSIAN_OAUTH_CLIENT_SECRET", "jira-test-secret")
os.environ.setdefault("CLICKUP_OAUTH_CLIENT_ID", "clickup-test-id")
os.environ.setdefault("CLICKUP_OAUTH_CLIENT_SECRET", "clickup-test-secret")
os.environ.setdefault("INTEGRATION_TOKEN_REFRESH_ENABLED", "false")
os.environ.setdefault("APP_URL", "http://test-api")
os.environ.setdefault("FRONTEND_URL", "http://test-web")

from piccolo.engine.postgres import PostgresEngine


async def _fake_get_version(self):
    return 16.0


async def _fake_check_version(self):
    return None


async def _fake_prep_database(self):
    return None


PostgresEngine.get_version = _fake_get_version
PostgresEngine.check_version = _fake_check_version
PostgresEngine.prep_database = _fake_prep_database
PostgresEngine.get_version_sync = lambda self: 16.0

import piccolo.utils.sync

def _safe_run_sync(coro):
    if hasattr(coro, "close"):
        coro.close()
    return None

piccolo.utils.sync.run_sync = _safe_run_sync

