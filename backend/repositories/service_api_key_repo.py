import uuid as uuid_lib
from typing import Any

from lib.tables import ServiceApiKey


async def find_by_key_hash(key_hash: str) -> dict[str, Any] | None:
    rows = await ServiceApiKey.select().where(ServiceApiKey.key_hash == key_hash).run()
    return rows[0] if rows else None


async def create(service_name: str, key_hash: str) -> dict[str, Any]:
    row = await (
        ServiceApiKey.insert(
            ServiceApiKey(
                uuid=uuid_lib.uuid4(),
                service_name=service_name,
                key_hash=key_hash,
            )
        )
        .returning(*ServiceApiKey.all_columns())
        .run()
    )
    return row[0]
