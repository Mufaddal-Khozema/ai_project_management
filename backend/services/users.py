from __future__ import annotations

import structlog

from litestar.exceptions import HTTPException

from repositories import payment_repo, user_repo, workspace_repo
from schemas.user import UpdateProfileRequest, UserResponse

logger = structlog.get_logger(__name__)


def _account_flags(user_id: int) -> tuple[bool, bool]:
    subscription = payment_repo.find_by_user_id(user_id)
    workspace = workspace_repo.find_by_user_id(user_id)
    has_subscription = subscription is not None
    onboarding_completed = workspace is not None and workspace.get("onboarding_completed_at") is not None
    return has_subscription, onboarding_completed


def get_profile(email: str) -> UserResponse:
    user = user_repo.find_by_email(email)
    if not user:
        logger.warning("user not found for profile", email=email)
        raise HTTPException(status_code=404, detail="User not found")
    has_subscription, onboarding_completed = _account_flags(user["id"])
    return UserResponse(
        uuid=user["uuid"],
        email=user["email"],
        status=user["status"],
        name=user.get("name"),
        avatar=user.get("avatar"),
        has_subscription=has_subscription,
        onboarding_completed=onboarding_completed,
        created_on=user["created_on"],
        updated_on=user["updated_on"],
    )


def update_profile(email: str, body: UpdateProfileRequest) -> UserResponse:
    user = user_repo.find_by_email(email)
    if not user:
        logger.warning("user not found for profile update", email=email)
        raise HTTPException(status_code=404, detail="User not found")
    updated = user_repo.update_profile(user["id"], body.name, body.avatar)
    has_subscription, onboarding_completed = _account_flags(user["id"])
    return UserResponse(
        uuid=updated["uuid"],
        email=updated["email"],
        status=updated["status"],
        name=updated.get("name"),
        avatar=updated.get("avatar"),
        has_subscription=has_subscription,
        onboarding_completed=onboarding_completed,
        created_on=updated["created_on"],
        updated_on=updated["updated_on"],
    )
