from uuid import UUID

from younilab_seo.resource_catalog.application.errors import Conflict, ResourceNotFound
from younilab_seo.resource_catalog.application.interfaces import (
    AuthorizedPrincipal,
    Clock,
    IdGenerator,
    ResourceCatalogRepository,
)
from younilab_seo.resource_catalog.domain import Customer, ResourceStatus, SeoTask


class ManageResourceCatalog:
    """Tenant-scoped customer and SEO task lifecycle use case."""

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
        tenant_id: UUID,
        search: str = "",
        status: ResourceStatus | None = ResourceStatus.ACTIVE,
    ) -> list[Customer]:
        return await self._repository.list_customers(
            tenant_id=tenant_id,
            search=search,
            status=status,
        )

    async def get_customer(self, tenant_id: UUID, customer_id: UUID) -> Customer:
        customer = await self._repository.get_customer(tenant_id, customer_id)
        if customer is None:
            raise ResourceNotFound
        return customer

    async def create_customer(self, *, tenant_id: UUID, name: str) -> Customer:
        if any(
            customer.name.lower() == name.strip().lower()
            for customer in await self._repository.list_customers(
                tenant_id=tenant_id,
                search="",
                status=None,
            )
        ):
            raise Conflict("customer name already exists")
        now = self._clock.now()
        customer = Customer(
            id=self._id_generator.new_id(),
            tenant_id=tenant_id,
            name=name,
            status=ResourceStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await self._repository.save_customer(customer)
        return customer

    async def update_customer(
        self,
        tenant_id: UUID,
        customer_id: UUID,
        name: str,
    ) -> Customer:
        customer = await self.get_customer(tenant_id, customer_id)
        duplicate = next(
            (
                item
                for item in await self._repository.list_customers(
                    tenant_id=tenant_id,
                    search="",
                    status=None,
                )
                if item.id != customer_id and item.name.lower() == name.strip().lower()
            ),
            None,
        )
        if duplicate is not None:
            raise Conflict("customer name already exists")
        customer.update(name=name, updated_at=self._clock.now())
        await self._repository.save_customer(customer)
        return customer

    async def archive_customer(self, tenant_id: UUID, customer_id: UUID) -> None:
        customer = await self.get_customer(tenant_id, customer_id)
        customer.archive(self._clock.now())
        await self._repository.save_customer(customer)

    async def list_customers_for(
        self,
        principal: AuthorizedPrincipal,
        *,
        search: str = "",
        status: ResourceStatus | None = ResourceStatus.ACTIVE,
    ) -> list[Customer]:
        customers = await self.list_customers(
            tenant_id=principal.tenant_id,
            search=search,
            status=status,
        )
        if principal.has_global_resource_access:
            return customers
        return [
            customer
            for customer in customers
            if customer.id in principal.customer_ids
        ]

    async def get_customer_for(
        self,
        principal: AuthorizedPrincipal,
        customer_id: UUID,
    ) -> Customer:
        customer = await self.get_customer(principal.tenant_id, customer_id)
        self._require_customer_access(principal, customer.id)
        return customer

    async def update_customer_for(
        self,
        principal: AuthorizedPrincipal,
        customer_id: UUID,
        name: str,
    ) -> Customer:
        self._require_customer_access(principal, customer_id)
        return await self.update_customer(principal.tenant_id, customer_id, name)

    async def archive_customer_for(
        self,
        principal: AuthorizedPrincipal,
        customer_id: UUID,
    ) -> None:
        self._require_customer_access(principal, customer_id)
        await self.archive_customer(principal.tenant_id, customer_id)

    async def list_tasks(
        self,
        *,
        tenant_id: UUID,
        search: str = "",
        customer_id: UUID | None = None,
        status: ResourceStatus | None = ResourceStatus.ACTIVE,
    ) -> list[SeoTask]:
        if customer_id is not None:
            await self.get_customer(tenant_id, customer_id)
        return await self._repository.list_tasks(
            tenant_id=tenant_id,
            search=search,
            customer_id=customer_id,
            status=status,
        )

    async def get_task(self, tenant_id: UUID, task_id: UUID) -> SeoTask:
        task = await self._repository.get_task(tenant_id, task_id)
        if task is None:
            raise ResourceNotFound
        return task

    async def create_task(
        self,
        *,
        tenant_id: UUID,
        customer_id: UUID,
        name: str,
    ) -> SeoTask:
        customer = await self.get_customer(tenant_id, customer_id)
        if customer.status is not ResourceStatus.ACTIVE:
            raise Conflict("task customer is archived")
        now = self._clock.now()
        task = SeoTask(
            id=self._id_generator.new_id(),
            tenant_id=tenant_id,
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
        tenant_id: UUID,
        task_id: UUID,
        *,
        customer_id: UUID,
        name: str,
    ) -> SeoTask:
        customer = await self.get_customer(tenant_id, customer_id)
        if customer.status is not ResourceStatus.ACTIVE:
            raise Conflict("task customer is archived")
        task = await self.get_task(tenant_id, task_id)
        task.update(
            customer_id=customer_id,
            name=name,
            updated_at=self._clock.now(),
        )
        await self._repository.save_task(task)
        return task

    async def archive_task(self, tenant_id: UUID, task_id: UUID) -> None:
        task = await self.get_task(tenant_id, task_id)
        task.archive(self._clock.now())
        await self._repository.save_task(task)

    async def list_tasks_for(
        self,
        principal: AuthorizedPrincipal,
        *,
        search: str = "",
        customer_id: UUID | None = None,
        status: ResourceStatus | None = ResourceStatus.ACTIVE,
    ) -> list[SeoTask]:
        if customer_id is not None and not principal.has_global_resource_access:
            if customer_id not in principal.customer_ids:
                return []
        tasks = await self.list_tasks(
            tenant_id=principal.tenant_id,
            search=search,
            customer_id=customer_id,
            status=status,
        )
        if principal.has_global_resource_access:
            return tasks
        return [task for task in tasks if self._can_access_task(principal, task)]

    async def get_task_for(
        self,
        principal: AuthorizedPrincipal,
        task_id: UUID,
    ) -> SeoTask:
        task = await self.get_task(principal.tenant_id, task_id)
        self._require_task_access(principal, task)
        return task

    async def create_task_for(
        self,
        principal: AuthorizedPrincipal,
        *,
        customer_id: UUID,
        name: str,
    ) -> SeoTask:
        self._require_customer_access(principal, customer_id)
        return await self.create_task(
            tenant_id=principal.tenant_id,
            customer_id=customer_id,
            name=name,
        )

    async def update_task_for(
        self,
        principal: AuthorizedPrincipal,
        task_id: UUID,
        *,
        customer_id: UUID,
        name: str,
    ) -> SeoTask:
        task = await self.get_task_for(principal, task_id)
        if task.customer_id != customer_id:
            self._require_customer_access(principal, customer_id)
        return await self.update_task(
            principal.tenant_id,
            task_id,
            customer_id=customer_id,
            name=name,
        )

    async def archive_task_for(
        self,
        principal: AuthorizedPrincipal,
        task_id: UUID,
    ) -> None:
        task = await self.get_task_for(principal, task_id)
        await self.archive_task(principal.tenant_id, task.id)

    @staticmethod
    def _can_access_customer(
        principal: AuthorizedPrincipal,
        customer_id: UUID,
    ) -> bool:
        return (
            principal.has_global_resource_access
            or customer_id in principal.customer_ids
        )

    @classmethod
    def _require_customer_access(
        cls,
        principal: AuthorizedPrincipal,
        customer_id: UUID,
    ) -> None:
        if not cls._can_access_customer(principal, customer_id):
            raise ResourceNotFound

    @classmethod
    def _can_access_task(
        cls,
        principal: AuthorizedPrincipal,
        task: SeoTask,
    ) -> bool:
        return (
            principal.has_global_resource_access
            or task.id in principal.task_ids
            or task.customer_id in principal.customer_ids
        )

    @classmethod
    def _require_task_access(
        cls,
        principal: AuthorizedPrincipal,
        task: SeoTask,
    ) -> None:
        if not cls._can_access_task(principal, task):
            raise ResourceNotFound


ResourceCatalogService = ManageResourceCatalog
