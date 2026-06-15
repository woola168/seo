from uuid import UUID

from younilab_resource_catalog_domain import Customer, ResourceStatus, SeoTask


class MemoryResourceCatalogRepository:
    def __init__(self) -> None:
        self.customers: dict[UUID, Customer] = {}
        self.tasks: dict[UUID, SeoTask] = {}

    async def list_customers(
        self,
        *,
        search: str,
        status: ResourceStatus | None,
    ) -> list[Customer]:
        normalized = search.strip().lower()
        return sorted(
            (
                customer
                for customer in self.customers.values()
                if (status is None or customer.status is status)
                and (not normalized or normalized in customer.name.lower())
            ),
            key=lambda item: item.name.lower(),
        )

    async def get_customer(self, customer_id: UUID) -> Customer | None:
        return self.customers.get(customer_id)

    async def save_customer(self, customer: Customer) -> None:
        self.customers[customer.id] = customer

    async def list_tasks(
        self,
        *,
        search: str,
        customer_id: UUID | None,
        status: ResourceStatus | None,
    ) -> list[SeoTask]:
        normalized = search.strip().lower()
        return sorted(
            (
                task
                for task in self.tasks.values()
                if (status is None or task.status is status)
                and (customer_id is None or task.customer_id == customer_id)
                and (not normalized or normalized in task.name.lower())
            ),
            key=lambda item: item.name.lower(),
        )

    async def get_task(self, task_id: UUID) -> SeoTask | None:
        return self.tasks.get(task_id)

    async def save_task(self, task: SeoTask) -> None:
        self.tasks[task.id] = task
