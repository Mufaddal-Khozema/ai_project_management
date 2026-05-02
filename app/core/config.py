"""
Application configuration loaded from environment variables.
Uses pydantic-settings for type-safe config management.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration object — all values sourced from env vars / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── Application ────────────────────────────────────────────────────────────
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    # ── Database ───────────────────────────────────────────────────────────────
    database_url: str = "postgresql://auth_user:auth_pass@localhost:5432/auth_db"

    # ── JWT ────────────────────────────────────────────────────────────────────
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 30

    # ── Kafka ──────────────────────────────────────────────────────────────────
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_topic_user_created: str = "auth.user.created"
    kafka_topic_login_success: str = "auth.user.login.success"
    kafka_topic_login_failed: str = "auth.user.login.failed"
    kafka_topic_token_refreshed: str = "auth.token.refreshed"

    # ── Rate Limiting ──────────────────────────────────────────────────────────
    rate_limit_requests: int = 10
    rate_limit_window_seconds: int = 60

    # ── Defaults ───────────────────────────────────────────────────────────────
    default_role: str = "user"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings singleton."""
    return Settings()
