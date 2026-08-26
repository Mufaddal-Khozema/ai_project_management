from __future__ import annotations

from dataclasses import dataclass, field
from functools import cache

from dotenv import load_dotenv

from lib.env import get_env


@dataclass
class Settings:
    app_name: str = field(default_factory=get_env("APP_NAME", "CoordinaAI API"))
    debug: bool = field(default_factory=get_env("DEBUG", True))
    host: str = field(default_factory=get_env("HOST", "0.0.0.0"))
    port: int = field(default_factory=get_env("PORT", 8000))
    database_url: str = field(default_factory=get_env("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/coordinaai"))
    otp_secret_key: str = field(default_factory=get_env("OTP_SECRET_KEY", "change-me-in-production"))

    from_email: str = field(default_factory=get_env("FROM_EMAIL", "noreply@coordinaai.com"))
    from_name: str = field(default_factory=get_env("FROM_NAME", "CoordinaAI"))
    support_email: str = field(default_factory=get_env("SUPPORT_EMAIL", "support@coordinaai.com"))
    smtp_host: str = field(default_factory=get_env("SMTP_HOST", ""))
    smtp_port: int = field(default_factory=get_env("SMTP_PORT", 587))
    smtp_user: str = field(default_factory=get_env("SMTP_USER", ""))
    smtp_password: str = field(default_factory=get_env("SMTP_PASSWORD", ""))
    smtp_use_tls: bool = field(default_factory=get_env("SMTP_USE_TLS", True))
    smtp_use_ssl: bool = field(default_factory=get_env("SMTP_USE_SSL", False))

    invitation_token_expiry_days: int = field(default_factory=get_env("INVITATION_TOKEN_EXPIRY_DAYS", 7))

    app_url: str = field(default_factory=get_env("APP_URL", "http://localhost:8000"))
    frontend_url: str = field(default_factory=get_env("FRONTEND_URL", "http://localhost:3000"))
    github_oauth_client_id: str = field(default_factory=get_env("GITHUB_OAUTH_CLIENT_ID", ""))
    github_oauth_client_secret: str = field(default_factory=get_env("GITHUB_OAUTH_CLIENT_SECRET", ""))
    google_oauth_client_id: str = field(default_factory=get_env("GOOGLE_OAUTH_CLIENT_ID", ""))
    google_oauth_client_secret: str = field(default_factory=get_env("GOOGLE_OAUTH_CLIENT_SECRET", ""))

    integration_token_encryption_key: str = field(default_factory=get_env("INTEGRATION_TOKEN_ENCRYPTION_KEY", ""))
    integration_token_refresh_interval_minutes: int = field(default_factory=get_env("INTEGRATION_TOKEN_REFRESH_INTERVAL_MINUTES", 60))
    integration_token_refresh_lead_minutes: int = field(default_factory=get_env("INTEGRATION_TOKEN_REFRESH_LEAD_MINUTES", 2880))
    integration_token_refresh_enabled: bool = field(default_factory=get_env("INTEGRATION_TOKEN_REFRESH_ENABLED", True))

    email_scheduler_enabled: bool = field(default_factory=get_env("EMAIL_SCHEDULER_ENABLED", True))

    slack_oauth_client_id: str = field(default_factory=get_env("SLACK_OAUTH_CLIENT_ID", ""))
    slack_oauth_client_secret: str = field(default_factory=get_env("SLACK_OAUTH_CLIENT_SECRET", ""))
    microsoft_oauth_client_id: str = field(default_factory=get_env("MICROSOFT_OAUTH_CLIENT_ID", ""))
    microsoft_oauth_client_secret: str = field(default_factory=get_env("MICROSOFT_OAUTH_CLIENT_SECRET", ""))
    microsoft_oauth_tenant: str = field(default_factory=get_env("MICROSOFT_OAUTH_TENANT", "common"))
    discord_oauth_client_id: str = field(default_factory=get_env("DISCORD_OAUTH_CLIENT_ID", ""))
    discord_oauth_client_secret: str = field(default_factory=get_env("DISCORD_OAUTH_CLIENT_SECRET", ""))
    discord_bot_token: str = field(default_factory=get_env("DISCORD_BOT_TOKEN", ""))
    atlassian_oauth_client_id: str = field(default_factory=get_env("ATLASSIAN_OAUTH_CLIENT_ID", ""))
    atlassian_oauth_client_secret: str = field(default_factory=get_env("ATLASSIAN_OAUTH_CLIENT_SECRET", ""))
    clickup_oauth_client_id: str = field(default_factory=get_env("CLICKUP_OAUTH_CLIENT_ID", ""))
    clickup_oauth_client_secret: str = field(default_factory=get_env("CLICKUP_OAUTH_CLIENT_SECRET", ""))
    taiga_base_url: str = field(default_factory=get_env("TAIGA_BASE_URL", "https://api.taiga.io"))

    jwt_secret_key: str = field(default_factory=get_env("JWT_SECRET_KEY", "change-me-in-production"))
    jwt_algorithm: str = field(default_factory=get_env("JWT_ALGORITHM", "HS256"))
    jwt_expire_minutes: int = field(default_factory=get_env("JWT_EXPIRE_MINUTES", 15))
    jwt_refresh_expire_days: int = field(default_factory=get_env("JWT_REFRESH_EXPIRE_DAYS", 7))

    stripe_secret_key: str = field(default_factory=get_env("STRIPE_SECRET_KEY", ""))
    stripe_publishable_key: str = field(default_factory=get_env("STRIPE_PUBLISHABLE_KEY", ""))
    stripe_webhook_secret: str = field(default_factory=get_env("STRIPE_WEBHOOK_SECRET", ""))
    stripe_price_monthly: str = field(default_factory=get_env("STRIPE_PRICE_MONTHLY", ""))
    stripe_price_yearly: str = field(default_factory=get_env("STRIPE_PRICE_YEARLY", ""))


@cache
def get_settings() -> Settings:
    load_dotenv()
    return Settings()


settings = get_settings()
