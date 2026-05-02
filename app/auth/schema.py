"""
Pydantic schemas for request validation and response serialisation.
"""
import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator


# ── Register ──────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    """Payload for POST /register."""

    email: EmailStr = Field(..., examples=["alice@example.com"])
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        examples=["Str0ng!Pass"],
    )
    username: str | None = Field(
        default=None, min_length=3, max_length=64, examples=["alice"]
    )
    phone: str | None = Field(
        default=None, max_length=30, examples=["+15550001234"]
    )
    org_id: uuid.UUID | None = Field(default=None)

    @field_validator("password")
    @classmethod
    def password_complexity(cls, v: str) -> str:
        """Enforce at least one digit and one uppercase character."""
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter.")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit.")
        return v


class RegisterResponse(BaseModel):
    """Response body for a successful registration."""

    user_id: uuid.UUID
    email: str
    username: str | None
    created_at: datetime
    message: str = "User registered successfully."

    model_config = {"from_attributes": True}


# ── Login ─────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    """Payload for POST /login."""

    email: EmailStr = Field(..., examples=["alice@example.com"])
    password: str = Field(..., examples=["Str0ng!Pass"])


class LoginResponse(BaseModel):
    """Response body for a successful login."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


# ── Refresh ───────────────────────────────────────────────────────────────────

class RefreshRequest(BaseModel):
    """Payload for POST /refresh."""

    refresh_token: str = Field(..., min_length=1)


class RefreshResponse(BaseModel):
    """Response body after a successful token rotation."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


# ── Error ─────────────────────────────────────────────────────────────────────

class ErrorResponse(BaseModel):
    """Standard error envelope."""

    error: str
    detail: str | None = None
