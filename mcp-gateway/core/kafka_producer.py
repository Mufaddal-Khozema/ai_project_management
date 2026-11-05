from __future__ import annotations
import json
import logging
import os
import sys
from typing import Any
from kafka import KafkaProducer
from kafka.errors import KafkaError
from core.config import settings

logger = logging.getLogger("mcp_gateway.kafka")

class KafkaTelemetry:
    _producer: KafkaProducer | None = None
    _init_attempted: bool = False

    @classmethod
    def get_producer(cls) -> KafkaProducer | None:
        if cls._producer is not None:
            return cls._producer
        if cls._init_attempted:
            return cls._producer

        cls._init_attempted = True

        # Check if disabled by env, offline, or running within unit tests
        if (
            os.environ.get("KAFKA_ENABLED", "false").lower() not in ("true", "1", "yes", "on")
            or "pytest" in sys.modules
            or "run_tests" in sys.modules
            or os.environ.get("TESTING", "").lower() in ("true", "1")
        ):
            return None




        try:
            brokers = [b.strip() for b in settings.KAFKA_BROKERS.split(",") if b.strip()]
            kwargs: dict[str, Any] = {
                "bootstrap_servers": brokers,
                "client_id": settings.KAFKA_CLIENT_ID,
                "value_serializer": lambda v: json.dumps(v).encode("utf-8"),
                "request_timeout_ms": 10000,
                "max_block_ms": 5000,
            }

            # Auto-detect Aiven Cloud host or explicit SSL flag
            is_aiven = any("aivencloud.com" in b.lower() for b in brokers)
            use_ssl = settings.KAFKA_SSL or is_aiven

            if use_ssl:
                kwargs["security_protocol"] = "SASL_SSL" if settings.KAFKA_SASL_USERNAME else "SSL"
                if not settings.KAFKA_SSL_VERIFY:
                    import ssl
                    ctx = ssl.create_default_context()
                    ctx.check_hostname = False
                    ctx.verify_mode = ssl.CERT_NONE
                    kwargs["ssl_context"] = ctx
                else:
                    if settings.KAFKA_SSL_CAFILE and os.path.exists(settings.KAFKA_SSL_CAFILE):
                        kwargs["ssl_cafile"] = settings.KAFKA_SSL_CAFILE
                    if settings.KAFKA_SSL_CERTFILE and os.path.exists(settings.KAFKA_SSL_CERTFILE):
                        kwargs["ssl_certfile"] = settings.KAFKA_SSL_CERTFILE
                    if settings.KAFKA_SSL_KEYFILE and os.path.exists(settings.KAFKA_SSL_KEYFILE):
                        kwargs["ssl_keyfile"] = settings.KAFKA_SSL_KEYFILE

            if settings.KAFKA_SASL_USERNAME and settings.KAFKA_SASL_PASSWORD:
                kwargs["sasl_mechanism"] = (settings.KAFKA_SASL_MECHANISM or "SCRAM-SHA-256").upper()
                kwargs["sasl_plain_username"] = settings.KAFKA_SASL_USERNAME
                kwargs["sasl_plain_password"] = settings.KAFKA_SASL_PASSWORD

            cls._producer = KafkaProducer(**kwargs)
            logger.info("KafkaProducer connected to %s (Aiven SSL=%s, SASL=%s)", brokers, use_ssl, bool(settings.KAFKA_SASL_USERNAME))
        except Exception as e:
            logger.warning("Could not initialize KafkaProducer (offline/disabled): %s", e)
            cls._producer = None
        return cls._producer



    @classmethod
    def emit_task_event(cls, event_type: str, payload: dict[str, Any]) -> None:
        producer = cls.get_producer()
        if not producer:
            return
        event = {
            "type": event_type,
            "source": "mcp-gateway",
            "payload": payload,
        }
        try:
            producer.send(settings.TOPIC_TASK_EVENTS, value=event)
        except KafkaError as e:
            logger.warning("Failed to emit task event to Kafka: %s", e)

    @classmethod
    def emit_missing_tool_event(
        cls,
        requested_tool: str,
        category: str,
        org_id: str = "default",
        user_id: str = "unknown",
    ) -> None:
        producer = cls.get_producer()
        if not producer:
            return
        event = {
            "type": "unsupported_tool_invoked",
            "requested_tool": requested_tool,
            "category": category,
            "org_id": org_id,
            "user_id": user_id,
        }
        try:
            producer.send(settings.TOPIC_MISSING_TOOLS, value=event)
            logger.info("Emitted unsupported tool telemetry for '%s' in category '%s'", requested_tool, category)
        except KafkaError as e:
            logger.warning("Failed to emit missing tool telemetry to Kafka: %s", e)
