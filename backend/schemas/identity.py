from datetime import datetime
from uuid import UUID

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class ResolveIdentityRequest(BaseModel):
    provider: str = Field(min_length=1, max_length=50)
    external_id: str = Field(min_length=1, max_length=255)
    guild_id: str | None = Field(default=None, max_length=255)
    channel_id: str | None = Field(default=None, max_length=255)


class IdentityUser(BaseModel):
    uuid: UUID
    email: str | None
    status: str
    name: str | None
    avatar: str | None = None


class IdentityWorkspace(BaseModel):
    uuid: UUID
    company_name: str


class IdentityProject(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    provider: str = Field(validation_alias=AliasChoices("provider", "pm_provider"))
    project_id: str
    project_name: str | None = None
    project_slug: str | None = None
    comm_provider: str = "discord"
    guild_id: str | None = None
    channel_id: str


class IdentityEntitlements(BaseModel):
    has_subscription: bool = False
    onboarding_completed: bool = False


class IdentityIntegration(BaseModel):
    provider: str
    account_name: str | None
    status: str
    # Fernet-encrypted credential blob as stored in `integrations`.
    # Downstream services decode it with the shared
    # INTEGRATION_TOKEN_ENCRYPTION_KEY into a live access/refresh token pair.
    token_encrypted: str


class ResolveIdentityResponse(BaseModel):
    linked: bool = True
    user: IdentityUser
    workspace: IdentityWorkspace | None
    project: IdentityProject | None = None
    entitlements: IdentityEntitlements
    integrations: list[IdentityIntegration]
    cached_at: datetime | None = None
