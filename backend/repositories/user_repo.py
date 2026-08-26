import uuid as uuid_lib
from datetime import datetime, timezone
from typing import Any

from lib.tables import User, UserStatus, UserStatusHistory


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def find_by_email(email: str) -> dict[str, Any] | None:
    rows = User.select().where(User.email == email).run_sync()
    return rows[0] if rows else None


def find_by_id(user_id: int) -> dict[str, Any] | None:
    rows = User.select().where(User.id == user_id).run_sync()
    return rows[0] if rows else None


def create_user(email: str, otp: str, otp_expires_at: datetime) -> dict[str, Any]:
    row = (
        User.insert(User(uuid=uuid_lib.uuid4(), email=email, otp=otp, otp_expires_at=otp_expires_at))
        .returning(*User.all_columns())
        .run_sync()
    )
    return row[0]


def update_otp(user_id: int, otp: str, otp_expires_at: datetime) -> None:
    User.update(
        {
            User.otp: otp,
            User.otp_expires_at: otp_expires_at,
            User.updated_on: utc_now(),
        }
    ).where(User.id == user_id).run_sync()


def update_status(user_id: int, new_status: Any) -> None:
    User.update(
        {
            User.status: new_status,
            User.updated_on: utc_now(),
        }
    ).where(User.id == user_id).run_sync()


def insert_status_history(user_id: int, status: Any) -> None:
    UserStatusHistory.insert(UserStatusHistory(user_id=user_id, status=status)).run_sync()


def update_social_login(user_id: int, provider: str, social_id: str, name: str, current_status: Any) -> None:
    values: dict[Any, Any] = {
        User.name: name,
        User.provider: provider,
        User.social_id: social_id,
        User.updated_on: utc_now(),
    }
    promote_to_verified = current_status is None or current_status == UserStatus.registered.value
    if promote_to_verified:
        values[User.status] = UserStatus.email_verified
    User.update(values).where(User.id == user_id).run_sync()
    if promote_to_verified:
        insert_status_history(user_id, UserStatus.email_verified)


def update_profile(user_id: int, name: str | None, avatar: str | None) -> dict[str, Any]:
    values: dict[Any, Any] = {User.updated_on: utc_now()}
    if name is not None:
        values[User.name] = name
    if avatar is not None:
        values[User.avatar] = avatar
    row = (
        User.update(values)
        .where(User.id == user_id)
        .returning(*User.all_columns())
        .run_sync()
    )
    return row[0]


def create_social_user(email: str, name: str, provider: str, social_id: str) -> dict[str, Any]:
    row = (
        User.insert(
            User(
                uuid=uuid_lib.uuid4(),
                email=email,
                name=name,
                provider=provider,
                social_id=social_id,
                status=UserStatus.email_verified,
            )
        )
        .returning(*User.all_columns())
        .run_sync()
    )
    insert_status_history(row[0]["id"], UserStatus.email_verified)
    return row[0]


def create_pending_user(
    email: str | None,
    name: str | None = None,
    avatar: str | None = None,
) -> dict[str, Any]:
    row = (
        User.insert(
            User(
                uuid=uuid_lib.uuid4(),
                email=email,
                name=name,
                avatar=avatar,
                status=UserStatus.pending,
            )
        )
        .returning(*User.all_columns())
        .run_sync()
    )
    insert_status_history(row[0]["id"], UserStatus.pending)
    return row[0]
