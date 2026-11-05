from __future__ import annotations
import os
from pathlib import Path
from dataclasses import dataclass
from dotenv import load_dotenv

env_path = Path(__file__).resolve().parent.parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()



@dataclass
class Settings:
    PORT: int = int(os.environ.get("PORT", "8005"))
    HOST: str = os.environ.get("HOST", "0.0.0.0")
    ENVIRONMENT: str = os.environ.get("ENVIRONMENT", "development")

    # Backend
    BACKEND_URL: str = os.environ.get("BACKEND_URL", "http://localhost:8000")
    SERVICE_API_KEY: str = os.environ.get("SERVICE_API_KEY", "svc_6Q22890ts96ox-oc0pavSc_OSWQZyueE8-J8AY5ytlo")
    INTEGRATION_TOKEN_ENCRYPTION_KEY: str = os.environ.get("INTEGRATION_TOKEN_ENCRYPTION_KEY", "")

    # Voice Scrum Master
    VOICE_SERVICE_URL: str = os.environ.get("VOICE_SERVICE_URL", "http://localhost:3001")

    # Kafka & Aiven Cloud Configuration
    KAFKA_BROKERS: str = os.environ.get("KAFKA_BROKERS", "localhost:9092")
    KAFKA_CLIENT_ID: str = os.environ.get("KAFKA_CLIENT_ID", "mcp-gateway")
    KAFKA_ENABLED: str = os.environ.get("KAFKA_ENABLED", "true")
    TOPIC_TASK_EVENTS: str = os.environ.get("TOPIC_TASK_EVENTS", "agent-bridge.task-events")
    TOPIC_MISSING_TOOLS: str = os.environ.get("TOPIC_MISSING_TOOLS", "agent-bridge.missing-tool-requests")

    # Aiven SSL & SASL Settings
    KAFKA_SSL: bool = os.environ.get("KAFKA_SSL", "false").lower() in ("true", "1")
    KAFKA_SSL_CAFILE: str | None = os.environ.get("KAFKA_SSL_CAFILE")
    KAFKA_SSL_CERTFILE: str | None = os.environ.get("KAFKA_SSL_CERTFILE")
    KAFKA_SSL_KEYFILE: str | None = os.environ.get("KAFKA_SSL_KEYFILE")
    KAFKA_SSL_VERIFY: bool = os.environ.get("KAFKA_SSL_VERIFY", "true").lower() not in ("false", "0", "no")
    KAFKA_SASL_USERNAME: str | None = os.environ.get("KAFKA_SASL_USERNAME")
    KAFKA_SASL_PASSWORD: str | None = os.environ.get("KAFKA_SASL_PASSWORD")
    KAFKA_SASL_MECHANISM: str = os.environ.get("KAFKA_SASL_MECHANISM", "SCRAM-SHA-256")


    # Settings
    FUZZY_MATCH_CUTOFF: float = float(os.environ.get("FUZZY_MATCH_CUTOFF", "0.5"))
    DLP_SCRUB_KEYS: str = os.environ.get("DLP_SCRUB_KEYS", "token,secret,password,key,authorization,bearer")

settings = Settings()

