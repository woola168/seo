import asyncio

from uuid import UUID

import httpx
import pytest

from younilab_seo.resource_catalog.application import AccessDenied
from younilab_seo.resource_catalog.infrastructure.authorization import (
    AccessControlAuthorizer,
)

TENANT_ID = "00000000-0000-4000-8000-000000000001"


def test_access_control_authorizer_allows_known_permission() -> None:
    requests: list[httpx.Request] = []
    principal_tenant_ids: list[UUID] = []

    async def scenario() -> None:
        async def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            return httpx.Response(
                200,
                json={
                    "permissions": ["customers.read"],
                    "tenantId": TENANT_ID,
                    "hasGlobalResourceAccess": False,
                    "customerIds": [],
                    "taskIds": [],
                },
            )

        authorizer = AccessControlAuthorizer(
            "https://access-control.test",
            transport=httpx.MockTransport(handler),
        )

        principal = await authorizer.require("token", "customers.read")
        principal_tenant_ids.append(principal.tenant_id)

    asyncio.run(scenario())

    assert [request.url.path for request in requests] == ["/api/me/capabilities"]
    assert requests[0].headers["authorization"] == "Bearer token"
    assert principal_tenant_ids == [UUID(TENANT_ID)]


def test_access_control_authorizer_denies_missing_permission() -> None:
    async def scenario() -> None:
        async def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json={
                    "permissions": ["tasks.read"],
                    "tenantId": TENANT_ID,
                    "hasGlobalResourceAccess": False,
                    "customerIds": [],
                    "taskIds": [],
                },
            )

        authorizer = AccessControlAuthorizer(
            "https://access-control.test",
            transport=httpx.MockTransport(handler),
        )

        with pytest.raises(AccessDenied):
            await authorizer.require("token", "customers.read")

    asyncio.run(scenario())


def test_access_control_authorizer_fails_closed_when_unavailable() -> None:
    async def scenario() -> None:
        async def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("unavailable", request=request)

        authorizer = AccessControlAuthorizer(
            "https://access-control.test",
            transport=httpx.MockTransport(handler),
        )

        with pytest.raises(AccessDenied):
            await authorizer.require("token", "customers.read")

    asyncio.run(scenario())
