from uuid import UUID

from younilab_resource_catalog_application.errors import Conflict, ResourceNotFound
from younilab_resource_catalog_application.interfaces import (
    Clock,
    IdGenerator,
    ResourceCatalogRepository,
)
from younilab_resource_catalog_domain import Customer, ResourceStatus, SeoTask


class ResourceCatalogService:
    def __init__(
        self,
        repository: ResourceCatalogRepository,
        clock: Clock,
        id_generator: IdGenerator,
    ) -> None:
        self._repository = repository
        self._clock = clock
        self._id_generator = id_generator

    async def list_customers(
        self,
        *,
        search: str = "",
        status: ResourceStatus | None = ResourceStatus.ACTIVE,
    ) -> list[Customer]:
        return await self._repository.list_customers(search=search, status=status)

    async def get_customer(self, customer_id: UUID) -> Customer:
        customer = await self._repository.get_customer(customer_id)
        if customer is None:
            raise ResourceNotFound
        return customer

    async def create_customer(self, name: str) -> Customer:
        if any(
            customer.name.lower() == name.strip().lower()
            for customer in await self._repository.list_customers(
                search="",
                status=None,
            )
        ):
            raise Conflict("customer name already exists")
        now = self._clock.now()
        customer = Customer(
            id=self._id_generator.new_id(),
            name=name,
            status=ResourceStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await self._repository.save_customer(customer)
        return customer

    async def update_customer(self, customer_id: UUID, name: str) -> Customer:
        customer = await self.get_customer(customer_id)
        customer.update(name=name, updated_at=self._clock.now())
        await self._repository.save_customer(customer)
        return customer

    async def archive_customer(self, customer_id: UUID) -> None:
        customer = await self.get_customer(customer_id)
        customer.archive(self._clock.now())
        await self._repository.save_customer(customer)

    async def list_tasks(
        self,
        *,
        search: str = "",
        customer_id: UUID | None = None,
        status: ResourceStatus | None = ResourceStatus.ACTIVE,
    ) -> list[SeoTask]:
        return await self._repository.list_tasks(
            search=search,
            customer_id=customer_id,
            status=status,
        )

    async def get_task(self, task_id: UUID) -> SeoTask:
        task = await self._repository.get_task(task_id)
        if task is None:
            raise ResourceNotFound
        return task

    async def create_task(self, *, customer_id: UUID, name: str) -> SeoTask:
        customer = await self.get_customer(customer_id)
        if customer.status is not ResourceStatus.ACTIVE:
            raise Conflict("task customer is archived")
        now = self._clock.now()
        task = SeoTask(
            id=self._id_generator.new_id(),
            customer_id=customer_id,
            name=name,
            status=ResourceStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await self._repository.save_task(task)
        return task

    async def update_task(
        self,
        task_id: UUID,
        *,
        customer_id: UUID,
        name: str,
    ) -> SeoTask:
        customer = await self.get_customer(customer_id)
        if customer.status is not ResourceStatus.ACTIVE:
            raise Conflict("task customer is archived")
        task = await self.get_task(task_id)
        task.update(
            customer_id=customer_id,
            name=name,
            updated_at=self._clock.now(),
        )
        await self._repository.save_task(task)
        return task

    async def archive_task(self, task_id: UUID) -> None:
        task = await self.get_task(task_id)
        task.archive(self._clock.now())
        await self._repository.save_task(task)
