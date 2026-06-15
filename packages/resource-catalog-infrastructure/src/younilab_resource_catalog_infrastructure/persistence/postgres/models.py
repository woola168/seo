from datetime import datetime
from uuid import UUID

from sqlalchemy import Column, DateTime, String
from sqlmodel import Field, SQLModel


class CustomerRow(SQLModel, table=True):
    __tablename__ = "customer"

    id: UUID = Field(primary_key=True)
    name: str = Field(sa_column=Column(String(200), nullable=False, unique=True))
    status: str = Field(sa_column=Column(String(32), nullable=False))
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    updated_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))


class TaskRow(SQLModel, table=True):
    __tablename__ = "seo_task"

    id: UUID = Field(primary_key=True)
    customer_id: UUID = Field(foreign_key="customer.id", nullable=False)
    name: str = Field(sa_column=Column(String(200), nullable=False))
    status: str = Field(sa_column=Column(String(32), nullable=False))
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    updated_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
