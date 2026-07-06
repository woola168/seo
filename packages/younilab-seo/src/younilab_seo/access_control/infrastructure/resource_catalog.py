from uuid import UUID

import asyncio
import httpx

from younilab_seo.access_control.application import ResourceNotFound


class ResourceCatalogHttpGrantVerifier:
    """Verifies grant resource ids against the tenant-scoped catalog API."""

    def __init__(
        self,
        resource_catalog_url: str,
        transport: httpx.AsyncBaseTransport | None = None,
        max_concurrency: int = 8,
    ) -> None:
        self._resource_catalog_url = resource_catalog_url.rstrip("/")
        self._transport = transport
        self._max_concurrency = max(1, max_concurrency)

    async def require_customers_in_tenant(
        self,
        tenant_id: UUID,
        customer_ids: set[UUID],
        access_token: str | None = None,
    ) -> None:
        if not customer_ids:
            return
        await self._require_resources(
            resource_path="customers",
            resource_ids=customer_ids,
            tenant_id=tenant_id,
            access_token=access_token,
        )

    async def require_tasks_in_tenant(
        self,
        tenant_id: UUID,
        task_ids: set[UUID],
        access_token: str | None = None,
    ) -> None:
        if not task_ids:
            return
        await self._require_resources(
            resource_path="tasks",
            resource_ids=task_ids,
            tenant_id=tenant_id,
            access_token=access_token,
        )

    async def _require_resources(
        self,
        *,
        resource_path: str,
        resource_ids: set[UUID],
        tenant_id: UUID,
        access_token: str | None,
    ) -> None:
        if access_token is None:
            raise ResourceNotFound
        try:
            async with httpx.AsyncClient(
                timeout=5,
                transport=self._transport,
            ) as client:
                semaphore = asyncio.Semaphore(self._max_concurrency)
                await asyncio.gather(
                    *(
                        self._require_resource(
                            client=client,
                            semaphore=semaphore,
                            resource_path=resource_path,
                            resource_id=resource_id,
                            tenant_id=tenant_id,
                            access_token=access_token,
                        )
                        for resource_id in resource_ids
                    )
                )
        except httpx.HTTPError as exc:
            raise ResourceNotFound from exc

    async def _require_resource(
        self,
        *,
        client: httpx.AsyncClient,
        semaphore: asyncio.Semaphore,
        resource_path: str,
        resource_id: UUID,
        tenant_id: UUID,
        access_token: str,
    ) -> None:
        async with semaphore:
            response = await client.get(
                f"{self._resource_catalog_url}/api/{resource_path}/{resource_id}",
                headers={"Authorization": f"Bearer {access_token}"},
            )
        if response.status_code != 200:
            raise ResourceNotFound
        if response.json().get("tenantId") != str(tenant_id):
            raise ResourceNotFound
