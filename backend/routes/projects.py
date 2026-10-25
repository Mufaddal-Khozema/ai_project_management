from __future__ import annotations

import structlog

from litestar import Request, Router, delete, get, put
from litestar.exceptions import HTTPException

from schemas.project import (
    DeleteProjectResponse,
    ProjectResponse,
    UpsertProjectRequest,
)
from services import projects as project_service

logger = structlog.get_logger(__name__)


@get("/projects", sync_to_thread=False, operation_id="listProjectMappings")
async def list_projects(request: Request) -> list[ProjectResponse]:
    try:
        rows = await project_service.list_mappings(request.user.sub)
        return [ProjectResponse(**row) for row in rows]
    except HTTPException:
        raise
    except Exception:
        logger.exception("project mapping list failed")
        raise HTTPException(status_code=500, detail="Internal server error")


@put("/projects", sync_to_thread=False, operation_id="upsertProjectMapping")
async def upsert_project(
    data: UpsertProjectRequest,
    request: Request,
) -> ProjectResponse:
    try:
        row = await project_service.upsert_mapping(request.user.sub, data)
        return ProjectResponse(**row)
    except HTTPException:
        raise
    except Exception:
        logger.exception("project mapping upsert failed")
        raise HTTPException(status_code=500, detail="Internal server error")


@delete(
    "/projects/{uuid:str}",
    sync_to_thread=False,
    status_code=200,
    operation_id="deleteProjectMapping",
)
async def delete_project(uuid: str, request: Request) -> DeleteProjectResponse:
    try:
        await project_service.delete_mapping(request.user.sub, uuid)
        return DeleteProjectResponse(message="deleted")
    except HTTPException:
        raise
    except Exception:
        logger.exception("project mapping delete failed")
        raise HTTPException(status_code=500, detail="Internal server error")


router = Router(
    path="",
    route_handlers=[list_projects, upsert_project, delete_project],
    tags=["projects"],
)
