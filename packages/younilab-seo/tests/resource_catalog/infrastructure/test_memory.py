import asyncio
from datetime import UTC, datetime
from uuid import uuid4

from younilab_seo.resource_catalog.domain import Customer, ResourceStatus
from younilab_seo.resource_catalog.application import (
    CustomerRepository,
    ResourceCatalogRepository,
    TaskRepository,
)
from younilab_seo.resource_catalog.infrastructure import MemoryResourceCatalogRepository


def test_memory_repository_filters_archived_customers() -> None:
    async def scenario() -> None:
        repository = MemoryResourceCatalogRepository()
        now = datetime.now(UTC)
        customer = Customer(uuid4(), "Acme", ResourceStatus.ARCHIVED, now, now)
        await repository.save_customer(customer)

        assert await repository.list_customers(
            search="",
            status=ResourceStatus.ACTIVE,
        ) == []

    asyncio.run(scenario())


def test_memory_repository_implements_application_ports() -> None:
    repository = MemoryResourceCatalogRepository()

    assert isinstance(repository, CustomerRepository)
    assert isinstance(repository, TaskRepository)
    assert isinstance(repository, ResourceCatalogRepository)
