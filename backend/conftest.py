import os

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


PostgresEngine.get_version = _fake_get_version