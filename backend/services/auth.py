from datetime import datetime, timedelta

import structlog

from litestar.connection.request import Request
from litestar.exceptions import HTTPException

from lib import auth as lib_auth
from lib.auth import OTP_EXPIRE_SECONDS
from lib.events import Events
from lib.tables import UserStatus
from repositories import user_repo

logger = structlog.get_logger(__name__)


SIGNUP_ALLOWED_STATUSES = frozenset({UserStatus.registered.value, None})


def send_otp(email: str, request: Request) -> dict:
    try:
        otp = lib_auth.generate_secure_otp()
    except Exception:
        logger.exception("failed to generate OTP")
        raise HTTPException(status_code=500, detail="Failed to send OTP")

    user = user_repo.find_by_email(email)
    if user is not None and user["status"] not in SIGNUP_ALLOWED_STATUSES:
        logger.warning("otp rejected — user past signup", email=email, status=user["status"])
        raise HTTPException(status_code=409, detail="User already registered")

    expires_at = datetime.utcnow() + timedelta(seconds=OTP_EXPIRE_SECONDS)
    if user:
        user_repo.update_otp(user["id"], otp, expires_at)
    else:
        user_repo.create_user(email, otp, expires_at)

    request.app.emit(Events.OTP_SEND, email=email, otp=otp)
    return {"message": f"OTP sent to {email}", "expires_in_seconds": OTP_EXPIRE_SECONDS}


def verify_otp(email: str, otp: str) -> str:
    user = user_repo.find_by_email(email)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired OTP")

    if user["otp"] is None or user["otp_expires_at"] is None:
        raise HTTPException(status_code=401, detail="Invalid or expired OTP")

    if user["otp"] != otp:
        raise HTTPException(status_code=401, detail="Invalid or expired OTP")

    if user["otp_expires_at"] < datetime.utcnow():
        raise HTTPException(status_code=401, detail="Invalid or expired OTP")

    user_repo.update_status(user["id"], UserStatus.email_verified)
    user_repo.insert_status_history(user["id"], UserStatus.email_verified)

    return email
