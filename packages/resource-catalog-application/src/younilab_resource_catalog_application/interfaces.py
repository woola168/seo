from datetime import datetime
from typing import Protocol, runtime_checkable
from uuid import UUID

from younilab_resource_catalog_domain import Customer, ResourceStatus, SeoTask


@runtime_checkable
class CustomerRepository(Protocol):
    async def list_customers(
        self,
        *,
        search: str,
        status: ResourceStatus | None,
    ) -> list[Customer]: ...

    async def get_customer(self, customer_id: UUID) -> Customer | None: ...

    async def save_customer(self, customer: Customer) -> None: ...


@runtime_checkable
class TaskRepository(Protocol):
    async def list_tasks(
        self,
        *,
        search: str,
        customer_id: UUID | None,
        status: ResourceStatus | None,
    ) -> list[SeoTask]: ...

    async def get_task(self, task_id: UUID) -> SeoTask | None: ...

    async def save_task(self, task: SeoTask) -> None: ...


@runtime_checkable
class ResourceCatalogRepository(
    CustomerRepository,
    TaskRepository,
    Protocol,
):
    pass


class PermissionAuthorizer(Protocol):
    async def require(self, access_token: str, permission: str) -> None: ...


class Clock(Protocol):
    def now(self) -> datetime: ...


class IdGenerator(Protocol):
    def new_id(self) -> UUID: ...
