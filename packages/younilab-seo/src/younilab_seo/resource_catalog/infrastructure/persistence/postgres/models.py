from datetime import datetime
from uuid import UUID

from sqlalchemy import Column, DateTime, String, UniqueConstraint
from sqlmodel import Field, SQLModel


class CustomerRow(SQLModel, table=True):
    __tablename__ = "customer"
    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="ux_customer_tenant_name"),
    )

    id: UUID = Field(primary_key=True)
    tenant_id: UUID = Field(nullable=False, index=True)
    name: str = Field(sa_column=Column(String(200), nullable=False))
    status: str = Field(sa_column=Column(String(32), nullable=False))
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    updated_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))


class TaskRow(SQLModel, table=True):
    __tablename__ = "seo_task"

    id: UUID = Field(primary_key=True)
    tenant_id: UUID = Field(nullable=False, index=True)
    customer_id: UUID = Field(foreign_key="customer.id", nullable=False, index=True)
    name: str = Field(sa_column=Column(String(200), nullable=False))
    status: str = Field(sa_column=Column(String(32), nullable=False))
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    updated_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
