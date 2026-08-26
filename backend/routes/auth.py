from datetime import timedelta

import structlog

from litestar import Request, Router, post
from litestar.exceptions import HTTPException
from litestar.response import Response

from config import settings
from lib.auth import (
    REFRESH_COOKIE_KEY,
    decode_refresh_token,
    jwt_auth,
    set_refresh_cookie,
)
from schemas.auth import (
    RefreshResponse,
    SendOTPRequest,
    SendOTPResponse,
    VerifyOTPRequest,
)
from services.auth import send_otp, verify_otp

logger = structlog.get_logger(__name__)


@post("/auth/email/send-otp")
async def send_otp_handler(data: SendOTPRequest, request: Request) -> SendOTPResponse:
    try:
        result = send_otp(email=data.email, request=request)
        return SendOTPResponse(**result)
    except HTTPException:
        raise
    except Exception:
        logger.exception("send OTP handler failed")
        raise HTTPException(status_code=500, detail="Internal server error")


@post("/auth/email/verify-otp")
async def verify_otp_handler(data: VerifyOTPRequest) -> Response:
    try:
        verified_email = verify_otp(email=data.email, otp=data.otp)
        response = jwt_auth.login(
            identifier=verified_email,
            token_expiration=timedelta(minutes=settings.jwt_expire_minutes),
            send_token_as_response_body=True,
        )
        return set_refresh_cookie(response, verified_email)
    except HTTPException:
        raise
    except Exception:
        logger.exception("verify OTP handler failed")
        raise HTTPException(status_code=500, detail="Internal server error")


@post("/auth/refresh")
async def refresh_handler(request: Request) -> RefreshResponse:
    try:
        refresh_token = request.cookies.get(REFRESH_COOKIE_KEY)
        if not refresh_token:
            raise HTTPException(status_code=401, detail="Missing refresh token")
        payload = decode_refresh_token(refresh_token)
        email = payload["sub"]
        expires_in = settings.jwt_expire_minutes * 60
        access_token = jwt_auth.create_token(
            identifier=email,
            token_expiration=timedelta(minutes=settings.jwt_expire_minutes),
        )
        content = RefreshResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=expires_in,
        )
        response = Response(content=content.model_dump())
        set_refresh_cookie(response, email)
        return response
    except HTTPException:
        raise
    except Exception:
        logger.exception("refresh handler failed")
        raise HTTPException(status_code=500, detail="Internal server error")


router = Router(
    path="",
    route_handlers=[send_otp_handler, verify_otp_handler, refresh_handler],
    tags=["auth"],
)
