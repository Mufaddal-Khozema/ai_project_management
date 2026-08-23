from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class MatchItem(BaseModel):
    pm_member_id: str = Field(min_length=1, max_length=255)
    comm_member_id: str = Field(min_length=1, max_length=255)


class OnboardingRequest(BaseModel):
    company_name: str = Field(max_length=255)
    role: str | None = Field(default=None, max_length=50)
    team_size: str | None = Field(default=None, max_length=20)
    acquisition_source: str | None = Field(default=None, max_length=50)
    comm_platform: str | None = Field(default=None, max_length=50)
    pm_platform: str | None = Field(default=None, max_length=50)
    project_id: str | None = Field(default=None, max_length=255)
    channel_id: str | None = Field(default=None, max_length=255)
    matches: list[MatchItem] = Field(default_factory=list)

    @field_validator("company_name")
    @classmethod
    def strip_company_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("company_name must not be empty")
        return value


class WorkspaceResponse(BaseModel):
    uuid: UUID
    company_name: str
    role: str | None
    team_size: str | None
    acquisition_source: str | None
    comm_platform: str | None
    pm_platform: str | None
    created_on: datetime
    updated_on: datetime
