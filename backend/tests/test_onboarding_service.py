import pytest
from litestar.exceptions import HTTPException

from schemas.workspace import MatchItem, OnboardingRequest
from services import onboarding as onboarding_service


def _wire(monkeypatch, existing_workspace=None):
    calls = {"save_mapping": [], "matches": []}
    row = {
        "id": 5,
        "uuid": "223e4567-e89b-12d3-a456-426614174001",
        "company_name": "Acme",
        "onboarding_completed_at": None,
    }

    async def fake_find_by_email(email):
        return {"id": 7, "email": email}

    async def fake_find_workspace(user_id):
        return existing_workspace

    async def fake_create(user_id, values):
        return {**row, **values}

    async def fake_update(workspace_id, values):
        return {**row, **values}

    async def fake_add(*args, **kwargs):
        return {"id": 1}

    async def fake_save_mapping(**kwargs):
        calls["save_mapping"].append(kwargs)
        return {"id": 1, **kwargs}

    async def fake_create_matched_users(**kwargs):
        calls["matches"].append(kwargs)
        return []

    monkeypatch.setattr(onboarding_service.user_repo, "find_by_email", fake_find_by_email)
    monkeypatch.setattr(onboarding_service.workspace_repo, "find_by_user_id", fake_find_workspace)
    monkeypatch.setattr(onboarding_service.workspace_repo, "create", fake_create)
    monkeypatch.setattr(onboarding_service.workspace_repo, "update", fake_update)
    monkeypatch.setattr(onboarding_service.workspace_member_repo, "add", fake_add)
    monkeypatch.setattr(onboarding_service.project_service, "save_mapping", fake_save_mapping)
    monkeypatch.setattr(
        onboarding_service.members_service, "create_matched_users", fake_create_matched_users
    )
    return calls


async def test_onboarding_persists_mapping_without_matches(monkeypatch):
    calls = _wire(monkeypatch)
    await onboarding_service.submit_onboarding(
        "ada@example.com",
        OnboardingRequest(
            company_name="Acme",
            pm_platform="taiga",
            comm_platform="discord",
            project_id="10",
            channel_id="300",
        ),
    )
    assert calls["save_mapping"] == [
        {
            "workspace_id": 5,
            "pm_provider": "taiga",
            "project_id": "10",
            "comm_provider": "discord",
            "channel_id": "300",
        }
    ]
    assert calls["matches"] == []


async def test_onboarding_persists_mapping_and_matches(monkeypatch):
    calls = _wire(monkeypatch)
    await onboarding_service.submit_onboarding(
        "ada@example.com",
        OnboardingRequest(
            company_name="Acme",
            pm_platform="taiga",
            comm_platform="discord",
            project_id="10",
            channel_id="300",
            matches=[MatchItem(pm_member_id="1", comm_member_id="100")],
        ),
    )
    assert len(calls["save_mapping"]) == 1
    assert len(calls["matches"]) == 1


async def test_onboarding_updates_existing_workspace(monkeypatch):
    calls = _wire(monkeypatch, existing_workspace={"id": 5})
    await onboarding_service.submit_onboarding(
        "ada@example.com",
        OnboardingRequest(
            company_name="Acme",
            pm_platform="taiga",
            comm_platform="discord",
            project_id="10",
            channel_id="300",
        ),
    )
    assert calls["save_mapping"][0]["workspace_id"] == 5


@pytest.mark.parametrize(
    "body",
    [
        {"project_id": "10"},
        {"channel_id": "300"},
    ],
)
async def test_onboarding_rejects_partial_mapping(monkeypatch, body):
    calls = _wire(monkeypatch)
    with pytest.raises(HTTPException) as exc:
        await onboarding_service.submit_onboarding(
            "ada@example.com", OnboardingRequest(company_name="Acme", **body)
        )
    assert exc.value.status_code == 400
    assert calls["save_mapping"] == []


async def test_onboarding_rejects_unsupported_provider_pair(monkeypatch):
    calls = _wire(monkeypatch)
    with pytest.raises(HTTPException) as exc:
        await onboarding_service.submit_onboarding(
            "ada@example.com",
            OnboardingRequest(
                company_name="Acme",
                pm_platform="jira",
                comm_platform="discord",
                project_id="10",
                channel_id="300",
            ),
        )
    assert exc.value.status_code == 400
    assert calls["save_mapping"] == []


async def test_onboarding_without_ids_skips_mapping(monkeypatch):
    calls = _wire(monkeypatch)
    await onboarding_service.submit_onboarding(
        "ada@example.com", OnboardingRequest(company_name="Acme")
    )
    assert calls["save_mapping"] == []
