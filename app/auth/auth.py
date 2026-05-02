"""
Falcon resource classes for all auth endpoints.

Each class maps HTTP verbs to AuthService methods and handles
request/response serialisation + error translation.
"""
import json
import logging

import falcon
from pydantic import ValidationError
from sqlalchemy.orm import Session

from kafka_app.producer import AuthEventProducer
from app.auth.schema import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
)
from app.auth.service import (
    AuthenticationError,
    AuthService,
    RegistrationError,
    TokenError,
)

logger = logging.getLogger(__name__)


def _parse_body(req: falcon.Request, schema_cls):
    """Deserialise and validate the request body using *schema_cls*."""
    try:
        raw = req.bounded_stream.read()
        data = json.loads(raw)
        return schema_cls(**data)
    except json.JSONDecodeError:
        raise falcon.HTTPBadRequest(
            title="Bad Request", description="Request body must be valid JSON."
        )
    except ValidationError as exc:
        errors = exc.errors()
        raise falcon.HTTPUnprocessableEntity(
            title="Validation Error",
            description=str(errors),
        )


def _make_service(req: falcon.Request) -> AuthService:
    """Build an AuthService from request-scoped context."""
    db: Session = req.context.db
    events: AuthEventProducer = req.context.events
    return AuthService(db=db, events=events)


# ── /register ─────────────────────────────────────────────────────────────────

class RegisterResource:
    """POST /register — Create a new user account."""

    def on_post(self, req: falcon.Request, resp: falcon.Response) -> None:
        """
        ---
        summary: Register a new user
        tags:
          - Authentication
        requestBody:
          required: true
          content:
            application/json:
              schema: RegisterRequestSchema
              example:
                email: alice@example.com
                password: Str0ng!Pass
                username: alice
                phone: "+15550001234"
        responses:
          201:
            description: User registered successfully
            content:
              application/json:
                schema: RegisterResponseSchema
          409:
            description: Duplicate email / username / phone
          422:
            description: Validation error
        """
        payload = _parse_body(req, RegisterRequest)
        svc = _make_service(req)

        try:
            result = svc.register(
                email=payload.email,
                password=payload.password,
                username=payload.username,
                phone=payload.phone,
                org_id=payload.org_id,
            )
        except RegistrationError as exc:
            raise falcon.HTTPConflict(title="Conflict", description=str(exc))

        resp.status = falcon.HTTP_201
        resp.media = result.model_dump(mode="json")


# ── /login ────────────────────────────────────────────────────────────────────

class LoginResource:
    """POST /login — Authenticate and receive tokens."""

    def on_post(self, req: falcon.Request, resp: falcon.Response) -> None:
        """
        ---
        summary: Login with email and password
        tags:
          - Authentication
        requestBody:
          required: true
          content:
            application/json:
              schema: LoginRequestSchema
              example:
                email: alice@example.com
                password: Str0ng!Pass
        responses:
          200:
            description: Authentication successful
            content:
              application/json:
                schema: LoginResponseSchema
          401:
            description: Invalid credentials
          422:
            description: Validation error
        """
        payload = _parse_body(req, LoginRequest)
        svc = _make_service(req)

        try:
            result = svc.login(email=payload.email, password=payload.password)
        except AuthenticationError as exc:
            raise falcon.HTTPUnauthorized(title="Unauthorized", description=str(exc))

        resp.media = result.model_dump(mode="json")


# ── /refresh ──────────────────────────────────────────────────────────────────

class RefreshResource:
    """POST /refresh — Exchange a refresh token for a new access token."""

    def on_post(self, req: falcon.Request, resp: falcon.Response) -> None:
        """
        ---
        summary: Rotate refresh token and get a new access token
        tags:
          - Authentication
        requestBody:
          required: true
          content:
            application/json:
              schema: RefreshRequestSchema
              example:
                refresh_token: <your-refresh-token>
        responses:
          200:
            description: Token rotated successfully
            content:
              application/json:
                schema: RefreshResponseSchema
          401:
            description: Invalid or expired refresh token
          422:
            description: Validation error
        """
        payload = _parse_body(req, RefreshRequest)
        svc = _make_service(req)

        try:
            result = svc.refresh(raw_refresh_token=payload.refresh_token)
        except TokenError as exc:
            raise falcon.HTTPUnauthorized(title="Unauthorized", description=str(exc))

        resp.media = result.model_dump(mode="json")


# ── /health ───────────────────────────────────────────────────────────────────

class HealthResource:
    """GET /health — Simple liveness probe."""

    def on_get(self, req: falcon.Request, resp: falcon.Response) -> None:
        resp.media = {"status": "ok"}
