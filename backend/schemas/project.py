from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class UpsertProjectRequest(BaseModel):
    pm_provider: Literal["taiga"] = "taiga"
    project_id: str = Field(min_length=1, max_length=255)
    comm_provider: Literal["discord"] = "discord"
    channel_id: str = Field(min_length=1, max_length=255)
    active: bool = True


class DeleteProjectResponse(BaseModel):
    message: str


class ProjectResponse(BaseModel):
    uuid: UUID
    pm_provider: str
    project_id: str
    project_name: str | None = None
    project_slug: str | None = None
    comm_provider: str
    guild_id: str | None = None
    channel_id: str
    active: bool
    created_on: datetime
    updated_on: datetime
