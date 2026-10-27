"""
scripts/create_kafka_topics.py
───────────────────────────────
Ensures all required Kafka topics exist on the Aiven cluster.
Reads connection credentials directly from .env.
"""
import os
import sys
from pathlib import Path
import dotenv

ROOT = Path(__file__).resolve().parent.parent
dotenv.load_dotenv(ROOT / ".env")

brokers_raw = os.environ.get("KAFKA_BROKERS", "")
if not brokers_raw:
    print("❌ KAFKA_BROKERS not set in .env")
    sys.exit(1)

brokers = [b.strip() for b in brokers_raw.split(",") if b.strip()]
ssl_flag = os.environ.get("KAFKA_SSL", "false").lower() == "true"
sasl_user = os.environ.get("KAFKA_SASL_USERNAME")
sasl_pass = os.environ.get("KAFKA_SASL_PASSWORD")
sasl_mech = (os.environ.get("KAFKA_SASL_MECHANISM", "SCRAM-SHA-256")).upper()
ssl_verify_raw = os.environ.get("KAFKA_SSL_VERIFY", "")
ssl_verify = ssl_verify_raw.lower() not in ("false", "0", "no") if ssl_verify_raw else False

TOPICS = [
    "agent-bridge.task-events",
    "agent-bridge.meeting-events",
    "agent-bridge.config-events",
    "agent-bridge.missing-tool-requests",
]

print(f"Connecting to Kafka brokers: {brokers} (SSL={ssl_flag}, SASL={sasl_mech})...")

kwargs = dict(
    bootstrap_servers=brokers,
    client_id="setup-topics-admin",
)

if ssl_flag:
    kwargs["security_protocol"] = "SASL_SSL" if sasl_user else "SSL"
    if not ssl_verify:
        import ssl
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        kwargs["ssl_context"] = ctx

if sasl_user:
    kwargs["sasl_mechanism"] = sasl_mech
    kwargs["sasl_plain_username"] = sasl_user
    kwargs["sasl_plain_password"] = sasl_pass

try:
    from kafka.admin import KafkaAdminClient, NewTopic
    admin = KafkaAdminClient(**kwargs)
    print("✅ Successfully authenticated to Aiven Kafka cluster!")

    existing_topics = set(admin.list_topics())
    print(f"Existing cluster topics: {existing_topics}")

    to_create = [t for t in TOPICS if t not in existing_topics]
    if not to_create:
        print("✅ All required topics already exist:")
        for t in TOPICS:
            print(f"   • {t}")
    else:
        print(f"Creating missing topics: {to_create}...")
        created = False
        for rf in (2, 1):
            try:
                new_topics = [NewTopic(name=t, num_partitions=1, replication_factor=rf) for t in to_create]
                admin.create_topics(new_topics=new_topics, validate_only=False)
                print(f"✅ Successfully created topics with replication_factor={rf}:")
                for t in to_create:
                    print(f"   • {t}")
                created = True
                break
            except Exception as e:
                print(f"   Attempt with replication_factor={rf} failed ({e}), trying next...")

        if not created:
            print("⚠️ Failed to create topics automatically. You can create them in Aiven Console.")

    admin.close()
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)
