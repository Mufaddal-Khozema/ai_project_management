"""
Reusable Kafka producer with graceful degradation when Kafka is unavailable.
All messages are serialised to JSON.
"""
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class KafkaProducer:
    """
    Thin wrapper around ``kafka-python``'s ``KafkaProducer``.

    Gracefully handles the case where Kafka is unreachable (e.g. local dev
    without a running broker) by logging the event instead of crashing.
    """

    def __init__(self) -> None:
        self._producer = None
        self._connect()

    def _connect(self) -> None:
        """Attempt to connect to the Kafka broker. Failures are non-fatal."""
        try:
            from kafka import KafkaProducer as _KafkaProducer  # lazy import
            from kafka.errors import NoBrokersAvailable

            self._producer = _KafkaProducer(
                bootstrap_servers=settings.kafka_bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                key_serializer=lambda k: k.encode("utf-8") if k else None,
                acks="all",             # wait for leader + replicas
                retries=3,
                linger_ms=5,            # micro-batching
                compression_type="gzip",
            )
            logger.info("Kafka producer connected to %s", settings.kafka_bootstrap_servers)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Kafka unavailable — events will be logged only. Reason: %s", exc)
            self._producer = None

    def _build_envelope(self, event_type: str, data: dict[str, Any]) -> dict[str, Any]:
        """Wrap the payload in a standard CloudEvents-style envelope."""
        return {
            "id": str(uuid.uuid4()),
            "type": event_type,
            "source": "auth-service",
            "time": datetime.now(tz=timezone.utc).isoformat(),
            "data": data,
        }

    def publish(
        self,
        topic: str,
        event_type: str,
        data: dict[str, Any],
        key: str | None = None,
    ) -> None:
        """
        Publish an event to *topic*.

        Args:
            topic:      Kafka topic name.
            event_type: Logical event name (e.g. ``auth.user.created``).
            data:       Event payload dict.
            key:        Optional partition key (e.g. ``user_id``).
        """
        message = self._build_envelope(event_type, data)

        if self._producer is None:
            logger.info("[KAFKA-STUB] topic=%s event=%s payload=%s", topic, event_type, message)
            return

        try:
            future = self._producer.send(topic, value=message, key=key)
            self._producer.flush(timeout=5)
            record_metadata = future.get(timeout=10)
            logger.debug(
                "Kafka message sent | topic=%s partition=%s offset=%s",
                record_metadata.topic,
                record_metadata.partition,
                record_metadata.offset,
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to publish Kafka event: %s", exc)

    def close(self) -> None:
        """Flush pending messages and close the producer connection."""
        if self._producer:
            self._producer.close()


# ── Pre-built event helpers ───────────────────────────────────────────────────

class AuthEventProducer:
    """
    High-level facade that emits domain-specific auth events.
    """

    def __init__(self, producer: KafkaProducer) -> None:
        self._p = producer

    def user_created(self, user_id: str, email: str, org_id: str | None) -> None:
        self._p.publish(
            topic=settings.kafka_topic_user_created,
            event_type=settings.kafka_topic_user_created,
            data={"user_id": user_id, "email": email, "org_id": org_id},
            key=user_id,
        )

    def login_success(self, user_id: str, email: str) -> None:
        self._p.publish(
            topic=settings.kafka_topic_login_success,
            event_type=settings.kafka_topic_login_success,
            data={"user_id": user_id, "email": email},
            key=user_id,
        )

    def login_failed(self, email: str, reason: str) -> None:
        self._p.publish(
            topic=settings.kafka_topic_login_failed,
            event_type=settings.kafka_topic_login_failed,
            data={"email": email, "reason": reason},
            key=email,
        )

    def token_refreshed(self, user_id: str) -> None:
        self._p.publish(
            topic=settings.kafka_topic_token_refreshed,
            event_type=settings.kafka_topic_token_refreshed,
            data={"user_id": user_id},
            key=user_id,
        )
