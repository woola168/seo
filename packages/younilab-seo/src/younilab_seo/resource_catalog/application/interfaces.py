from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, runtime_checkable
from uuid import UUID

from younilab_seo.resource_catalog.domain import Customer, ResourceStatus, SeoTask


@runtime_checkable
class CustomerRepository(Protocol):
    """Customer persistence boundary scoped by tenant."""

    async def list_customers(
        self,
        *,
        tenant_id: UUID,
        search: str,
        status: ResourceStatus | None,
    ) -> list[Customer]: ...

    async def get_customer(
        self,
        tenant_id: UUID,
        customer_id: UUID,
    ) -> Customer | None: ...

    async def save_customer(self, customer: Customer) -> None: ...


@runtime_checkable
class TaskRepository(Protocol):
    """SEO task persistence boundary scoped by tenant."""

    async def list_tasks(
        self,
        *,
        tenant_id: UUID,
        search: str,
        customer_id: UUID | None,
        status: ResourceStatus | None,
    ) -> list[SeoTask]: ...

    async def get_task(
        self,
        tenant_id: UUID,
        task_id: UUID,
    ) -> SeoTask | None: ...

    async def save_task(self, task: SeoTask) -> None: ...


@runtime_checkable
class ResourceCatalogRepository(
    CustomerRepository,
    TaskRepository,
    Protocol,
):
    """Persistence port used by resource catalog use cases."""

    pass


@dataclass(frozen=True)
class AuthorizedPrincipal:
    """Authorized request context returned by Access Control."""

    tenant_id: UUID
    permissions: frozenset[str]
    has_global_resource_access: bool
    customer_ids: frozenset[UUID]
    task_ids: frozenset[UUID]


class PermissionAuthorizer(Protocol):
    """Checks a bearer token and returns tenant-scoped authorization context."""

    async def require(
        self,
        access_token: str,
        permission: str,
    ) -> AuthorizedPrincipal: ...


class Clock(Protocol):
    """Application clock used when changing resource catalog records."""

    def now(self) -> datetime: ...


class IdGenerator(Protocol):
    """Identifier source used when creating resource catalog records."""

    def new_id(self) -> UUID: ...
