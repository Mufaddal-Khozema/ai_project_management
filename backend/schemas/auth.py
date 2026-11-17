from typing import Literal

from pydantic import BaseModel, EmailStr


class SendOTPRequest(BaseModel):
    email: EmailStr
    purpose: Literal["signup", "signin"] = "signup"


class SendOTPResponse(BaseModel):
    message: str
    expires_in_seconds: int


class VerifyOTPRequest(BaseModel):
    email: EmailStr
    otp: str


class VerifyOTPResponse(BaseModel):
    access_token: str
    token_type: str
    refresh_token: str | None
    expires_in: int


class CreateSessionRequest(BaseModel):
    access_token: str


class RefreshResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
