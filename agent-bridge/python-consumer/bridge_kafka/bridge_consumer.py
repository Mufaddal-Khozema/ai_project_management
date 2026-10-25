"""
bridge_kafka/bridge_consumer.py
────────────────────────────────
Kafka consumer for agent-bridge (Python side).
Reads task and meeting events published by the voice bot.
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
from typing import Callable, Any

from kafka import KafkaConsumer
from kafka.errors import KafkaConnectionError, KafkaError

logger = logging.getLogger("agent_bridge.kafka")

TOPICS = {
    "TASK_EVENTS":    "agent-bridge.task-events",
    "MEETING_EVENTS": "agent-bridge.meeting-events",
}


class BridgeConsumer:
    """
    Long-running Kafka consumer that dispatches events to registered handlers.
    Runs in a daemon thread — never blocks the Discord bot event loop.
    """

    def __init__(
        self,
        brokers: list[str],
        group_id: str = "agent-bridge-consumer",
        auto_offset_reset: str = "latest",
        sasl_username: str | None = None,
        sasl_password: str | None = None,
        sasl_mechanism: str = "PLAIN",
        ssl: bool = False,
        ssl_cafile: str | None = None,
        ssl_certfile: str | None = None,
        ssl_keyfile: str | None = None,
        ssl_verify: bool = True,
    ):
        self._brokers  = brokers
        self._group_id = group_id
        self._auto_offset_reset = auto_offset_reset
        self._sasl_username = sasl_username
        self._sasl_password = sasl_password
        self._sasl_mechanism = sasl_mechanism
        self._ssl = ssl
        self._ssl_cafile = ssl_cafile
        self._ssl_certfile = ssl_certfile
        self._ssl_keyfile = ssl_keyfile
        self._ssl_verify = ssl_verify
        self._handlers: dict[str, list[Callable[[dict], None]]] = {}
        self._running   = False
        self._thread: threading.Thread | None = None

    def on(self, event_type: str, handler: Callable[[dict], None]) -> None:
        """Register a handler for a specific eventType string."""
        self._handlers.setdefault(event_type, []).append(handler)

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread  = threading.Thread(
            target=self._consume_loop, daemon=True, name="kafka-consumer")
        self._thread.start()
        logger.info("Kafka consumer started (brokers=%s group=%s)", self._brokers, self._group_id)

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)

    def _build_admin_kwargs(self) -> dict[str, Any]:
        kwargs: dict[str, Any] = dict(
            bootstrap_servers=self._brokers,
            client_id=f"{self._group_id}-admin",
            reconnect_backoff_ms=500,
            reconnect_backoff_max_ms=10_000,
        )
        if self._ssl:
            kwargs["security_protocol"] = "SASL_SSL" if self._sasl_username else "SSL"
            if not self._ssl_verify:
                import ssl as _ssl_mod
                ctx = _ssl_mod.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = _ssl_mod.CERT_NONE
                kwargs["ssl_context"] = ctx
            elif self._ssl_cafile:
                kwargs["ssl_cafile"] = self._ssl_cafile
            if self._ssl_certfile:
                kwargs["ssl_certfile"] = self._ssl_certfile
            if self._ssl_keyfile:
                kwargs["ssl_keyfile"] = self._ssl_keyfile
        if self._sasl_username:
            kwargs["sasl_mechanism"]       = (self._sasl_mechanism or "PLAIN").upper()
            kwargs["sasl_plain_username"]  = self._sasl_username
            kwargs["sasl_plain_password"]  = self._sasl_password
            if not self._ssl:
                kwargs["security_protocol"] = "SASL_PLAINTEXT"
        return kwargs

    def _ensure_topics(self) -> None:
        try:
            from kafka.admin import KafkaAdminClient, NewTopic
            admin_kwargs = self._build_admin_kwargs()
            admin = KafkaAdminClient(**admin_kwargs)
            try:
                existing = set(admin.list_topics())
                needed = [t for t in TOPICS.values() if t not in existing]
                if needed:
                    logger.info("Creating missing Kafka topics on cluster: %s", needed)
                    for rf in (2, 1):
                        try:
                            new_topics = [NewTopic(name=t, num_partitions=1, replication_factor=rf) for t in needed]
                            admin.create_topics(new_topics=new_topics, validate_only=False)
                            logger.info("Successfully created Kafka topics (rf=%d): %s", rf, needed)
                            break
                        except Exception as e:
                            logger.debug("Failed creating topics with rf=%d: %s", rf, e)
            finally:
                admin.close()
        except Exception as e:
            logger.warning("Could not auto-create Kafka topics: %s", e)

    def _build_consumer(self) -> KafkaConsumer:
        kwargs: dict[str, Any] = dict(
            bootstrap_servers=self._brokers,
            group_id=self._group_id,
            auto_offset_reset=self._auto_offset_reset,
            enable_auto_commit=True,
            auto_commit_interval_ms=1000,
            value_deserializer=lambda v: json.loads(v.decode("utf-8")),
            consumer_timeout_ms=1000,
            reconnect_backoff_ms=500,
            reconnect_backoff_max_ms=10_000,
        )
        if self._ssl:
            kwargs["security_protocol"] = "SASL_SSL" if self._sasl_username else "SSL"
            if not self._ssl_verify:
                import ssl as _ssl_mod
                ctx = _ssl_mod.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = _ssl_mod.CERT_NONE
                kwargs["ssl_context"] = ctx
            elif self._ssl_cafile:
                kwargs["ssl_cafile"] = self._ssl_cafile
            if self._ssl_certfile:
                kwargs["ssl_certfile"] = self._ssl_certfile
            if self._ssl_keyfile:
                kwargs["ssl_keyfile"] = self._ssl_keyfile
        if self._sasl_username:
            kwargs["sasl_mechanism"]       = (self._sasl_mechanism or "PLAIN").upper()
            kwargs["sasl_plain_username"]  = self._sasl_username
            kwargs["sasl_plain_password"]  = self._sasl_password
            if not self._ssl:
                kwargs["security_protocol"] = "SASL_PLAINTEXT"
        return KafkaConsumer(
            TOPICS["TASK_EVENTS"],
            TOPICS["MEETING_EVENTS"],
            **kwargs,
        )

    def _consume_loop(self) -> None:
        self._ensure_topics()
        consumer: KafkaConsumer | None = None
        while self._running:
            try:
                if consumer is None:
                    consumer = self._build_consumer()
                    logger.info("Kafka consumer connected, subscribed to %s", list(TOPICS.values()))

                records = consumer.poll(timeout_ms=1000)
                if not records:
                    time.sleep(0.5)
                    continue

                for tp, messages in records.items():
                    for msg in messages:
                        if not self._running:
                            break
                        try:
                            self._dispatch(msg.value)
                        except Exception as e:
                            logger.error("Handler error on event %s: %s",
                                         msg.value.get("eventType"), e, exc_info=True)

            except (KafkaConnectionError, KafkaError) as e:
                logger.warning("Kafka error: %s — reconnecting in 10s", e)
                time.sleep(10)
                consumer = None
            except Exception as e:
                logger.error("Consumer loop error: %s — restarting in 5s", e, exc_info=True)
                time.sleep(5)
                consumer = None

        if consumer:
            consumer.close()
        logger.info("Kafka consumer stopped")

    def _dispatch(self, event: dict) -> None:
        event_type = event.get("eventType")
        if not event_type:
            logger.warning("Event missing eventType: %s", event)
            return
        for handler in self._handlers.get(event_type, []):
            try:
                handler(event)
            except Exception as e:
                logger.error("Handler %s failed for %s: %s", handler.__name__, event_type, e)


def build_consumer_from_env() -> BridgeConsumer | None:
    brokers_raw = os.environ.get("KAFKA_BROKERS", "")
    if not brokers_raw:
        logger.warning("KAFKA_BROKERS not set — Kafka consumer disabled")
        return None
    brokers = [b.strip() for b in brokers_raw.split(",") if b.strip()]
    invalid = [b for b in brokers if "://" in b or "/" in b]
    if invalid:
        logger.error(
            "Invalid KAFKA_BROKERS format: %s. Brokers must be 'host:port' (e.g. localhost:9092), not database connection URLs. Kafka consumer disabled.",
            invalid,
        )
        return None
    ssl_flag = os.environ.get("KAFKA_SSL", "").lower() == "true"
    if not ssl_flag and any("aivencloud.com" in b or "upstash.io" in b for b in brokers):
        logger.info("Cloud Kafka broker detected — automatically enabling SSL")
        ssl_flag = True

    ssl_cafile = os.environ.get("KAFKA_SSL_CAFILE")
    ssl_verify_raw = os.environ.get("KAFKA_SSL_VERIFY", "")
    if ssl_verify_raw:
        ssl_verify = ssl_verify_raw.lower() not in ("false", "0", "no")
    else:
        ssl_verify = bool(ssl_cafile)

    return BridgeConsumer(
        brokers=brokers,
        group_id=os.environ.get("KAFKA_GROUP_ID", "agent-bridge-consumer"),
        auto_offset_reset=os.environ.get("KAFKA_AUTO_OFFSET_RESET", "latest"),
        sasl_username=os.environ.get("KAFKA_SASL_USERNAME"),
        sasl_password=os.environ.get("KAFKA_SASL_PASSWORD"),
        sasl_mechanism=os.environ.get("KAFKA_SASL_MECHANISM", "PLAIN"),
        ssl=ssl_flag,
        ssl_cafile=ssl_cafile,
        ssl_certfile=os.environ.get("KAFKA_SSL_CERTFILE"),
        ssl_keyfile=os.environ.get("KAFKA_SSL_KEYFILE"),
        ssl_verify=ssl_verify,
    )
