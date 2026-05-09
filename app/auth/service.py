"""
AuthService: pure business-logic layer — no HTTP, no Falcon specifics.
"""
import logging
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from producer import AuthEventProducer
from model import RefreshToken, Role, User, Organization, OrgMember
from schema import LoginResponse, RefreshResponse, RegisterResponse
from config import get_settings
import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from passlib.context import CryptContext

 

logger = logging.getLogger(__name__)
settings = get_settings()

# ── Password hashing (bcrypt) ──────────────────────────────────────────────────
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    """Return bcrypt hash of *plain* password."""
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Return True when *plain* matches *hashed*."""
    return _pwd_context.verify(plain, hashed)


# ── Refresh-token helpers ──────────────────────────────────────────────────────

def generate_refresh_token() -> str:
    """Generate a cryptographically-secure random refresh token (hex string)."""
    return secrets.token_hex(64)


def hash_refresh_token(token: str) -> str:
    """SHA-256 hash a refresh token before storing it in the database."""
    return hashlib.sha256(token.encode()).hexdigest()


# ── JWT ────────────────────────────────────────────────────────────────────────

def create_access_token(
    user_id: uuid.UUID,
    roles: list[str],
    org_id: uuid.UUID | None = None,
) -> str:
    """
    Mint a signed JWT access token.

    Args:
        user_id: The authenticated user's UUID (becomes ``sub`` claim).
        roles:   List of role names assigned to the user.
        org_id:  Optional organisation UUID.

    Returns:
        Encoded JWT string.
    """
    now = datetime.now(tz=timezone.utc)
    expire = now + timedelta(minutes=settings.jwt_access_token_expire_minutes)

    payload: dict[str, Any] = {
        "sub": str(user_id),
        "roles": roles,
        "org_id": str(org_id) if org_id else None,
        "iat": now,
        "exp": expire,
        "jti": str(uuid.uuid4()),  # unique token id — useful for future blocklisting
    }

    return jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def decode_access_token(token: str) -> dict[str, Any]:
    """
    Decode and verify a JWT access token.

    Raises:
        jwt.ExpiredSignatureError: Token has expired.
        jwt.InvalidTokenError:    Token is invalid.
    """
    return jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
    )

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
        role_name: str | None = None,
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
        default_role = self._get_or_create_role(role_name or settings.default_role)
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
    

    def create_organization(
        self,
        name: str,
        slug: str,
        admin_email: str,
        admin_password: str,
        admin_username: str | None = None,
        admin_phone: str | None = None,
    ) -> Organization:
        if self.db.query(Organization).filter(Organization.slug == slug).first():
            raise AuthenticationError(
                f"Organization with slug '{slug}' already exists.",
                code="ORG_ALREADY_EXISTS",
            )

        org_id = uuid.uuid4()

        # Create the admin user in the auth service
        admin_user = self.register(
            email=admin_email,
            password=admin_password,
            username=admin_username,
            phone=admin_phone,
            org_id=org_id,
            role_name="owner",
        )

        owner_user_id = admin_user.id
        org = Organization(id=org_id, name=name, slug=slug, owner_user_id=owner_user_id)
        self.db.add(org)
        self.db.add(
            OrgMember(
                org_id=org_id,
                user_id=owner_user_id,
                role="owner",
            )
        )
        self.db.commit()
        self.db.refresh(org)
        return org

    def create_org(
        self,
        name: str,
        slug: str,
        admin_email: str,
        admin_password: str,
        admin_username: str | None = None,
        admin_phone: str | None = None,
    ) -> Organization:
        return self.create_organization(
            name=name,
            slug=slug,
            admin_email=admin_email,
            admin_password=admin_password,
            admin_username=admin_username,
            admin_phone=admin_phone,
        )
    
    def get_org(self, org_id: str) -> Organization:
        org_uuid = uuid.UUID(org_id)
        org = self.db.query(Organization).filter(Organization.id == org_uuid).first()
        if not org:
            raise AuthenticationError(
                f"Organization with ID '{org_id}' not found.",
                code="ORG_NOT_FOUND",
            )
        return org

    def invite_member(self, org_id: str, user_id: str, role: str = "member") -> OrgMember:
        org = self.get_org(org_id)
        user_uuid = uuid.UUID(user_id)
        member = self.db.query(OrgMember).filter(
            OrgMember.org_id == org.id,
            OrgMember.user_id == user_uuid,
        ).first()
        if member:
            raise AuthenticationError(
                f"User '{user_id}' is already a member of organization '{org_id}'.",
                code="MEMBER_ALREADY_EXISTS",
            )

        member = OrgMember(org_id=org.id, user_id=user_uuid, role=role)
        self.db.add(member)
        self.db.commit()
        self.db.refresh(member)
        return member

    def remove_member(self, org_id: str, user_id: str) -> None:
        org = self.get_org(org_id)
        user_uuid = uuid.UUID(user_id)
        member = self.db.query(OrgMember).filter(
            OrgMember.org_id == org.id,
            OrgMember.user_id == user_uuid,
        ).first()
        if not member:
            raise AuthenticationError(
                f"User '{user_id}' is not a member of organization '{org_id}'.",
                code="MEMBER_NOT_FOUND",
            )

        self.db.delete(member)
        self.db.commit()

    def delete_organization(self, org_id: str) -> None:
        org = self.db.query(Organization).filter(Organization.id == org_id).first()
        if not org:
            raise AuthenticationError(
                f"Organization with ID '{org_id}' not found.",
                code="ORG_NOT_FOUND",
            )
        self.db.delete(org)
        self.db.commit()
    
