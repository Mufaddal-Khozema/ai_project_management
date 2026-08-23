from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class UserResponse(BaseModel):
    uuid: UUID
    email: str
    status: str
    name: str | None
    avatar: str | None = None
    has_subscription: bool = False
    onboarding_completed: bool = False
    created_on: datetime
    updated_on: datetime


class UpdateProfileRequest(BaseModel):
    name: str | None = None
    avatar: str | None = None


class UserStatusHistoryResponse(BaseModel):
    id: int
    user_id: int
    status: str
    changed_at: datetime
