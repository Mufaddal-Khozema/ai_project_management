"""
Application configuration loaded from environment variables.
Uses pydantic-settings for type-safe config management.
"""
from functools import lru_cache
from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
import os

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
    app_port: int = 8001

    # ── Database ───────────────────────────────────────────────────────────────
    database_url: str = os.getenv("DATABASE_URL")

    # ── JWT ────────────────────────────────────────────────────────────────────
    jwt_secret_key: str = os.getenv("JWT_SECRET_KEY")
    jwt_algorithm: str = os.getenv("JWT_ALGORITHM")
    jwt_access_token_expire_minutes: int = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", 15))
    jwt_refresh_token_expire_days: int = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", 30))

    # ── Kafka / Redpanda ───────────────────────────────────────────────────────
    kafka_bootstrap_servers: str = Field(
        default="localhost:9092",
        validation_alias=AliasChoices(
            "KAFKA_BOOTSTRAP_SERVERS",
            "REDPANDA_BROKERS",
            "KAFKA_BOOTSTARP_SERVERS",
        ),
    )
    kafka_topic_user_created: str = os.getenv("KAFKA_TOPIC_USER_CREATED", "auth.user.created")
    kafka_topic_login_success: str = os.getenv("KAFKA_TOPIC_LOGIN_SUCCESS", "auth.user.login.success")
    kafka_topic_login_failed: str = os.getenv("KAFKA_TOPIC_LOGIN_FAILED", "auth.user.login.failed")
    kafka_topic_token_refreshed: str = os.getenv("KAFKA_TOPIC_TOKEN_REFRESHED", "auth.token.refreshed")
    kafka_topic_org_created: str = os.getenv("KAFKA_TOPIC_ORG_CREATED", "auth.org.created")
    kafka_topic_org_deleted: str = os.getenv("KAFKA_TOPIC_ORG_DELETED", "auth.org.deleted")
    kafka_topic_member_added: str = os.getenv("KAFKA_TOPIC_MEMBER_ADDED", "auth.member.added")

    # ── gRPC ───────────────────────────────────────────────────────────────────
    auth_grpc_bind_address: str = "0.0.0.0:50051"
    auth_grpc_target: str = "localhost:50051"

    # ── Rate Limiting ──────────────────────────────────────────────────────────
    rate_limit_requests: int = int(os.getenv("RATE_LIMIT_REQUESTS", 10))
    rate_limit_window_seconds: int = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", 60))

    # ── Defaults ───────────────────────────────────────────────────────────────
    default_role: str = os.getenv("DEFAULT_ROLE", "user")

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings singleton."""
    return Settings()
