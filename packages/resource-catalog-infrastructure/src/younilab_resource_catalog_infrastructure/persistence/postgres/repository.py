from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from younilab_resource_catalog_domain import Customer, ResourceStatus, SeoTask
from younilab_resource_catalog_infrastructure.persistence.postgres.models import (
    CustomerRow,
    TaskRow,
)


class PostgresResourceCatalogRepository:
    """catalog persistence 使用的 PostgreSQL ResourceCatalogRepository adapter。"""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def list_customers(
        self,
        *,
        search: str,
        status: ResourceStatus | None,
    ) -> list[Customer]:
        statement = select(CustomerRow)
        if search.strip():
            statement = statement.where(
                CustomerRow.name.ilike(f"%{search.strip()}%")
            )
        if status is not None:
            statement = statement.where(CustomerRow.status == status.value)
        async with self._session_scope() as session:
            rows = (await session.scalars(statement.order_by(CustomerRow.name))).all()
            return [_customer_from_row(row) for row in rows]

    async def get_customer(self, customer_id: UUID) -> Customer | None:
        async with self._session_scope() as session:
            row = await session.get(CustomerRow, customer_id)
            return _customer_from_row(row) if row is not None else None

    async def save_customer(self, customer: Customer) -> None:
        async with self._session_scope() as session:
            row = await session.get(CustomerRow, customer.id)
            if row is None:
                row = CustomerRow(
                    id=customer.id,
                    name=customer.name,
                    status=customer.status.value,
                    created_at=customer.created_at,
                    updated_at=customer.updated_at,
                )
                session.add(row)
            row.name = customer.name
            row.status = customer.status.value
            row.updated_at = customer.updated_at

    async def list_tasks(
        self,
        *,
        search: str,
        customer_id: UUID | None,
        status: ResourceStatus | None,
    ) -> list[SeoTask]:
        statement = select(TaskRow)
        if search.strip():
            statement = statement.where(TaskRow.name.ilike(f"%{search.strip()}%"))
        if customer_id is not None:
            statement = statement.where(TaskRow.customer_id == customer_id)
        if status is not None:
            statement = statement.where(TaskRow.status == status.value)
        async with self._session_scope() as session:
            rows = (await session.scalars(statement.order_by(TaskRow.name))).all()
            return [_task_from_row(row) for row in rows]

    async def get_task(self, task_id: UUID) -> SeoTask | None:
        async with self._session_scope() as session:
            row = await session.get(TaskRow, task_id)
            return _task_from_row(row) if row is not None else None

    async def save_task(self, task: SeoTask) -> None:
        async with self._session_scope() as session:
            row = await session.get(TaskRow, task.id)
            if row is None:
                row = TaskRow(
                    id=task.id,
                    customer_id=task.customer_id,
                    name=task.name,
                    status=task.status.value,
                    created_at=task.created_at,
                    updated_at=task.updated_at,
                )
                session.add(row)
            row.customer_id = task.customer_id
            row.name = task.name
            row.status = task.status.value
            row.updated_at = task.updated_at

    @asynccontextmanager
    async def _session_scope(self) -> AsyncIterator[AsyncSession]:
        async with self._session_factory() as session:
            async with session.begin():
                yield session


def _customer_from_row(row: CustomerRow) -> Customer:
    return Customer(
        id=row.id,
        name=row.name,
        status=ResourceStatus(row.status),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _task_from_row(row: TaskRow) -> SeoTask:
    return SeoTask(
        id=row.id,
        customer_id=row.customer_id,
        name=row.name,
        status=ResourceStatus(row.status),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )
