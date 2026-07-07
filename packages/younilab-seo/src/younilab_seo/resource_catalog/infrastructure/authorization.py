from uuid import UUID

import httpx

from younilab_seo.resource_catalog.application import (
    AccessDenied,
    AuthenticationRequired,
    AuthorizedPrincipal,
)


class AccessControlAuthorizer:
    """Delegates permission and tenant context lookup to Access Control."""

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
        try:
            async with httpx.AsyncClient(
                timeout=5,
                transport=self._transport,
            ) as client:
                headers = {"Authorization": f"Bearer {access_token}"}
                response = await client.get(
                    f"{self._access_control_url}/api/me/capabilities",
                    headers=headers,
                )
        except httpx.HTTPError as exc:
            raise AccessDenied("authorization service unavailable") from exc
        if response.status_code == 401:
            raise AuthenticationRequired
        if response.status_code != 200:
            raise AccessDenied
        body = response.json()
        if permission not in body.get("permissions", []):
            raise AccessDenied
        tenant_id = body.get("tenantId")
        if tenant_id is None:
            raise AccessDenied("authorization response missing tenantId")
        return AuthorizedPrincipal(
            tenant_id=UUID(tenant_id),
            permissions=frozenset(body.get("permissions", [])),
            has_global_resource_access=bool(
                body.get("hasGlobalResourceAccess", False)
            ),
            customer_ids=frozenset(UUID(value) for value in body.get("customerIds", [])),
            task_ids=frozenset(UUID(value) for value in body.get("taskIds", [])),
        )


class AllowAllAuthorizer:
    """Development authorizer that returns a fixed tenant context."""

    def __init__(
        self,
        tenant_id: UUID = UUID("00000000-0000-4000-8000-000000000001"),
    ) -> None:
        self._tenant_id = tenant_id

    async def require(
        self,
        access_token: str,
        permission: str,
    ) -> AuthorizedPrincipal:
        return AuthorizedPrincipal(
            tenant_id=self._tenant_id,
            permissions=frozenset({permission}),
            has_global_resource_access=True,
            customer_ids=frozenset(),
            task_ids=frozenset(),
        )
