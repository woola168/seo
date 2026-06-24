import asyncio
from datetime import UTC, datetime
from uuid import uuid4

from younilab_seo.resource_catalog.application import ResourceCatalogService
class FakeRepository:
    def __init__(self) -> None:
        self.customers = {}
        self.tasks = {}

    async def list_customers(self, *, search, status):
        return [
            item
            for item in self.customers.values()
            if status is None or item.status is status
        ]

    async def get_customer(self, customer_id):
        return self.customers.get(customer_id)

    async def save_customer(self, customer):
        self.customers[customer.id] = customer

    async def list_tasks(self, *, search, customer_id, status):
        return [
            item
            for item in self.tasks.values()
            if (status is None or item.status is status)
            and (customer_id is None or item.customer_id == customer_id)
        ]

    async def get_task(self, task_id):
        return self.tasks.get(task_id)

    async def save_task(self, task):
        self.tasks[task.id] = task


class FixedClock:
    def now(self):
        return datetime(2026, 6, 12, tzinfo=UTC)


class RandomIdGenerator:
    def new_id(self):
        return uuid4()


def test_customer_and_task_crud() -> None:
    async def scenario() -> None:
        service = ResourceCatalogService(
            FakeRepository(),
            FixedClock(),
            RandomIdGenerator(),
        )
        customer = await service.create_customer("Acme")
        task = await service.create_task(customer_id=customer.id, name="SEO audit")

        assert (await service.get_task(task.id)).customer_id == customer.id

    asyncio.run(scenario())
