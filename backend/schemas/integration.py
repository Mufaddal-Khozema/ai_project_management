from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class IntegrationResponse(BaseModel):
    uuid: UUID
    provider: str
    account_name: str | None
    status: Literal["connected", "expired", "error"]
    expires_at: datetime | None
    last_synced_at: datetime | None
    created_on: datetime
    updated_on: datetime


class IntegrationsListResponse(BaseModel):
    integrations: list[IntegrationResponse]


class InitiateAuthRequest(BaseModel):
    redirect_source: Literal["onboarding", "settings"] = "settings"
    company_name: str | None = Field(default=None, max_length=255)


class InitiateAuthResponse(BaseModel):
    authorization_url: str


class TaigaConnectRequest(BaseModel):
    username: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=1, max_length=255)


class DisconnectResponse(BaseModel):
    message: str


class IntegrationMember(BaseModel):
    id: str
    name: str
    username: str
    email: str
    avatar: str


class IntegrationMembersResponse(BaseModel):
    provider: str
    account_name: str | None
    members: list[IntegrationMember]


class IntegrationScope(BaseModel):
    id: str
    name: str
    parent_id: str | None = None


class IntegrationScopesResponse(BaseModel):
    provider: str
    account_name: str | None
    scopes: list[IntegrationScope]