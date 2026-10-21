from datetime import datetime, timezone
from typing import Any

from lib.tables import Subscription


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


async def find_by_user_id(user_id: int) -> dict[str, Any] | None:
    rows = await Subscription.select().where(Subscription.user_id == user_id).run()
    return rows[0] if rows else None


async def find_by_subscription_id(stripe_subscription_id: str) -> dict[str, Any] | None:
    rows = await (
        Subscription.select()
        .where(Subscription.stripe_subscription_id == stripe_subscription_id)
        .run()
    )
    return rows[0] if rows else None


async def upsert(user_id: int, values: dict[str, Any]) -> dict[str, Any]:
    existing = await find_by_subscription_id(values["stripe_subscription_id"])
    if existing:
        return await update(values["stripe_subscription_id"], values)
    row = await (
        Subscription.insert(Subscription(user_id=user_id, **values))
        .returning(*Subscription.all_columns())
        .run()
    )
    return row[0]


async def update(stripe_subscription_id: str, values: dict[str, Any]) -> dict[str, Any]:
    updates: dict[Any, Any] = dict(values)
    updates.pop("stripe_subscription_id", None)
    updates[Subscription.updated_on] = utc_now()
    row = await (
        Subscription.update(updates)
        .where(Subscription.stripe_subscription_id == stripe_subscription_id)
        .returning(*Subscription.all_columns())
        .run()
    )
    return row[0]
