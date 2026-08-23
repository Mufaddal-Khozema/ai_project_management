from datetime import datetime, timezone
from typing import Any

from lib.tables import Subscription


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def find_by_user_id(user_id: int) -> dict[str, Any] | None:
    rows = Subscription.select().where(Subscription.user_id == user_id).run_sync()
    return rows[0] if rows else None


def find_by_subscription_id(stripe_subscription_id: str) -> dict[str, Any] | None:
    rows = (
        Subscription.select()
        .where(Subscription.stripe_subscription_id == stripe_subscription_id)
        .run_sync()
    )
    return rows[0] if rows else None


def upsert(user_id: int, values: dict[str, Any]) -> dict[str, Any]:
    existing = find_by_subscription_id(values["stripe_subscription_id"])
    if existing:
        return update(values["stripe_subscription_id"], values)
    row = (
        Subscription.insert(Subscription(user_id=user_id, **values))
        .returning(*Subscription.all_columns())
        .run_sync()
    )
    return row[0]


def update(stripe_subscription_id: str, values: dict[str, Any]) -> dict[str, Any]:
    updates: dict[Any, Any] = dict(values)
    updates.pop("stripe_subscription_id", None)
    updates[Subscription.updated_on] = utc_now()
    row = (
        Subscription.update(updates)
        .where(Subscription.stripe_subscription_id == stripe_subscription_id)
        .returning(*Subscription.all_columns())
        .run_sync()
    )
    return row[0]
