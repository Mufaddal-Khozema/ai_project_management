from __future__ import annotations
from datetime import datetime, date
from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator
from typing import Optional, List, Literal

Resource = Literal["issues","tasks","userstories","epics"]


# Agent.py



class StatusInfo(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: Optional[str] = None

class UserInfo(BaseModel):
    model_config = ConfigDict(extra="ignore")
    full_name_display: Optional[str] = None

class TaigaItem(BaseModel):
    """One issue / task / user story / epic as returned by Taiga.
    extra="ignore" drops the dozens of fields we don't care about."""
 
    model_config = ConfigDict(extra="ignore")
 
    id: int
    ref: int
    version: Optional[int] = None
    subject: Optional[str] = None
    name: Optional[str] = None  # some resources use name instead of subject
    description: Optional[str] = None
    tags: Optional[list] = None  # Taiga may return [[name, color], ...] or [name, ...]
    due_date: Optional[date] = None
 
    # IDs (issues have priority/severity/type)
    priority: Optional[int] = None
    severity: Optional[int] = None
    type: Optional[int] = None
 
    status_extra_info: Optional[StatusInfo] = None
    assigned_to_extra_info: Optional[UserInfo] = None

# Compact summary returned to the LLM (replaces the dict in _summarize)
class ItemSummary(BaseModel):
    ref: int
    subject: Optional[str] = None
    status: Optional[str] = None
    assigned_to: Optional[str] = None
    due_date: Optional[date] = None
    priority: Optional[str] = None
    severity: Optional[str] = None
    type: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[list] = None
 
 
class ListResult(BaseModel):
    count: int
    shown: int
    items: list[ItemSummary]


# Tool input schemas (use with @tool(args_schema=...))
class ResolveDateInput(BaseModel):
    expression: str = Field(description="Natural-language date, e.g. 'next Friday'.")
 
 
class CreateItemInput(BaseModel):
    resource: Resource
    subject: str
    description: str = ""
    assigned_to: Optional[str] = Field(None, description="Assignee name or username, e.g. 'umer'.")
    priority: Optional[str] = Field(None, description="Priority name, e.g. 'high'.")
    severity: Optional[str] = Field(None, description="Severity name (issues only).")
    type: Optional[str] = Field(None, description="Issue type name (issues only), e.g. 'bug'.")
    status: Optional[str] = Field(None, description="Status name, e.g. 'in progress'.")
    due_date: Optional[date] = Field(None, description="ISO date; resolve relative dates first.")
 
 
class FetchItemInput(BaseModel):
    resource: Resource
    ref: int = Field(description="Taiga reference number, e.g. 'Epic #14' -> 14.")
 
 
class UpdateItemInput(BaseModel):
    resource: Resource
    ref: int
    subject: Optional[str] = None
    description: Optional[str] = None
    assigned_to: Optional[str] = None
    priority: Optional[str] = None
    severity: Optional[str] = None
    type: Optional[str] = None
    status: Optional[str] = None
    due_date: Optional[date] = None
    tags: Optional[list[str]] = None
 
 
class ListItemsInput(BaseModel):
    resource: Resource
    status: Optional[str] = None
    priority: Optional[str] = None
    severity: Optional[str] = None
    type: Optional[str] = None
    assigned_to: Optional[str] = None

class ItemResource(BaseModel):
    resource:Optional[str]
    subject:Optional[str]
    description:Optional[str] = ""
    assigned_to:Optional[str] = None
    priority: Optional[str] = None
    severity: Optional[str] = None
    type: Optional[str] = None
    status: Optional[str] = None
    due_date: Optional[str] = None

class User(BaseModel):
    uuid: str
    email: str
    status: str
    name: str
    avatar: Optional[str] = None

class WorkSpace(BaseModel):
    uuid: str
    company_name: Optional[str]

class Entitlments(BaseModel):
    has_subscription: bool    
    onboarding_completed: bool

class Integrations(BaseModel):
    provider: Optional[str]
    account_name: Optional[str]
    status: Optional[str]
    token_encrypted: Optional[str]

class Cached(BaseModel):
  cached_at : Optional[datetime]


class APIResponse(BaseModel):
    linked: bool
    user: User
    workspace: WorkSpace
    entitlements:Entitlments
    intergrations:List[Integrations]

# Identity.py
# Models
class _Base(BaseModel):
    model_config = ConfigDict(extra="ignore")
 
 
class IdentityUser(_Base):
    uuid: str
    name: Optional[str] = None
 
 
class Integration(_Base):
    provider: str
    status: str = "unknown"
    account_name: Optional[str] = None
    # SecretStr prints as '**********', so tokens can't leak through logs or repr().
    token: Optional[SecretStr] = None
    token_encrypted: Optional[SecretStr] = None

class Identity(_Base):
    linked: bool = False
    user: Optional[IdentityUser] = None
    integrations: list[Integration] = Field(default_factory=list)
 
    def integration(self, provider: str) -> Optional[Integration]:
        return next((i for i in self.integrations if i.provider == provider), None)
 
