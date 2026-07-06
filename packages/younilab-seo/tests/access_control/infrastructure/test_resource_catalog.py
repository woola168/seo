import asyncio
from uuid import UUID

import httpx
import pytest

from younilab_seo.access_control.application import ResourceNotFound
from younilab_seo.access_control.infrastructure import ResourceCatalogHttpGrantVerifier


TENANT_ID = UUID("00000000-0000-4000-8000-000000000001")
CUSTOMER_A_ID = UUID("11111111-1111-4111-8111-111111111111")
CUSTOMER_B_ID = UUID("22222222-2222-4222-8222-222222222222")


def test_resource_catalog_verifier_checks_all_resources() -> None:
    requests: list[httpx.Request] = []

    async def scenario() -> None:
        async def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            return httpx.Response(200, json={"tenantId": str(TENANT_ID)})

        verifier = ResourceCatalogHttpGrantVerifier(
            "https://resource-catalog.test",
            transport=httpx.MockTransport(handler),
            max_concurrency=2,
        )

        await verifier.require_customers_in_tenant(
            TENANT_ID,
            {CUSTOMER_A_ID, CUSTOMER_B_ID},
            access_token="token",
        )

    asyncio.run(scenario())

    assert sorted(request.url.path for request in requests) == [
        f"/api/customers/{CUSTOMER_A_ID}",
        f"/api/customers/{CUSTOMER_B_ID}",
    ]
    assert {request.headers["authorization"] for request in requests} == {
        "Bearer token"
    }


def test_resource_catalog_verifier_fails_when_any_resource_is_invalid() -> None:
    async def scenario() -> None:
        async def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path.endswith(str(CUSTOMER_B_ID)):
                return httpx.Response(404)
            return httpx.Response(200, json={"tenantId": str(TENANT_ID)})

        verifier = ResourceCatalogHttpGrantVerifier(
            "https://resource-catalog.test",
            transport=httpx.MockTransport(handler),
            max_concurrency=2,
        )

        with pytest.raises(ResourceNotFound):
            await verifier.require_customers_in_tenant(
                TENANT_ID,
                {CUSTOMER_A_ID, CUSTOMER_B_ID},
                access_token="token",
            )

    asyncio.run(scenario())
