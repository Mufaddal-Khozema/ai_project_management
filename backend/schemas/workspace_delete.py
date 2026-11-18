from pydantic import BaseModel, Field


class DeleteWorkspaceRequest(BaseModel):
    confirmation: str = Field(min_length=1, max_length=32)


class DeleteWorkspaceResponse(BaseModel):
    message: str
