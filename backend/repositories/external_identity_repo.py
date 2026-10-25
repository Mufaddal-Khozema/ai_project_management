import uuid as uuid_lib
from datetime import datetime, timezone
from typing import Any

from lib.tables import ExternalIdentity


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


async def find_by_provider_external_id(
    provider: str, external_id: str
) -> ExternalIdentity | None:
    return await (
        ExternalIdentity.objects()
        .get(
            (ExternalIdentity.provider == provider)
            & (ExternalIdentity.external_id == external_id)
        )
        .run()
    )


async def find_user_id_by_provider_external_id(provider: str, external_id: str) -> int | None:
    row = await find_by_provider_external_id(provider, external_id)
    if row is None or row.user_id is None:
        return None
    return row.user_id


async def create(
    user_id: int,
    provider: str,
    external_id: str,
    email: str | None,
    name: str | None,
    username: str | None,
    avatar: str | None,
) -> dict[str, Any]:
    row = await (
        ExternalIdentity.insert(
            ExternalIdentity(
                uuid=uuid_lib.uuid4(),
                user_id=user_id,
                provider=provider,
                external_id=external_id,
                email=email,
                name=name,
                username=username,
                avatar=avatar,
                created_on=utc_now(),
                updated_on=utc_now(),
            )
        )
        .returning(*ExternalIdentity.all_columns())
        .run()
    )
    return row[0]
