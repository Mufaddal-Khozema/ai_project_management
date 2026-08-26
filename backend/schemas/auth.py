from pydantic import BaseModel, EmailStr


class SendOTPRequest(BaseModel):
    email: EmailStr


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


class RefreshResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
