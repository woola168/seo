import asyncio
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from younilab_seo.resource_catalog.application import (
    Conflict,
    ResourceCatalogService,
    ResourceNotFound,
)
from younilab_seo.resource_catalog.infrastructure import MemoryResourceCatalogRepository


class FixedClock:
    def now(self):
        return datetime(2026, 6, 12, tzinfo=UTC)


class RandomIdGenerator:
    def new_id(self):
        return uuid4()


def test_customer_and_task_crud_is_tenant_scoped() -> None:
    async def scenario() -> None:
        service = ResourceCatalogService(
            MemoryResourceCatalogRepository(),
            FixedClock(),
            RandomIdGenerator(),
        )
        tenant_id = uuid4()
        other_tenant_id = uuid4()

        customer = await service.create_customer(tenant_id=tenant_id, name="Acme")
        await service.create_customer(tenant_id=other_tenant_id, name="Acme")
        task = await service.create_task(
            tenant_id=tenant_id,
            customer_id=customer.id,
            name="SEO audit",
        )

        assert (await service.get_task(tenant_id, task.id)).customer_id == customer.id
        assert len(await service.list_customers(tenant_id=tenant_id)) == 1
        with pytest.raises(ResourceNotFound):
            await service.get_task(other_tenant_id, task.id)

    asyncio.run(scenario())


def test_customer_name_is_unique_inside_tenant() -> None:
    async def scenario() -> None:
        service = ResourceCatalogService(
            MemoryResourceCatalogRepository(),
            FixedClock(),
            RandomIdGenerator(),
        )
        tenant_id = uuid4()

        await service.create_customer(tenant_id=tenant_id, name="Acme")
        with pytest.raises(Conflict):
            await service.create_customer(tenant_id=tenant_id, name=" acme ")

    asyncio.run(scenario())


def test_task_customer_must_belong_to_same_tenant() -> None:
    async def scenario() -> None:
        service = ResourceCatalogService(
            MemoryResourceCatalogRepository(),
            FixedClock(),
            RandomIdGenerator(),
        )
        tenant_id = uuid4()
        other_tenant_id = uuid4()
        customer = await service.create_customer(
            tenant_id=other_tenant_id,
            name="Other",
        )

        with pytest.raises(ResourceNotFound):
            await service.create_task(
                tenant_id=tenant_id,
                customer_id=customer.id,
                name="SEO audit",
            )

    asyncio.run(scenario())
