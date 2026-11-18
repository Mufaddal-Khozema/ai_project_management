from __future__ import annotations

import structlog

from litestar import Request, Router, delete
from litestar.exceptions import HTTPException

from schemas.workspace_delete import DeleteWorkspaceRequest, DeleteWorkspaceResponse
from services import workspaces as workspace_service

logger = structlog.get_logger(__name__)


@delete("/workspace", status_code=200, operation_id="deleteWorkspace")
async def delete_workspace(
    request: Request, data: DeleteWorkspaceRequest
) -> DeleteWorkspaceResponse:
    try:
        await workspace_service.delete_workspace(request.user.sub, data.confirmation)
        return DeleteWorkspaceResponse(message="deleted")
    except HTTPException:
        raise
    except Exception:
        logger.exception("workspace deletion failed")
        raise HTTPException(status_code=500, detail="Internal server error")


router = Router(path="", route_handlers=[delete_workspace], tags=["workspace"])
