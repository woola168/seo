from uuid import UUID

import httpx

from younilab_seo.geo_analysis.application import (
    AuthenticationRequired,
    AuthorizedPrincipal,
    PermissionAuthorizer,
    ResourceCatalogReferenceVerifier,
    ResourceCatalogVerificationDenied,
    ResourceCatalogVerificationUnavailable,
    ResourceTaskReference,
)


class AccessControlAuthorizer:
    """透過 Access Control API 取得 GEO request 的權限與租戶上下文。"""

    def __init__(
        self,
        access_control_url: str,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._access_control_url = access_control_url.rstrip("/")
        self._transport = transport

    async def require(
        self,
        access_token: str,
        permission: str,
    ) -> AuthorizedPrincipal:
        """確認 token 具備指定權限，並回傳 application layer 使用的 principal。"""

        try:
            async with httpx.AsyncClient(timeout=5, transport=self._transport) as client:
                response = await client.get(
                    f"{self._access_control_url}/api/me/capabilities",
                    headers={"Authorization": f"Bearer {access_token}"},
                )
        except httpx.HTTPError as exc:
            raise PermissionError("authorization service unavailable") from exc
        if response.status_code == 401:
            raise AuthenticationRequired
        if response.status_code != 200:
            raise PermissionError("access denied")
        body = response.json()
        if permission not in body.get("permissions", []):
            raise PermissionError("access denied")
        tenant_id = body.get("tenantId")
        if tenant_id is None:
            raise PermissionError("authorization response missing tenantId")
        return AuthorizedPrincipal(
            tenant_id=UUID(tenant_id),
            permissions=frozenset(body.get("permissions", [])),
            has_global_resource_access=bool(
                body.get("hasGlobalResourceAccess", False)
            ),
            customer_ids=frozenset(UUID(value) for value in body.get("customerIds", [])),
            task_ids=frozenset(UUID(value) for value in body.get("taskIds", [])),
        )


class ResourceCatalogHttpReferenceVerifier(ResourceCatalogReferenceVerifier):
    """透過 Resource Catalog API 驗證 customer/task reference 可用性。"""

    def __init__(
        self,
        resource_catalog_url: str,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._resource_catalog_url = resource_catalog_url.rstrip("/")
        self._transport = transport

    async def customer_exists(
        self,
        *,
        access_token: str,
        customer_id: UUID,
    ) -> bool:
        """確認 customer reference 對目前 token 可見。"""

        body = await self._get(
            access_token,
            f"/api/customers/{customer_id}",
        )
        return body is not None

    async def get_task(
        self,
        *,
        access_token: str,
        task_id: UUID,
    ) -> ResourceTaskReference | None:
        """取得目前 token 可見的 task reference 與 customer 歸屬。"""

        body = await self._get(access_token, f"/api/tasks/{task_id}")
        if body is None:
            return None
        return ResourceTaskReference(
            id=UUID(body["id"]),
            customer_id=UUID(body["customerId"]),
        )

    async def list_customer_names(
        self,
        *,
        access_token: str,
        customer_ids: frozenset[UUID],
    ) -> dict[UUID, str]:
        if not customer_ids:
            return {}
        names: dict[UUID, str] = {}
        for status in ("active", "archived"):
            page = 1
            while customer_ids - names.keys():
                body = await self._get(
                    access_token,
                    f"/api/customers?status={status}&page={page}&pageSize=100",
                )
                if body is None:
                    break
                try:
                    for item in body.get("items", []):
                        customer_id = UUID(item["id"])
                        if customer_id in customer_ids:
                            names[customer_id] = str(item["name"])
                    total_pages = int(body.get("totalPages", page))
                except (KeyError, TypeError, ValueError) as exc:
                    raise ResourceCatalogVerificationUnavailable(
                        "resource catalog customer response is invalid"
                    ) from exc
                if page >= total_pages:
                    break
                page += 1
        return names

    async def _get(self, access_token: str, path: str) -> dict | None:
        """將 Resource Catalog HTTP 狀態轉成 application 可處理的驗證結果。"""

        try:
            async with httpx.AsyncClient(timeout=5, transport=self._transport) as client:
                response = await client.get(
                    f"{self._resource_catalog_url}{path}",
                    headers={"Authorization": f"Bearer {access_token}"},
                )
        except httpx.HTTPError as exc:
            raise ResourceCatalogVerificationUnavailable(
                "resource catalog unavailable"
            ) from exc
        if response.status_code == 404:
            return None
        if response.status_code == 401:
            raise AuthenticationRequired
        if response.status_code == 403:
            raise ResourceCatalogVerificationDenied(
                "resource catalog reference verification denied"
            )
        if response.status_code >= 500:
            raise ResourceCatalogVerificationUnavailable(
                "resource catalog unavailable"
            )
        if response.status_code != 200:
            raise ResourceCatalogVerificationUnavailable(
                "resource catalog reference verification failed"
            )
        try:
            body = response.json()
        except ValueError as exc:
            raise ResourceCatalogVerificationUnavailable(
                "resource catalog response is invalid"
            ) from exc
        if not isinstance(body, dict):
            raise ResourceCatalogVerificationUnavailable(
                "resource catalog response is invalid"
            )
        return body
