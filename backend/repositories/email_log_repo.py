from __future__ import annotations

from typing import Any

from lib.tables import EmailLog


def exists(user_id: int, email_type: str, entity_id: int) -> bool:
    rows = (
        EmailLog.select(EmailLog.id)
        .where(
            EmailLog.user_id == user_id,
            EmailLog.email_type == email_type,
            EmailLog.entity_id == entity_id,
        )
        .run_sync()
    )
    return bool(rows)


def insert(user_id: int, email_type: str, entity_id: int, entity_type: str) -> dict[str, Any]:
    row = (
        EmailLog.insert(
            EmailLog(
                user_id=user_id,
                email_type=email_type,
                entity_id=entity_id,
                entity_type=entity_type,
            )
        )
        .returning(*EmailLog.all_columns())
        .run_sync()
    )
    return row[0]