from __future__ import annotations

from datetime import datetime

from litestar.exceptions import HTTPException
import structlog
import stripe

from config import settings
from repositories import payment_repo, user_repo

logger = structlog.get_logger(__name__)

stripe.api_key = settings.stripe_secret_key

PLANS = [
    {
        "id": "starter",
        "name": "Starter",
        "description": "For small teams getting started with AI coordination.",
        "price_monthly": 4900,
        "price_yearly": 49000,
        "price_id_monthly": settings.stripe_price_monthly,
        "price_id_yearly": settings.stripe_price_yearly,
        "features": [
            "Up to 5 teammates",
            "AI daily standups",
            "Slack & Jira sync",
            "1 active project",
        ],
        "badge": None,
        "highlighted": False,
    },
    {
        "id": "professional",
        "name": "Professional",
        "description": "For growing teams that need full coordination.",
        "price_monthly": 14900,
        "price_yearly": 149000,
        "price_id_monthly": settings.stripe_price_monthly,
        "price_id_yearly": settings.stripe_price_yearly,
        "features": [
            "Up to 25 teammates",
            "Everything in Starter",
            "AI weekly reports",
            "Unlimited projects",
            "Priority support",
        ],
        "badge": "Most Popular",
        "highlighted": True,
    },
    {
        "id": "enterprise",
        "name": "Enterprise",
        "description": "For organizations with advanced needs.",
        "price_monthly": 0,
        "price_yearly": 0,
        "price_id_monthly": "",
        "price_id_yearly": "",
        "features": [
            "Unlimited teammates",
            "Everything in Professional",
            "Custom integrations",
            "Dedicated account manager",
            "On-premise deployment",
            "SLA guarantee",
        ],
        "badge": None,
        "highlighted": False,
    },
]


def get_plans() -> list[dict]:
    return PLANS


def create_setup_intent(name: str | None, email: str, price_id: str) -> dict:
    try:
        customer_data = {"email": email}
        if name:
            customer_data["name"] = name
        existing_customers = stripe.Customer.list(email=email, limit=1)
        if existing_customers.data:
            customer = existing_customers.data[0]
            stripe.Customer.modify(customer.id, **customer_data)
        else:
            customer = stripe.Customer.create(**customer_data)

        metadata = {"price_id": price_id, "email": email}
        if name:
            metadata["name"] = name

        setup_intent = stripe.SetupIntent.create(
            customer=customer.id,
            metadata=metadata,
            payment_method_types=["card"],
        )

        return {
            "client_secret": setup_intent.client_secret,
            "setup_intent_id": setup_intent.id,
            "customer_id": customer.id,
        }
    except stripe.StripeError as e:
        logger.error("stripe setup intent failed", error=str(e))
        raise


def handle_webhook(payload: bytes, sig_header: str) -> dict:
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.stripe_webhook_secret
        )
    except stripe.SignatureVerificationError as e:
        logger.error("webhook signature verification failed", error=str(e))
        raise

    event_type = event.type
    data = event.data.object

    if event_type == "setup_intent.succeeded":
        _handle_setup_succeeded(data)
    elif event_type == "setup_intent.setup_failed":
        _handle_setup_failed(data)
    elif event_type in ("customer.subscription.created", "customer.subscription.updated"):
        _handle_subscription_upsert(data)
    elif event_type == "customer.subscription.deleted":
        _handle_subscription_deleted(data)
    elif event_type in ("invoice.paid", "invoice.payment_failed"):
        logger.info(
            "invoice event received",
            event_type=event_type,
            customer=event.data.object.customer,
        )

    return {"received": True}


def _derive_plan_from_price(price_id: str) -> tuple[str, str, int]:
    for plan in PLANS:
        if plan["price_id_monthly"] and price_id == plan["price_id_monthly"]:
            return plan["id"], plan["name"], plan["price_monthly"]
        if plan["price_id_yearly"] and price_id == plan["price_id_yearly"]:
            return plan["id"], plan["name"], plan["price_yearly"]
    return "free", "Free", 0


def _derive_interval_from_price(price_id: str) -> str:
    for plan in PLANS:
        if plan["price_id_monthly"] and price_id == plan["price_id_monthly"]:
            return "monthly"
        if plan["price_id_yearly"] and price_id == plan["price_id_yearly"]:
            return "yearly"
    return "monthly"


def _ts_to_datetime(value: int | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromtimestamp(value)


def _price_id_from_subscription(subscription: stripe.Subscription) -> str:
    """Extract the active price id from a Stripe subscription object.

    `subscription.items` is a callable (list method) on this Stripe lib version,
    so fall back to dict-style lookup to get the inline `ListObject`. Works with
    plain attribute mocks too.
    """
    items = getattr(subscription, "items", None)
    if callable(items):
        items = subscription["items"] if "items" in subscription else None
    if items is None:
        return ""
    data = items.data if hasattr(items, "data") else None
    if not data:
        return ""
    first = data[0]
    price = getattr(first, "price", None)
    if price is None:
        return ""
    return getattr(price, "id", None) or ""


def get_current_subscription(email: str) -> dict:
    user = user_repo.find_by_email(email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    sub = payment_repo.find_by_user_id(user["id"])
    if not sub:
        return {
            "plan_id": "free",
            "plan_name": "Free",
            "billing_interval": "monthly",
            "status": "free",
            "price": 0,
            "current_period_end": None,
            "trial_end": None,
            "cancel_at_period_end": False,
            "started_at": None,
        }

    try:
        stripe_sub = stripe.Subscription.retrieve(sub["stripe_subscription_id"])
    except stripe.StripeError as e:
        logger.error("stripe retrieve subscription failed", error=str(e))
        raise HTTPException(status_code=502, detail="Stripe error")

    price_id = _price_id_from_subscription(stripe_sub)
    plan_id, plan_name, price = _derive_plan_from_price(price_id)
    billing_interval = _derive_interval_from_price(price_id)

    raw_status = stripe_sub.status
    cancel_at_period_end = bool(stripe_sub.cancel_at_period_end)
    if raw_status == "active" and cancel_at_period_end:
        status = "canceled"
    elif raw_status == "trialing":
        status = "trialing"
    elif raw_status == "canceled":
        status = "canceled"
    else:
        status = "active"

    return {
        "plan_id": plan_id,
        "plan_name": plan_name,
        "billing_interval": billing_interval,
        "status": status,
        "price": price,
        "current_period_end": _ts_to_datetime(stripe_sub.current_period_end),
        "trial_end": _ts_to_datetime(stripe_sub.trial_end),
        "cancel_at_period_end": cancel_at_period_end,
        "started_at": _ts_to_datetime(stripe_sub.created),
    }


def cancel_subscription(email: str) -> dict:
    user = user_repo.find_by_email(email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    sub = payment_repo.find_by_user_id(user["id"])
    if not sub:
        raise HTTPException(status_code=404, detail="No active subscription")

    if sub["cancel_at_period_end"]:
        raise HTTPException(status_code=409, detail="Subscription already cancelled")

    try:
        stripe_sub = stripe.Subscription.modify(
            sub["stripe_subscription_id"],
            cancel_at_period_end=True,
        )
    except stripe.StripeError as e:
        logger.error("stripe cancel subscription failed", error=str(e))
        raise HTTPException(status_code=502, detail=str(e))

    payment_repo.update(
        sub["stripe_subscription_id"],
        {
            "status": "canceled",
            "cancel_at_period_end": True,
        },
    )

    return {
        "plan_id": sub["plan_id"],
        "status": "canceled",
        "cancel_at_period_end": True,
        "effective_end": _ts_to_datetime(stripe_sub.current_period_end),
    }


def list_invoices(email: str) -> list[dict]:
    user = user_repo.find_by_email(email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    sub = payment_repo.find_by_user_id(user["id"])
    if not sub:
        raise HTTPException(status_code=404, detail="No subscription")

    try:
        invoices = stripe.Invoice.list(
            customer=sub["stripe_customer_id"],
            limit=24,
        )
    except stripe.StripeError as e:
        logger.error("stripe list invoices failed", error=str(e))
        raise HTTPException(status_code=502, detail="Stripe error")

    result = []
    for invoice in invoices.data:
        result.append(
            {
                "id": invoice.id,
                "number": invoice.number,
                "amount": invoice.amount_paid or 0,
                "currency": invoice.currency or "usd",
                "status": invoice.status or "unknown",
                "created": _ts_to_datetime(invoice.created),
                "hosted_invoice_url": invoice.hosted_invoice_url,
                "invoice_pdf": invoice.invoice_pdf,
            }
        )
    result.sort(key=lambda item: item["created"], reverse=True)
    return result


def _handle_subscription_upsert(subscription: stripe.Subscription) -> None:
    email = subscription.metadata.get("email")
    if not email:
        email = getattr(subscription.customer_details, "email", None)
    if not email:
        logger.warning("no email in subscription metadata", subscription_id=subscription.id)
        return

    user = user_repo.find_by_email(email)
    if not user:
        logger.warning("no user found for subscription email", email=email)
        return

    price_id = _price_id_from_subscription(subscription)
    plan_id, _, _ = _derive_plan_from_price(price_id)
    billing_interval = _derive_interval_from_price(price_id)

    payment_repo.upsert(
        user["id"],
        {
            "stripe_customer_id": subscription.customer,
            "stripe_subscription_id": subscription.id,
            "price_id": price_id,
            "plan_id": plan_id,
            "billing_interval": billing_interval,
            "status": subscription.status,
            "cancel_at_period_end": bool(subscription.cancel_at_period_end),
        },
    )
    logger.info("subscription upserted", user_id=user["id"], subscription_id=subscription.id)


def _handle_subscription_deleted(subscription: stripe.Subscription) -> None:
    existing = payment_repo.find_by_subscription_id(subscription.id)
    if not existing:
        logger.warning("deleted subscription not found locally", subscription_id=subscription.id)
        return
    payment_repo.update(
        subscription.id,
        {
            "status": "canceled",
            "cancel_at_period_end": True,
        },
    )
    logger.info("subscription marked canceled", subscription_id=subscription.id)


def _handle_setup_succeeded(setup_intent: stripe.SetupIntent) -> None:
    customer_id = setup_intent.customer
    payment_method = setup_intent.payment_method
    price_id = setup_intent.metadata.get("price_id")
    email = setup_intent.metadata.get("email")
    name = setup_intent.metadata.get("name")

    if not price_id:
        logger.warning("no price_id in setup_intent metadata", setup_intent_id=setup_intent.id)
        return

    try:
        stripe.Subscription.create(
            customer=customer_id,
            items=[{"price": price_id}],
            default_payment_method=payment_method,
            trial_period_days=14,
            metadata={"email": email or "", "name": name or ""},
        )
        logger.info(
            "subscription created with trial",
            customer=customer_id,
            price_id=price_id,
            trial_days=14,
        )
    except stripe.StripeError as e:
        logger.error("failed to create subscription", error=str(e))
        raise

    logger.info(
        "trial subscription created for user",
        email=email,
        price_id=price_id,
        customer_id=customer_id,
    )


def _handle_setup_failed(setup_intent: stripe.SetupIntent) -> None:
    logger.error(
        "setup intent failed",
        setup_intent_id=setup_intent.id,
        customer=setup_intent.customer,
        error=setup_intent.last_setup_error,
    )
