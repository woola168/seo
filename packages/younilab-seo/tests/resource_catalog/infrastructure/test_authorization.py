import asyncio

import httpx
import pytest

from younilab_seo.resource_catalog.application import AccessDenied
from younilab_seo.resource_catalog.infrastructure.authorization import (
    AccessControlAuthorizer,
)


def test_access_control_authorizer_allows_known_permission() -> None:
    requests: list[httpx.Request] = []

    async def scenario() -> None:
        async def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            return httpx.Response(
                200,
                json={
                    "permissions": ["customers.read"],
                    "hasGlobalResourceAccess": False,
                    "customerIds": [],
                    "taskIds": [],
                },
            )

        authorizer = AccessControlAuthorizer(
            "https://access-control.test",
            transport=httpx.MockTransport(handler),
        )

        await authorizer.require("token", "customers.read")

    asyncio.run(scenario())

    assert [request.url.path for request in requests] == ["/api/me/capabilities"]
    assert requests[0].headers["authorization"] == "Bearer token"


def test_access_control_authorizer_denies_missing_permission() -> None:
    async def scenario() -> None:
        async def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json={
                    "permissions": ["tasks.read"],
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
