import asyncio
import json
from uuid import uuid4

import httpx
import pytest

from younilab_seo.geo_analysis.application import KMindHubWorkspaceProvisionUnavailable
from younilab_seo.geo_analysis.infrastructure import HttpKMindHubWorkspaceClient


def test_kmindhub_client_creates_workspace_and_builds_runtime_header() -> None:
    async def run() -> None:
        workspace_id = uuid4()
        captured: dict = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["path"] = request.url.path
            captured["payload"] = json.loads(request.content.decode("utf-8"))
            return httpx.Response(200, json={"workspaceId": str(workspace_id)})

        client = HttpKMindHubWorkspaceClient("https://kmindhub.test")
        client._client = httpx.AsyncClient(
            base_url="https://kmindhub.test",
            transport=httpx.MockTransport(handler),
        )

        result = await client.create_workspace("Acme Workspace")

        assert result == workspace_id
        assert captured == {
            "path": "/workspaces",
            "payload": {"displayName": "Acme Workspace"},
        }
        assert client.workspace_headers(workspace_id) == {
            "X-Workspace-Id": str(workspace_id)
        }

        await client.close()

    asyncio.run(run())


def test_kmindhub_client_maps_http_error_to_application_error() -> None:
    async def run() -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(503, json={"detail": "unavailable"})

        client = HttpKMindHubWorkspaceClient("https://kmindhub.test")
        client._client = httpx.AsyncClient(
            base_url="https://kmindhub.test",
            transport=httpx.MockTransport(handler),
        )

        with pytest.raises(KMindHubWorkspaceProvisionUnavailable):
            await client.create_workspace("Acme Workspace")

        await client.close()

    asyncio.run(run())
