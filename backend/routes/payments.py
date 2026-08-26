from __future__ import annotations

import structlog

from litestar import MediaType, Request, Router, get, post
from litestar.exceptions import HTTPException
from litestar.response import Response

from schemas.payment import (
    CancelSubscriptionResponse,
    InvoiceResponse,
    InvoicesResponse,
    PlanResponse,
    PlansResponse,
    SetupIntentRequest,
    SetupIntentResponse,
    SubscriptionResponse,
)
from services.payments import (
    cancel_subscription,
    create_setup_intent,
    get_current_subscription,
    get_plans,
    handle_webhook,
    list_invoices,
)

logger = structlog.get_logger(__name__)


@get("/payments/plans")
async def plans_handler() -> PlansResponse:
    try:
        plans = get_plans()
        return PlansResponse(plans=[PlanResponse(**p) for p in plans])
    except Exception:
        logger.exception("plans handler failed")
        raise HTTPException(status_code=500, detail="Internal server error")


@post("/payments/setup-intent")
async def setup_intent_handler(data: SetupIntentRequest) -> SetupIntentResponse:
    try:
        result = create_setup_intent(
            name=data.name,
            email=data.email,
            price_id=data.price_id,
        )
        return SetupIntentResponse(**result)
    except HTTPException:
        raise
    except Exception:
        logger.exception("setup intent handler failed")
        raise HTTPException(status_code=500, detail="Internal server error")


@post("/payments/webhook")
async def webhook_handler(request: Request) -> Response:
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        result = handle_webhook(payload, sig_header)
        return Response(content=result, media_type=MediaType.JSON)
    except Exception as e:
        logger.exception("webhook handler failed")
        return Response(
            content={"error": str(e)},
            status_code=400,
            media_type=MediaType.JSON,
        )


@get("/payments/current")
async def current_subscription_handler(request: Request) -> SubscriptionResponse:
    try:
        result = get_current_subscription(request.user.sub)
        return SubscriptionResponse(**result)
    except HTTPException:
        raise
    except Exception:
        logger.exception("current subscription handler failed")
        raise HTTPException(status_code=500, detail="Internal server error")


@post("/payments/cancel")
async def cancel_subscription_handler(request: Request) -> CancelSubscriptionResponse:
    try:
        result = cancel_subscription(request.user.sub)
        return CancelSubscriptionResponse(**result)
    except HTTPException:
        raise
    except Exception:
        logger.exception("cancel subscription handler failed")
        raise HTTPException(status_code=500, detail="Internal server error")


@get("/payments/invoices")
async def list_invoices_handler(request: Request) -> InvoicesResponse:
    try:
        result = list_invoices(request.user.sub)
        return InvoicesResponse(
            invoices=[InvoiceResponse(**invoice) for invoice in result]
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception("list invoices handler failed")
        raise HTTPException(status_code=500, detail="Internal server error")


router = Router(
    path="",
    route_handlers=[
        plans_handler,
        setup_intent_handler,
        webhook_handler,
        current_subscription_handler,
        cancel_subscription_handler,
        list_invoices_handler,
    ],
    tags=["payments"],
)
