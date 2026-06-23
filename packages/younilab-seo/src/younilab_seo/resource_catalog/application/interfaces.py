from datetime import datetime
from typing import Protocol, runtime_checkable
from uuid import UUID

from younilab_seo.resource_catalog.domain import Customer, ResourceStatus, SeoTask


@runtime_checkable
class CustomerRepository(Protocol):
    """customer master data 的 persistence port。"""

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
    """SEO task master data 的 persistence port。"""

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
    """resource catalog use cases 使用的整合 persistence port。"""

    pass


class PermissionAuthorizer(Protocol):
    """透過外部 authority 授權 resource catalog operations。"""

    async def require(self, access_token: str, permission: str) -> None:
        """允許 operation，或在拒絕與不確定時 raise AccessDenied。"""
        ...


class Clock(Protocol):
    """提供 resource catalog changes 使用的 application clock。"""

    def now(self) -> datetime: ...


class IdGenerator(Protocol):
    """建立 resource catalog records 的識別碼。"""

    def new_id(self) -> UUID: ...
