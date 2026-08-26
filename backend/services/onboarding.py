from __future__ import annotations

from typing import Any

import structlog

from litestar.exceptions import HTTPException

from repositories import user_repo, workspace_member_repo, workspace_repo
from schemas.workspace import OnboardingRequest
from services import members as members_service

logger = structlog.get_logger(__name__)


def _normalize(value: Any) -> Any:
    if isinstance(value, str) and not value.strip():
        return None
    return value


async def submit_onboarding(email: str, data: OnboardingRequest) -> tuple[dict, bool]:
    user = user_repo.find_by_email(email)
    if not user:
        logger.warning("user not found for onboarding", email=email)
        raise HTTPException(status_code=404, detail="User not found")

    workspace_fields = {
        "company_name",
        "role",
        "team_size",
        "acquisition_source",
        "comm_platform",
        "pm_platform",
    }
    provided = {
        field: value
        for field in data.model_fields_set
        if field in workspace_fields and (value := _normalize(getattr(data, field))) is not None
    }

    existing = workspace_repo.find_by_user_id(user["id"])
    if not existing:
        row = workspace_repo.create(user["id"], provided)
        logger.info(
            "workspace created from onboarding",
            user_id=user["id"],
            company_name=provided.get("company_name"),
        )
        created = True
    else:
        row = workspace_repo.update(existing["id"], provided)
        logger.info(
            "workspace updated from onboarding",
            user_id=user["id"],
            workspace_id=existing["id"],
        )
        created = False

    workspace_member_repo.add(
        row["id"],
        user["id"],
        role="owner",
        status="active",
    )

    if data.matches:
        pm_provider = _normalize(data.pm_platform)
        comm_provider = _normalize(data.comm_platform)
        if not pm_provider or not comm_provider:
            raise HTTPException(status_code=400, detail="Both platforms are required to match members")
        if not data.project_id or not data.channel_id:
            raise HTTPException(status_code=400, detail="Project and channel are required to match members")
        await members_service.create_matched_users(
            email=email,
            pm_provider=pm_provider,
            comm_provider=comm_provider,
            project_id=data.project_id,
            channel_id=data.channel_id,
            matches=[m.model_dump() for m in data.matches],
        )

    if row["onboarding_completed_at"] is None:
        row = workspace_repo.update(row["id"], {"onboarding_completed_at": workspace_repo.utc_now()})
        logger.info("workspace onboarding marked complete", user_id=user["id"], workspace_id=row["id"])

    return row, created
