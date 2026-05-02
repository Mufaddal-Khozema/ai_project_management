"""
Simple local Kafka consumer for testing producer sends.

Run from the project root with the virtualenv activated:

python -m kafka_app.consumer_example

It subscribes to the same topics configured in `app.core.config` and prints
received messages (key, envelope). Useful to observe what
`future = self._producer.send(...)` produces.
"""
import json
import logging
from typing import Iterable

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def _topics_from_settings(settings) -> Iterable[str]:
    return (
        settings.kafka_topic_user_created,
        settings.kafka_topic_login_success,
        settings.kafka_topic_login_failed,
        settings.kafka_topic_token_refreshed,
    )


def main() -> None:
    settings = get_settings()

    try:
        from kafka import KafkaConsumer  # lazy import
    except Exception as exc:  # pragma: no cover - helpful runtime message
        print("kafka-python not available. Install with: pip install kafka-python")
        raise

    topics = list(_topics_from_settings(settings))
    print("Starting local test consumer for topics:", topics)

    consumer = KafkaConsumer(
        *topics,
        bootstrap_servers=settings.kafka_bootstrap_servers,
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        group_id="local-test-consumer",
        value_deserializer=lambda v: json.loads(v.decode("utf-8")) if v else None,
        key_deserializer=lambda k: k.decode("utf-8") if k else None,
    )

    try:
        for msg in consumer:
            print("--- received message ---")
            print("topic:", msg.topic, "partition:", msg.partition, "offset:", msg.offset)
            print("key:", msg.key)
            try:
                print("value:", json.dumps(msg.value, indent=2))
            except Exception:
                print("value (raw):", msg.value)
    except KeyboardInterrupt:
        print("Stopping consumer (KeyboardInterrupt)")
    finally:
        consumer.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
