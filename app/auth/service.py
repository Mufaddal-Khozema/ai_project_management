"""
AuthService: pure business-logic layer — no HTTP, no Falcon specifics.
"""
import logging
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from kafka_app.producer import AuthEventProducer
from app.auth.model import RefreshToken, Role, User
from app.auth.schema import LoginResponse, RefreshResponse, RegisterResponse

logger = logging.getLogger(__name__)
settings = get_settings()


class AuthenticationError(Exception):
    """Raised when credentials are invalid."""


class RegistrationError(Exception):
    """Raised when registration pre-conditions fail."""


class TokenError(Exception):
    """Raised when a token is invalid, expired, or revoked."""


class AuthService:
    """
    Encapsulates all authentication operations.

    Args:
        db:       Active SQLAlchemy session (request-scoped).
        events:   Kafka event producer facade.
    """

    def __init__(self, db: Session, events: AuthEventProducer) -> None:
        self.db = db
        self.events = events

    # ── Private helpers ───────────────────────────────────────────────────────

    def _get_or_create_role(self, name: str) -> Role:
        role = self.db.query(Role).filter(Role.name == name).first()
        if not role:
            role = Role(name=name, description=f"Auto-created role: {name}")
            self.db.add(role)
            self.db.flush()
        return role

    def _create_refresh_token_record(self, user_id: uuid.UUID) -> str:
        """Generate, hash, persist, and return the raw refresh token."""
        raw_token = generate_refresh_token()
        token_hash = hash_refresh_token(raw_token)
        expires_at = datetime.now(tz=timezone.utc) + timedelta(
            days=settings.jwt_refresh_token_expire_days
        )
        record = RefreshToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        self.db.add(record)
        self.db.flush()
        return raw_token

    def _build_token_response(self, user: User, raw_refresh: str) -> dict:
        access_token = create_access_token(
            user_id=user.id,
            roles=user.role_names,
            org_id=user.org_id,
        )
        return {
            "access_token": access_token,
            "refresh_token": raw_refresh,
            "token_type": "bearer",
            "expires_in": settings.jwt_access_token_expire_minutes * 60,
        }

    # ── Public API ────────────────────────────────────────────────────────────

    def register(
        self,
        email: str,
        password: str,
        username: str | None = None,
        phone: str | None = None,
        org_id: uuid.UUID | None = None,
    ) -> RegisterResponse:
        """
        Register a new user.

        Raises:
            RegistrationError: Email, username, or phone already in use.
        """
        user = User(
            email=email.lower().strip(),
            username=username,
            phone=phone,
            password_hash=hash_password(password),
            org_id=org_id,
        )
        default_role = self._get_or_create_role(settings.default_role)
        user.roles.append(default_role)
        self.db.add(user)

        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            logger.warning("Registration failed — duplicate field: %s", exc.orig)
            raise RegistrationError(
                "An account with that email, username, or phone already exists."
            ) from exc

        self.db.refresh(user)
        logger.info("User registered: %s", user.id)

        # Fire-and-forget Kafka event
        self.events.user_created(
            user_id=str(user.id), email=user.email, org_id=str(user.org_id) if user.org_id else None
        )

        return RegisterResponse(
            user_id=user.id,
            email=user.email,
            username=user.username,
            created_at=user.created_at,
        )

    def login(self, email: str, password: str) -> LoginResponse:
        """
        Authenticate a user and issue tokens.

        Raises:
            AuthenticationError: Credentials are invalid or account is inactive.
        """
        user = self.db.query(User).filter(User.email == email.lower().strip()).first()

        if not user or not verify_password(password, user.password_hash):
            self.events.login_failed(email=email, reason="invalid_credentials")
            raise AuthenticationError("Invalid email or password.")

        if not user.is_active:
            self.events.login_failed(email=email, reason="account_inactive")
            raise AuthenticationError("Account is inactive.")

        raw_refresh = self._create_refresh_token_record(user.id)
        self.db.commit()

        self.events.login_success(user_id=str(user.id), email=user.email)
        logger.info("User logged in: %s", user.id)

        return LoginResponse(**self._build_token_response(user, raw_refresh))

    def refresh(self, raw_refresh_token: str) -> RefreshResponse:
        """
        Rotate a refresh token and issue a new access token.

        Raises:
            TokenError: Token not found, expired, or already revoked.
        """
        token_hash = hash_refresh_token(raw_refresh_token)
        record = (
            self.db.query(RefreshToken)
            .filter(RefreshToken.token_hash == token_hash)
            .first()
        )

        if not record or not record.is_valid:
            raise TokenError("Refresh token is invalid or has expired.")

        # Revoke the old token (rotation)
        record.revoked = True
        self.db.flush()

        user: User = record.user
        if not user.is_active:
            raise TokenError("Account is inactive.")

        new_raw_refresh = self._create_refresh_token_record(user.id)
        self.db.commit()

        self.events.token_refreshed(user_id=str(user.id))
        logger.info("Token refreshed for user: %s", user.id)

        return RefreshResponse(**self._build_token_response(user, new_raw_refresh))
