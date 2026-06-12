from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, JSON, String, Text, UniqueConstraint
from sqlmodel import Field, SQLModel


class UserRow(SQLModel, table=True):
    __tablename__ = "user_account"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    email: str = Field(sa_column=Column(String(320), nullable=False, unique=True))
    display_name: str = Field(sa_column=Column(String(200), nullable=False))
    status: str = Field(sa_column=Column(String(32), nullable=False))
    password_hash: str | None = Field(default=None, sa_column=Column(Text))
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    updated_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))


class RoleRow(SQLModel, table=True):
    __tablename__ = "role"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(sa_column=Column(String(100), nullable=False, unique=True))
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
        UniqueConstraint("user_id", "customer_id", name="ux_user_customer_grant"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="user_account.id", nullable=False)
    customer_id: UUID = Field(nullable=False)


class TaskAccessGrantRow(SQLModel, table=True):
    __tablename__ = "task_access_grant"
    __table_args__ = (
        UniqueConstraint("user_id", "task_id", name="ux_user_task_grant"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
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
