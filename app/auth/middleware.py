"""
FastAPI / Starlette middleware equivalents of the original Falcon middleware.

Provides:
 - `JWTAuthMiddleware` — validates Bearer tokens and attaches user context
 - `RateLimitMiddleware` — simple in-memory sliding-window rate limiter
"""
import logging
import time
from collections import defaultdict, deque
from typing import Any

import jwt
from fastapi import HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from config import get_settings
from service import decode_access_token


logger = logging.getLogger(__name__)
settings = get_settings()

# Routes exempt from JWT enforcement
_PUBLIC_ROUTES = frozenset(["/register", "/login", "/refresh", "/health", "/openapi.json", "/docs"])


class JWTAuthMiddleware(BaseHTTPMiddleware):
    """Validate Bearer JWT and attach decoded claims to `request.state.user`.

    Public routes are skipped.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path in _PUBLIC_ROUTES:
            return await call_next(request)

        auth_header: str | None = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing or malformed Authorization header.")

        token = auth_header[len("Bearer ") :]

        try:
            claims: dict[str, Any] = decode_access_token(token)
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Access token has expired. Please refresh.")
        except jwt.InvalidTokenError as exc:
            raise HTTPException(status_code=401, detail=str(exc))

        request.state.user = claims
        return await call_next(request)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """In-memory sliding-window rate limiter keyed by client IP.

    Not suitable for multi-process deployments.
    """

    def __init__(
        self,
        app,
        max_requests: int = settings.rate_limit_requests,
        window_seconds: int = settings.rate_limit_window_seconds,
    ) -> None:
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._windows: dict[str, deque] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next) -> Response:
        ip = (request.client.host if request.client else "unknown")
        now = time.monotonic()
        window = self._windows[ip]

        while window and window[0] < now - self.window_seconds:
            window.popleft()

        if len(window) >= self.max_requests:
            retry_after = int(self.window_seconds - (now - window[0])) + 1
            raise HTTPException(status_code=429, detail=f"Max {self.max_requests} requests per {self.window_seconds}s.")

        window.append(now)
        return await call_next(request)
