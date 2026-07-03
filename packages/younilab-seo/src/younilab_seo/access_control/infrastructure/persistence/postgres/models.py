from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, JSON, String, Text, UniqueConstraint
from sqlmodel import Field, SQLModel

from younilab_seo.access_control.domain import (
    DEFAULT_TENANT_CODE,
    DEFAULT_TENANT_ID,
    DEFAULT_TENANT_NAME,
)


class TenantRow(SQLModel, table=True):
    __tablename__ = "tenant"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    code: str = Field(
        default=DEFAULT_TENANT_CODE,
        sa_column=Column(String(80), nullable=False, unique=True),
    )
    name: str = Field(
        default=DEFAULT_TENANT_NAME,
        sa_column=Column(String(200), nullable=False),
    )
    status: str = Field(default="active", sa_column=Column(String(32), nullable=False))
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    updated_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    disabled_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True)),
    )


class UserRow(SQLModel, table=True):
    __tablename__ = "user_account"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    tenant_id: UUID = Field(
        default=DEFAULT_TENANT_ID,
        foreign_key="tenant.id",
        nullable=False,
    )
    email: str = Field(sa_column=Column(String(320), nullable=False, unique=True))
    display_name: str = Field(sa_column=Column(String(200), nullable=False))
    status: str = Field(sa_column=Column(String(32), nullable=False))
    password_hash: str | None = Field(default=None, sa_column=Column(Text))
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    updated_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    department_id: UUID | None = Field(default=None, foreign_key="department.id")
    auth_provider: str = Field(default="password", nullable=False)
    last_login_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True)),
    )
    invited_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True)),
    )
    deleted_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True)),
    )


class DepartmentRow(SQLModel, table=True):
    __tablename__ = "department"
    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="ux_department_tenant_name"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    tenant_id: UUID = Field(
        default=DEFAULT_TENANT_ID,
        foreign_key="tenant.id",
        nullable=False,
    )
    name: str = Field(sa_column=Column(String(100), nullable=False))
    description: str = Field(default="", sa_column=Column(Text, nullable=False))
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    updated_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    archived_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True)),
    )


class RoleRow(SQLModel, table=True):
    __tablename__ = "role"
    __table_args__ = (UniqueConstraint("tenant_id", "name", name="ux_role_tenant_name"),)

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    tenant_id: UUID = Field(
        default=DEFAULT_TENANT_ID,
        foreign_key="tenant.id",
        nullable=False,
    )
    name: str = Field(sa_column=Column(String(100), nullable=False))
    permissions: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    is_system: bool = Field(default=False, nullable=False)
    has_global_resource_access: bool = Field(default=False, nullable=False)


class UserRoleRow(SQLModel, table=True):
    __tablename__ = "user_role"
    __table_args__ = (UniqueConstraint("user_id", "role_id", name="ux_user_role"),)

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="user_account.id", nullable=False)
    role_id: UUID = Field(foreign_key="role.id", nullable=False)


class CustomerAccessGrantRow(SQLModel, table=True):
    __tablename__ = "customer_access_grant"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "user_id",
            "customer_id",
            name="ux_tenant_user_customer_grant",
        ),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    tenant_id: UUID = Field(foreign_key="tenant.id", nullable=False, index=True)
    user_id: UUID = Field(foreign_key="user_account.id", nullable=False)
    customer_id: UUID = Field(nullable=False)


class TaskAccessGrantRow(SQLModel, table=True):
    __tablename__ = "task_access_grant"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "user_id",
            "task_id",
            name="ux_tenant_user_task_grant",
        ),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    tenant_id: UUID = Field(foreign_key="tenant.id", nullable=False, index=True)
    user_id: UUID = Field(foreign_key="user_account.id", nullable=False)
    task_id: UUID = Field(nullable=False)


class RefreshSessionRow(SQLModel, table=True):
    __tablename__ = "refresh_session"

    id: UUID = Field(primary_key=True)
    user_id: UUID = Field(foreign_key="user_account.id", nullable=False)
    token_digest: str = Field(sa_column=Column(String(64), nullable=False, unique=True))
    family_id: UUID = Field(nullable=False, index=True)
    expires_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    revoked_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True)),
    )
    replaced_by_id: UUID | None = Field(default=None)


class PasswordResetRow(SQLModel, table=True):
    __tablename__ = "password_reset"

    id: UUID = Field(primary_key=True)
    user_id: UUID = Field(foreign_key="user_account.id", nullable=False)
    token_digest: str = Field(sa_column=Column(String(64), nullable=False, unique=True))
    expires_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    used_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True)),
    )
    revoked_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True)),
    )


class InvitationRow(SQLModel, table=True):
    __tablename__ = "invitation"

    id: UUID = Field(primary_key=True)
    user_id: UUID = Field(foreign_key="user_account.id", nullable=False)
    email: str = Field(sa_column=Column(String(320), nullable=False))
    token_digest: str = Field(sa_column=Column(String(64), nullable=False, unique=True))
    expires_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    accepted_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True)),
    )
    revoked_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True)),
    )
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    created_by: UUID = Field(foreign_key="user_account.id", nullable=False)


class NotificationOutboxRow(SQLModel, table=True):
    __tablename__ = "notification_outbox"

    id: UUID = Field(primary_key=True)
    recipient: str = Field(sa_column=Column(String(320), nullable=False))
    template: str = Field(sa_column=Column(String(100), nullable=False))
    payload_ciphertext: str = Field(sa_column=Column(Text, nullable=False))
    status: str = Field(sa_column=Column(String(32), nullable=False))
    attempts: int = Field(default=0, nullable=False)
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    sent_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True)),
    )
    last_error: str | None = Field(default=None, sa_column=Column(Text))


ACCESS_CONTROL_TABLES = (
    TenantRow.__table__,
    DepartmentRow.__table__,
    UserRow.__table__,
    RoleRow.__table__,
    UserRoleRow.__table__,
    CustomerAccessGrantRow.__table__,
    TaskAccessGrantRow.__table__,
    RefreshSessionRow.__table__,
    PasswordResetRow.__table__,
    InvitationRow.__table__,
    NotificationOutboxRow.__table__,
)
