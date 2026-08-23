import secrets
from datetime import datetime, timedelta

import jwt as pyjwt

from litestar.exceptions import HTTPException
from litestar.response import Response
from litestar.security.jwt import OAuth2PasswordBearerAuth

from config import settings

OTP_EXPIRE_SECONDS = 300

REFRESH_COOKIE_KEY = "refresh_token"


def generate_secure_otp(length: int = 6) -> str:
    return "".join(str(secrets.randbelow(10)) for _ in range(length))


def create_refresh_token(identifier: str) -> str:
    payload = {
        "sub": identifier,
        "exp": datetime.utcnow() + timedelta(days=settings.jwt_refresh_expire_days),
        "iat": datetime.utcnow(),
        "type": "refresh",
    }
    return pyjwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_refresh_token(token: str) -> dict:
    try:
        payload = pyjwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        return payload
    except pyjwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Refresh token expired")
    except pyjwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")


def set_refresh_cookie(response: Response, email: str) -> Response:
    refresh_token = create_refresh_token(email)
    response.set_cookie(
        key=REFRESH_COOKIE_KEY,
        value=refresh_token,
        httponly=True,
        samesite="lax",
        max_age=settings.jwt_refresh_expire_days * 86400,
        path="/api/auth/refresh",
    )
    return response


jwt_auth: OAuth2PasswordBearerAuth[dict] = OAuth2PasswordBearerAuth[dict](
    token_secret=settings.jwt_secret_key,
    token_url="/api/auth/login",
    algorithm=settings.jwt_algorithm,
    exclude=[
        "^/api/auth",
        "^/api/health",
        "^/docs",
        "^/schema",
        "^/api/payments/plans",
        "^/api/payments/webhook",
        "^/api/integrations/oauth",
    ],
    retrieve_user_handler=lambda data, conn: data,
)
