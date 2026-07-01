from uuid import UUID

from younilab_seo.resource_catalog.domain import Customer, ResourceStatus, SeoTask


class MemoryResourceCatalogRepository:
    """In-process ResourceCatalogRepository adapter for tests and local runs."""

    def __init__(self) -> None:
        self.customers: dict[UUID, Customer] = {}
        self.tasks: dict[UUID, SeoTask] = {}

    async def list_customers(
        self,
        *,
        tenant_id: UUID,
        search: str,
        status: ResourceStatus | None,
    ) -> list[Customer]:
        normalized = search.strip().lower()
        return sorted(
            (
                customer
                for customer in self.customers.values()
                if customer.tenant_id == tenant_id
                and (status is None or customer.status is status)
                and (not normalized or normalized in customer.name.lower())
            ),
            key=lambda item: item.name.lower(),
        )

    async def get_customer(
        self,
        tenant_id: UUID,
        customer_id: UUID,
    ) -> Customer | None:
        customer = self.customers.get(customer_id)
        if customer is None or customer.tenant_id != tenant_id:
            return None
        return customer

    async def save_customer(self, customer: Customer) -> None:
        self.customers[customer.id] = customer

    async def list_tasks(
        self,
        *,
        tenant_id: UUID,
        search: str,
        customer_id: UUID | None,
        status: ResourceStatus | None,
    ) -> list[SeoTask]:
        normalized = search.strip().lower()
        return sorted(
            (
                task
                for task in self.tasks.values()
                if task.tenant_id == tenant_id
                and (status is None or task.status is status)
                and (customer_id is None or task.customer_id == customer_id)
                and (not normalized or normalized in task.name.lower())
            ),
            key=lambda item: item.name.lower(),
        )

    async def get_task(self, tenant_id: UUID, task_id: UUID) -> SeoTask | None:
        task = self.tasks.get(task_id)
        if task is None or task.tenant_id != tenant_id:
            return None
        return task

    async def save_task(self, task: SeoTask) -> None:
        self.tasks[task.id] = task
