"""
End-to-end Kafka flow demo:
1. Produce login_success events
2. Consume and print them in real-time

Run from project root:
    python -m kafka_app.demo_flow

This script will:
- Send 5 test login_success events
- Consume and print all events (producer + any from server)
- Exit after consuming 5 events or 30 seconds
"""
import json
import logging
import threading
import time
from datetime import datetime, timezone
from typing import Iterable

from app.core.config import get_settings
from kafka_app.producer import AuthEventProducer, KafkaProducer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


def _topics_from_settings(settings) -> Iterable[str]:
    return (
        settings.kafka_topic_user_created,
        settings.kafka_topic_login_success,
        settings.kafka_topic_login_failed,
        settings.kafka_topic_token_refreshed,
    )


def producer_thread(duration_seconds: float = 5):
    """Send test events for a few seconds."""
    settings = get_settings()
    producer = KafkaProducer()
    events = AuthEventProducer(producer)

    logger.info("PRODUCER: Starting to send test events...")
    for i in range(5):
        user_id = f"test-user-{i}"
        email = f"user{i}@example.com"
        logger.info("PRODUCER: Sending login_success event for %s", email)
        events.login_success(user_id, email)
        time.sleep(0.5)

    producer.close()
    logger.info("PRODUCER: Closed.")


def consumer_thread(max_msgs: int = 10, timeout_seconds: float = 30):
    """Consume and print events in real-time."""
    settings = get_settings()

    try:
        from kafka import KafkaConsumer
    except Exception as exc:
        logger.error("Failed to import KafkaConsumer: %s", exc)
        raise

    topics = list(_topics_from_settings(settings))
    logger.info("CONSUMER: Subscribing to topics: %s", topics)

    consumer = KafkaConsumer(
        *topics,
        bootstrap_servers=settings.kafka_bootstrap_servers,
        auto_offset_reset="latest",  # Only new messages during this run
        enable_auto_commit=True,
        group_id=f"demo-consumer-{int(time.time())}",  # unique group per run
        value_deserializer=lambda v: json.loads(v.decode("utf-8")) if v else None,
        key_deserializer=lambda k: k.decode("utf-8") if k else None,
        consumer_timeout_ms=1000,  # 1s timeout between polls
    )

    start_time = time.time()
    msg_count = 0

    try:
        for msg in consumer:
            msg_count += 1
            logger.info("━" * 70)
            logger.info("CONSUMER: Received message #%d", msg_count)
            logger.info("  topic    : %s", msg.topic)
            logger.info("  partition: %s", msg.partition)
            logger.info("  offset   : %s", msg.offset)
            logger.info("  key      : %s", msg.key)
            try:
                logger.info(
                    "  value    : %s",
                    json.dumps(msg.value, indent=14),
                )
            except Exception:
                logger.info("  value    : %s", msg.value)

            if msg_count >= max_msgs:
                logger.info("CONSUMER: Reached max messages (%d). Stopping.", max_msgs)
                break

            elapsed = time.time() - start_time
            if elapsed > timeout_seconds:
                logger.info(
                    "CONSUMER: Timeout after %.1f seconds. Stopping.",
                    elapsed,
                )
                break

    except Exception as e:
        logger.error("CONSUMER error: %s", e, exc_info=True)
    finally:
        consumer.close()
        logger.info("CONSUMER: Closed.")


def main():
    logger.info("=" * 70)
    logger.info("Kafka End-to-End Flow Demo")
    logger.info("=" * 70)

    # Start producer in background
    prod_thread = threading.Thread(target=producer_thread, daemon=True)
    prod_thread.start()

    # Wait a bit for producer to queue some messages
    time.sleep(1)

    # Run consumer in main thread (blocking)
    consumer_thread(max_msgs=5, timeout_seconds=30)

    prod_thread.join(timeout=5)
    logger.info("=" * 70)
    logger.info("Demo complete!")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()
