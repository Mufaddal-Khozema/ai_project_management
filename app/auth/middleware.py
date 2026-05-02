"""
Falcon middleware components:
  - JWTAuthMiddleware   — validates Bearer tokens and attaches user context
  - RateLimitMiddleware — simple in-memory sliding-window rate limiter
"""
import logging
import time
from collections import defaultdict, deque
from typing import Any

import falcon
import jwt

from app.core.config import get_settings
from app.core.security import decode_access_token

logger = logging.getLogger(__name__)
settings = get_settings()

# Routes exempt from JWT enforcement
_PUBLIC_ROUTES = frozenset(["/register", "/login", "/refresh", "/health", "/openapi.json", "/docs"])


class JWTAuthMiddleware:
    """
    Process-request middleware that:
    1. Skips public routes.
    2. Extracts the ``Authorization: Bearer <token>`` header.
    3. Decodes and verifies the JWT.
    4. Attaches the decoded claims to ``req.context.user``.
    """

    def process_request(self, req: falcon.Request, resp: falcon.Response) -> None:
        # Allow public endpoints through without a token
        if req.path in _PUBLIC_ROUTES:
            return

        auth_header: str | None = req.get_header("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise falcon.HTTPUnauthorized(
                title="Unauthorized",
                description="Missing or malformed Authorization header.",
            )

        token = auth_header[len("Bearer "):]

        try:
            claims: dict[str, Any] = decode_access_token(token)
        except jwt.ExpiredSignatureError:
            raise falcon.HTTPUnauthorized(
                title="Token Expired",
                description="Access token has expired. Please refresh.",
            )
        except jwt.InvalidTokenError as exc:
            raise falcon.HTTPUnauthorized(
                title="Invalid Token",
                description=str(exc),
            )

        # Attach decoded claims so downstream resources can access them
        req.context.user = claims


class RateLimitMiddleware:
    """
    Sliding-window in-memory rate limiter keyed by client IP.

    Not suitable for multi-process deployments — replace with Redis-backed
    implementation for production clusters.

    Args:
        max_requests: Maximum allowed requests per *window_seconds*.
        window_seconds: Window duration in seconds.
    """

    def __init__(
        self,
        max_requests: int = settings.rate_limit_requests,
        window_seconds: int = settings.rate_limit_window_seconds,
    ) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        # ip → deque of timestamps
        self._windows: dict[str, deque] = defaultdict(deque)

    def process_request(self, req: falcon.Request, resp: falcon.Response) -> None:
        ip = req.remote_addr or "unknown"
        now = time.monotonic()
        window = self._windows[ip]

        # Evict timestamps outside the current window
        while window and window[0] < now - self.window_seconds:
            window.popleft()

        if len(window) >= self.max_requests:
            retry_after = int(self.window_seconds - (now - window[0])) + 1
            resp.set_header("Retry-After", str(retry_after))
            raise falcon.HTTPTooManyRequests(
                title="Rate Limit Exceeded",
                description=f"Max {self.max_requests} requests per {self.window_seconds}s.",
            )

        window.append(now)
