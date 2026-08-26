from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class SetupIntentRequest(BaseModel):
    name: str | None = None
    email: str
    price_id: str


class SetupIntentResponse(BaseModel):
    client_secret: str
    setup_intent_id: str
    customer_id: str | None = None


class PlanResponse(BaseModel):
    id: str
    name: str
    description: str
    price_monthly: int
    price_yearly: int
    price_id_monthly: str
    price_id_yearly: str
    features: list[str]
    badge: str | None = None
    highlighted: bool = False


class PlansResponse(BaseModel):
    plans: list[PlanResponse]


class SubscriptionResponse(BaseModel):
    plan_id: str
    plan_name: str
    billing_interval: str
    status: str
    price: int
    currency: str = "usd"
    current_period_end: datetime | None = None
    trial_end: datetime | None = None
    cancel_at_period_end: bool = False
    started_at: datetime | None = None


class CancelSubscriptionResponse(BaseModel):
    plan_id: str
    status: str
    cancel_at_period_end: bool
    effective_end: datetime


class InvoiceResponse(BaseModel):
    id: str
    number: str | None = None
    amount: int
    currency: str
    status: str
    created: datetime
    hosted_invoice_url: str | None = None
    invoice_pdf: str | None = None


class InvoicesResponse(BaseModel):
    invoices: list[InvoiceResponse]
