from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from litestar.exceptions import HTTPException

from services import projects as project_service


@pytest.mark.asyncio
async def test_save_mapping_rejects_channel_owned_by_another_workspace(monkeypatch):
    existing = SimpleNamespace(workspace_id=99)
    monkeypatch.setattr(
        project_service.project_repo,
        "find_by_comm_channel",
        AsyncMock(return_value=existing),
    )

    async def fail_if_called(*args, **kwargs):
        raise AssertionError("provider resolution should not run")

    monkeypatch.setattr(project_service, "_resolve_project", fail_if_called)

    with pytest.raises(HTTPException) as exc_info:
        await project_service.save_mapping(
            workspace_id=1,
            pm_provider="taiga",
            project_id="10",
            comm_provider="discord",
            channel_id="300",
        )

    assert exc_info.value.status_code == 409
    assert "another workspace" in exc_info.value.detail
