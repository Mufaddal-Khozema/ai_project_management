from __future__ import annotations

import structlog

from litestar.events import listener

from lib.email import send_email
from lib.events import Events

logger = structlog.get_logger(__name__)


@listener(Events.OTP_SEND)
async def send_otp_email(email: str, otp: str) -> None:
    logger.info("sending OTP email", email=email)
    await send_email(
        to=email,
        subject="Your CoordinaAI verification code",
        template_name="otp",
        otp=otp,
        email=email,
    )


@listener(Events.PAYMENT_CONFIRMATION)
async def send_payment_confirmation_email(
    email: str,
    name: str,
    plan_name: str,
    price: str,
    billing_cycle: str,
    billing_url: str,
    support_email: str,
) -> None:
    logger.info("sending payment confirmation email", email=email)
    await send_email(
        to=email,
        subject="Your CoordinaAI plan is active",
        template_name="payment-confirmation",
        name=name,
        plan_name=plan_name,
        price=price,
        billing_cycle=billing_cycle,
        billing_url=billing_url,
        support_email=support_email,
    )


@listener(Events.RENEWAL_RECEIPT)
async def send_renewal_receipt_email(
    email: str,
    name: str,
    plan_name: str,
    amount: str,
    currency: str,
    period_start: str,
    period_end: str,
    invoice_url: str,
    support_email: str,
) -> None:
    logger.info("sending renewal receipt email", email=email)
    await send_email(
        to=email,
        subject="Your CoordinaAI receipt",
        template_name="renewal-receipt",
        name=name,
        plan_name=plan_name,
        amount=amount,
        currency=currency,
        period_start=period_start,
        period_end=period_end,
        invoice_url=invoice_url,
        support_email=support_email,
    )


@listener(Events.TRIAL_EXPIRY_WARNING)
async def send_trial_expiry_email(
    email: str,
    name: str,
    plan_name: str,
    days_left: str,
    billing_url: str,
    support_email: str,
) -> None:
    logger.info("sending trial expiry warning email", email=email, days_left=days_left)
    subject = (
        "Your CoordinaAI trial ends tomorrow"
        if days_left == "1"
        else f"Your CoordinaAI trial ends in {days_left} days"
    )
    await send_email(
        to=email,
        subject=subject,
        template_name="trial-expiry",
        name=name,
        plan_name=plan_name,
        days_left=days_left,
        billing_url=billing_url,
        support_email=support_email,
    )


@listener(Events.SUBSCRIPTION_CANCELLED)
async def send_subscription_cancelled_email(
    email: str,
    name: str,
    plan_name: str,
    access_until: str,
    reactivate_url: str,
    support_email: str,
) -> None:
    logger.info("sending subscription cancelled email", email=email)
    await send_email(
        to=email,
        subject="Your CoordinaAI subscription has been cancelled",
        template_name="subscription-cancelled",
        name=name,
        plan_name=plan_name,
        access_until=access_until,
        reactivate_url=reactivate_url,
        support_email=support_email,
    )


@listener(Events.TOKEN_EXPIRY_WARNING)
async def send_token_expiry_email(
    email: str,
    name: str,
    provider: str,
    days_left: str,
    reconnect_url: str,
    support_email: str,
) -> None:
    logger.info("sending token expiry warning email", email=email, provider=provider)
    await send_email(
        to=email,
        subject=f"Your {provider} connection expires soon",
        template_name="token-expiry",
        name=name,
        provider=provider,
        days_left=days_left,
        reconnect_url=reconnect_url,
        support_email=support_email,
    )
