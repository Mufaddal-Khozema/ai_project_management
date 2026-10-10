from __future__ import annotations

import structlog

from litestar import Request, Router, get, patch
from litestar.exceptions import HTTPException

from schemas.user import UpdateProfileRequest, UserResponse, WorkspaceMembersResponse, WorkspaceMemberResponse
from services import users as user_service

logger = structlog.get_logger(__name__)


@get("/users", sync_to_thread=False, operation_id="listWorkspaceUsers")
async def list_workspace_users(request: Request) -> WorkspaceMembersResponse:
    try:
        email = request.user.sub
        members = user_service.list_workspace_members(email)
        return WorkspaceMembersResponse(
            members=[WorkspaceMemberResponse(**m) for m in members]
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception("list workspace users failed")
        raise HTTPException(status_code=500, detail="Internal server error")


@get("/users/me", operation_id="getCurrentUser")
async def get_current_user(request: Request) -> UserResponse:
    try:
        email = request.user.sub
        return user_service.get_profile(email)
    except HTTPException:
        raise
    except Exception:
        logger.exception("get current user failed")
        raise HTTPException(status_code=500, detail="Internal server error")


@patch("/users/me", operation_id="updateCurrentUser")
async def update_current_user(
    request: Request,
    data: UpdateProfileRequest,
) -> UserResponse:
    try:
        email = request.user.sub
        return user_service.update_profile(email, data)
    except HTTPException:
        raise
    except Exception:
        logger.exception("update current user failed")
        raise HTTPException(status_code=500, detail="Internal server error")


router = Router(
    path="",
    route_handlers=[list_workspace_users, get_current_user, update_current_user],
    tags=["users"],
)
