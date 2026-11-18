from __future__ import annotations

from litestar.exceptions import HTTPException

from repositories import user_repo, workspace_repo
from services import payments as payment_service


async def delete_workspace(email: str, confirmation: str) -> None:
    if confirmation != "DELETE":
        raise HTTPException(status_code=400, detail="Type DELETE to confirm workspace deletion")

    user = await user_repo.find_by_email(email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    workspace = await workspace_repo.find_by_user_id(user["id"])
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    await payment_service.cancel_subscription_immediately(email)
    deleted = await workspace_repo.soft_delete(workspace["id"], workspace_repo.utc_now())
    if not deleted:
        raise HTTPException(status_code=409, detail="Workspace was already deleted")
