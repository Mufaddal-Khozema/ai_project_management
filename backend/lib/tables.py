from enum import Enum

from piccolo.columns import Boolean, ForeignKey, Integer, OnDelete, OnUpdate, Text, Timestamp, UUID, Varchar
from piccolo.columns.defaults import TimestampNow, UUID4
from piccolo.table import Table
from piccolo.utils.sync import run_sync

from lib.db import DB


class UserStatus(str, Enum):
    registered = "registered"
    pending = "pending"
    email_verified = "email_verified"


class IntegrationStatus(str, Enum):
    connected = "connected"
    expired = "expired"
    error = "error"


class UserAccountStatus(Varchar):
    """Native Postgres enum column backed by the `user_account_status` type."""

    @property
    def column_type(self) -> str:
        return "user_account_status"


class User(Table, tablename="users", db=DB):
    uuid = UUID(null=False, default=UUID4, unique=True)
    email = Varchar(length=255, null=True, unique=True)
    otp = Varchar(length=6, null=True, default=None)
    otp_expires_at = Timestamp(null=True, default=None)
    status = UserAccountStatus(
        length=50,
        null=False,
        default=UserStatus.registered,
        choices=UserStatus,
    )
    name = Varchar(length=255, null=True, default=None)
    provider = Varchar(length=50, null=True, default=None)
    social_id = Varchar(length=255, null=True, default=None)
    avatar = Varchar(length=512, null=True, default=None)
    created_on = Timestamp(null=False, default=TimestampNow())
    updated_on = Timestamp(null=False, default=TimestampNow())


class UserStatusHistory(Table, tablename="user_status", db=DB):
    user_id = ForeignKey(
        references=User,
        null=False,
        on_delete=OnDelete.no_action,
        on_update=OnUpdate.no_action,
    )
    status = UserAccountStatus(length=50, null=False, default=None, choices=UserStatus)
    changed_at = Timestamp(null=False, default=TimestampNow())


class Workspace(Table, tablename="workspace", db=DB):
    uuid = UUID(null=False, default=UUID4, unique=True)
    user_id = ForeignKey(
        references=User,
        null=False,
        unique=True,
        on_delete=OnDelete.cascade,
        on_update=OnUpdate.no_action,
    )
    company_name = Varchar(length=255, null=False)
    role = Varchar(length=50, null=True, default=None)
    team_size = Varchar(length=20, null=True, default=None)
    acquisition_source = Varchar(length=50, null=True, default=None)
    comm_platform = Varchar(length=50, null=True, default=None)
    pm_platform = Varchar(length=50, null=True, default=None)
    onboarding_completed_at = Timestamp(null=True, default=None)
    created_on = Timestamp(null=False, default=TimestampNow())
    updated_on = Timestamp(null=False, default=TimestampNow())


class WorkspaceMember(Table, tablename="workspace_members", db=DB):
    workspace_id = ForeignKey(
        references=Workspace,
        null=False,
        on_delete=OnDelete.cascade,
        on_update=OnUpdate.no_action,
    )
    user_id = ForeignKey(
        references=User,
        null=False,
        on_delete=OnDelete.cascade,
        on_update=OnUpdate.no_action,
    )
    role = Varchar(length=50, null=False, default="member")
    status = Varchar(length=50, null=False, default="pending")
    created_on = Timestamp(null=False, default=TimestampNow())
    updated_on = Timestamp(null=False, default=TimestampNow())


class Integration(Table, tablename="integrations", db=DB):
    uuid = UUID(null=False, default=UUID4, unique=True)
    workspace_id = ForeignKey(
        references=Workspace,
        null=False,
        on_delete=OnDelete.cascade,
        on_update=OnUpdate.no_action,
    )
    provider = Varchar(length=50, null=False)
    account_name = Varchar(length=255, null=True, default=None)
    token_encrypted = Text(null=False)
    scopes = Varchar(length=512, null=True, default=None)
    status = Varchar(length=20, null=False, default=IntegrationStatus.connected, choices=IntegrationStatus)
    expires_at = Timestamp(null=True, default=None)
    last_synced_at = Timestamp(null=True, default=None)
    created_on = Timestamp(null=False, default=TimestampNow())
    updated_on = Timestamp(null=False, default=TimestampNow())


class ExternalIdentity(Table, tablename="external_identities", db=DB):
    uuid = UUID(null=False, default=UUID4, unique=True)
    user_id = ForeignKey(
        references=User,
        null=True,
        on_delete=OnDelete.set_null,
        on_update=OnUpdate.no_action,
    )
    provider = Varchar(length=50, null=False)
    external_id = Varchar(length=255, null=False)
    email = Varchar(length=255, null=True, default=None)
    name = Varchar(length=255, null=True, default=None)
    username = Varchar(length=255, null=True, default=None)
    avatar = Varchar(length=512, null=True, default=None)
    created_on = Timestamp(null=False, default=TimestampNow())
    updated_on = Timestamp(null=False, default=TimestampNow())


class EmailLog(Table, tablename="email_log", db=DB):
    user_id = ForeignKey(
        references=User,
        null=False,
        on_delete=OnDelete.cascade,
        on_update=OnUpdate.no_action,
    )
    email_type = Varchar(length=100, null=False)
    entity_id = Integer(null=False, default=0)
    entity_type = Varchar(length=50, null=False)
    sent_at = Timestamp(null=False, default=TimestampNow())


class Subscription(Table, tablename="subscription", db=DB):
    uuid = UUID(null=False, default=UUID4, unique=True)
    user_id = ForeignKey(
        references=User,
        null=False,
        unique=True,
        on_delete=OnDelete.cascade,
        on_update=OnUpdate.no_action,
    )
    stripe_customer_id = Varchar(length=255, null=False)
    stripe_subscription_id = Varchar(length=255, null=False, unique=True)
    price_id = Varchar(length=255, null=False)
    plan_id = Varchar(length=50, null=False)
    billing_interval = Varchar(length=20, null=False)
    status = Varchar(length=20, null=False)
    cancel_at_period_end = Boolean(null=False, default=False)
    created_on = Timestamp(null=False, default=TimestampNow())
    updated_on = Timestamp(null=False, default=TimestampNow())

CREATE_USER_ACCOUNT_STATUS_DDL = """
CREATE TYPE user_account_status AS ENUM ('registered', 'pending', 'email_verified');
"""

CREATE_INTEGRATIONS_WORKSPACE_PROVIDER_UNIQUE_DDL = """
CREATE UNIQUE INDEX IF NOT EXISTS integrations_workspace_id_provider_idx
ON integrations (workspace_id, provider);
"""

CREATE_EXTERNAL_IDENTITIES_PROVIDER_EXTERNAL_ID_UNIQUE_DDL = """
CREATE UNIQUE INDEX IF NOT EXISTS external_identities_provider_external_id_idx
ON external_identities (provider, external_id);
"""

CREATE_WORKSPACE_MEMBERS_WORKSPACE_USER_UNIQUE_DDL = """
CREATE UNIQUE INDEX IF NOT EXISTS workspace_members_workspace_id_user_id_idx
ON workspace_members (workspace_id, user_id);
"""

CREATE_EMAIL_LOG_USER_EMAIL_TYPE_ENTITY_UNIQUE_DDL = """
CREATE UNIQUE INDEX IF NOT EXISTS email_log_user_id_email_type_entity_id_idx
ON email_log (user_id, email_type, entity_id);
"""


def create_user_account_status_type() -> None:
    run_sync(DB.run_ddl(CREATE_USER_ACCOUNT_STATUS_DDL, in_pool=False))


def create_integrations_indexes() -> None:
    run_sync(DB.run_ddl(CREATE_INTEGRATIONS_WORKSPACE_PROVIDER_UNIQUE_DDL, in_pool=False))


def create_external_identities_indexes() -> None:
    run_sync(DB.run_ddl(CREATE_EXTERNAL_IDENTITIES_PROVIDER_EXTERNAL_ID_UNIQUE_DDL, in_pool=False))


def create_workspace_members_index() -> None:
    run_sync(DB.run_ddl(CREATE_WORKSPACE_MEMBERS_WORKSPACE_USER_UNIQUE_DDL, in_pool=False))


def create_email_log_index() -> None:
    run_sync(DB.run_ddl(CREATE_EMAIL_LOG_USER_EMAIL_TYPE_ENTITY_UNIQUE_DDL, in_pool=False))


def create_all_tables() -> None:
    create_user_account_status_type()
    User.create_table(if_not_exists=True).run_sync()
    UserStatusHistory.create_table(if_not_exists=True).run_sync()
    Workspace.create_table(if_not_exists=True).run_sync()
    WorkspaceMember.create_table(if_not_exists=True).run_sync()
    Integration.create_table(if_not_exists=True).run_sync()
    ExternalIdentity.create_table(if_not_exists=True).run_sync()
    Subscription.create_table(if_not_exists=True).run_sync()
    EmailLog.create_table(if_not_exists=True).run_sync()
    create_integrations_indexes()
    create_external_identities_indexes()
    create_workspace_members_index()
    create_email_log_index()
