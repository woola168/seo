import asyncio
import json
import logging
from uuid import uuid4

import httpx
import pytest

from younilab_seo.geo_analysis.application import (
    KMindHubExtractionUnavailable,
    KMindHubWorkspaceProvisionUnavailable,
)
from younilab_seo.geo_analysis.application.kmindhub_extraction_schema import (
    geo_answer_analysis_task_definition,
)
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


def test_kmindhub_client_runs_extraction_preview_and_commit() -> None:
    async def run() -> None:
        workspace_id = uuid4()
        task_id = uuid4()
        captured: list[tuple[str, str]] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append((request.method, request.url.path))
            assert request.headers["X-Workspace-Id"] == str(workspace_id)
            if request.url.path == "/extraction-tasks":
                payload = json.loads(request.content.decode("utf-8"))
                assert payload["fields"][0]["name"] == "summary"
                return httpx.Response(200, json={"taskId": str(task_id)})
            if request.url.path == "/extractions":
                body = request.content.decode("utf-8")
                assert str(task_id) in body
                assert "text=Acme+is+good" in body
                return httpx.Response(
                    200,
                    json={
                        "taskId": str(task_id),
                        "items": [
                            {
                                "fields": {"summary": {"value": "Acme is good"}},
                                "verification": {"passed": True},
                            }
                        ],
                    },
                )
            if request.url.path == "/extractions/commit":
                payload = json.loads(request.content.decode("utf-8"))
                assert payload["taskId"] == str(task_id)
                return httpx.Response(
                    200,
                    json={"commitBatchId": "batch-1", "itemIds": ["item-1"]},
                )
            return httpx.Response(404)

        client = HttpKMindHubWorkspaceClient("https://kmindhub.test")
        client._client = httpx.AsyncClient(
            base_url="https://kmindhub.test",
            transport=httpx.MockTransport(handler),
        )

        created_task_id = await client.create_extraction_task(
            workspace_id=workspace_id,
            definition=geo_answer_analysis_task_definition(),
        )
        preview = await client.preview_text_extraction(
            workspace_id=workspace_id,
            task_id=created_task_id,
            text="Acme is good",
        )
        commit = await client.commit_extraction_items(
            workspace_id=workspace_id,
            task_id=created_task_id,
            items=[{"itemId": None, "fields": {"summary": {"value": "Acme is good"}}}],
        )

        assert preview.items[0].fields["summary"].value == "Acme is good"
        assert preview.request_payload == {
            "taskId": str(created_task_id),
            "text": "Acme is good",
        }
        assert preview.response_payload == {
            "taskId": str(created_task_id),
            "items": [
                {
                    "fields": {"summary": {"value": "Acme is good"}},
                    "verification": {"passed": True},
                }
            ],
        }
        assert commit.commit_batch_id == "batch-1"
        assert captured == [
            ("POST", "/extraction-tasks"),
            ("POST", "/extractions"),
            ("POST", "/extractions/commit"),
        ]

        await client.close()

    asyncio.run(run())


def test_kmindhub_client_retries_transient_preview_http_error() -> None:
    async def run() -> None:
        workspace_id = uuid4()
        task_id = uuid4()
        attempts = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal attempts
            if request.url.path == "/extractions":
                attempts += 1
                if attempts == 1:
                    return httpx.Response(502, json={"detail": "bad gateway"})
                return httpx.Response(
                    200,
                    json={
                        "taskId": str(task_id),
                        "items": [
                            {
                                "fields": {"summary": {"value": "Acme is good"}},
                                "verification": {"passed": True},
                            }
                        ],
                    },
                )
            return httpx.Response(404)

        client = HttpKMindHubWorkspaceClient(
            "https://kmindhub.test",
            preview_retry_delay_seconds=0,
        )
        client._client = httpx.AsyncClient(
            base_url="https://kmindhub.test",
            transport=httpx.MockTransport(handler),
        )

        preview = await client.preview_text_extraction(
            workspace_id=workspace_id,
            task_id=task_id,
            text="Acme is good",
        )

        assert attempts == 2
        assert preview.items[0].fields["summary"].value == "Acme is good"

        await client.close()

    asyncio.run(run())


def test_kmindhub_client_logs_full_preview_payloads_when_debug_enabled(caplog) -> None:
    async def run() -> None:
        workspace_id = uuid4()
        task_id = uuid4()

        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/extractions":
                return httpx.Response(
                    200,
                    json={
                        "taskId": str(task_id),
                        "items": [
                            {
                                "fields": {"summary": {"value": "Acme is good"}},
                                "verification": {"passed": True},
                            }
                        ],
                    },
                )
            return httpx.Response(404)

        client = HttpKMindHubWorkspaceClient(
            "https://kmindhub.test",
            debug_payloads=True,
        )
        client._client = httpx.AsyncClient(
            base_url="https://kmindhub.test",
            transport=httpx.MockTransport(handler),
        )

        with caplog.at_level(logging.INFO):
            await client.preview_text_extraction(
                workspace_id=workspace_id,
                task_id=task_id,
                text="Acme is good",
            )

        request_record = next(
            record
            for record in caplog.records
            if record.message.startswith(
                "KMindHub extraction preview request payload: "
            )
        )
        response_record = next(
            record
            for record in caplog.records
            if record.message.startswith(
                "KMindHub extraction preview response payload: "
            )
        )

        assert request_record.kmindhub_request_data == {
            "taskId": str(task_id),
            "text": "Acme is good",
        }
        assert '"requestData":' in request_record.message
        assert '"text": "Acme is good"' in request_record.message
        assert '"summary"' in response_record.kmindhub_response_body
        assert "Acme is good" in response_record.kmindhub_response_body
        assert '"responseBody":' in response_record.message
        assert "Acme is good" in response_record.message

        await client.close()

    asyncio.run(run())


def test_kmindhub_client_logs_full_preview_http_error_payload_when_debug_enabled(caplog) -> None:
    async def run() -> None:
        workspace_id = uuid4()
        task_id = uuid4()

        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/extractions":
                return httpx.Response(
                    502,
                    json={"detail": "preview upstream failed"},
                )
            return httpx.Response(404)

        client = HttpKMindHubWorkspaceClient(
            "https://kmindhub.test",
            debug_payloads=True,
            preview_retry_attempts=0,
        )
        client._client = httpx.AsyncClient(
            base_url="https://kmindhub.test",
            transport=httpx.MockTransport(handler),
        )

        with caplog.at_level(logging.INFO):
            with pytest.raises(KMindHubExtractionUnavailable):
                await client.preview_text_extraction(
                    workspace_id=workspace_id,
                    task_id=task_id,
                    text="Acme is good",
                )

        response_record = next(
            record
            for record in caplog.records
            if record.message.startswith(
                "KMindHub extraction preview response payload: "
            )
        )

        assert response_record.status_code == 502
        assert "preview upstream failed" in response_record.kmindhub_response_body
        assert '"statusCode": 502' in response_record.message
        assert "preview upstream failed" in response_record.message
        failure_record = next(
            record
            for record in caplog.records
            if record.message.startswith("KMindHub extraction preview failed: ")
        )
        assert '"statusCode": 502' in failure_record.message
        assert "preview upstream failed" in failure_record.message

        await client.close()

    asyncio.run(run())


def test_kmindhub_client_does_not_retry_non_transient_preview_http_error() -> None:
    async def run() -> None:
        workspace_id = uuid4()
        task_id = uuid4()
        attempts = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal attempts
            if request.url.path == "/extractions":
                attempts += 1
                return httpx.Response(400, json={"detail": "bad request"})
            return httpx.Response(404)

        client = HttpKMindHubWorkspaceClient(
            "https://kmindhub.test",
            preview_retry_delay_seconds=0,
        )
        client._client = httpx.AsyncClient(
            base_url="https://kmindhub.test",
            transport=httpx.MockTransport(handler),
        )

        with pytest.raises(KMindHubExtractionUnavailable, match="HTTPStatusError"):
            await client.preview_text_extraction(
                workspace_id=workspace_id,
                task_id=task_id,
                text="Acme is good",
            )

        assert attempts == 1

        await client.close()

    asyncio.run(run())


def test_kmindhub_client_does_not_retry_preview_parsing_error() -> None:
    async def run() -> None:
        workspace_id = uuid4()
        task_id = uuid4()
        attempts = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal attempts
            if request.url.path == "/extractions":
                attempts += 1
                return httpx.Response(200, content=b"not-json")
            return httpx.Response(404)

        client = HttpKMindHubWorkspaceClient(
            "https://kmindhub.test",
            preview_retry_delay_seconds=0,
        )
        client._client = httpx.AsyncClient(
            base_url="https://kmindhub.test",
            transport=httpx.MockTransport(handler),
        )

        with pytest.raises(KMindHubExtractionUnavailable, match="JSONDecodeError"):
            await client.preview_text_extraction(
                workspace_id=workspace_id,
                task_id=task_id,
                text="Acme is good",
            )

        assert attempts == 1

        await client.close()

    asyncio.run(run())


def test_kmindhub_client_parses_reference_commit_response_shape() -> None:
    async def run() -> None:
        workspace_id = uuid4()
        task_id = uuid4()
        item_id = uuid4()

        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/extractions/commit":
                return httpx.Response(
                    200,
                    json={
                        "commitBatchId": str(uuid4()),
                        "tenantId": str(workspace_id),
                        "items": [{"itemId": str(item_id), "fields": {}}],
                    },
                )
            return httpx.Response(404)

        client = HttpKMindHubWorkspaceClient("https://kmindhub.test")
        client._client = httpx.AsyncClient(
            base_url="https://kmindhub.test",
            transport=httpx.MockTransport(handler),
        )

        commit = await client.commit_extraction_items(
            workspace_id=workspace_id,
            task_id=task_id,
            items=[{"itemId": None, "fields": {"summary": {"value": "Acme"}}}],
        )

        assert commit.commit_batch_id is not None
        assert commit.item_ids == [str(item_id)]

        await client.close()

    asyncio.run(run())


def test_kmindhub_client_accepts_commit_items_without_top_level_batch_id() -> None:
    async def run() -> None:
        workspace_id = uuid4()
        task_id = uuid4()
        item_id = uuid4()

        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/extractions/commit":
                return httpx.Response(200, json={"items": [{"itemId": str(item_id)}]})
            return httpx.Response(404)

        client = HttpKMindHubWorkspaceClient("https://kmindhub.test")
        client._client = httpx.AsyncClient(
            base_url="https://kmindhub.test",
            transport=httpx.MockTransport(handler),
        )

        commit = await client.commit_extraction_items(
            workspace_id=workspace_id,
            task_id=task_id,
            items=[{"itemId": None, "fields": {"summary": {"value": "Acme"}}}],
        )

        assert commit.commit_batch_id is None
        assert commit.item_ids == [str(item_id)]

        await client.close()

    asyncio.run(run())


def test_kmindhub_client_reports_commit_parsing_error_class() -> None:
    async def run() -> None:
        workspace_id = uuid4()
        task_id = uuid4()

        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/extractions/commit":
                return httpx.Response(200, content=b"not-json")
            return httpx.Response(404)

        client = HttpKMindHubWorkspaceClient("https://kmindhub.test")
        client._client = httpx.AsyncClient(
            base_url="https://kmindhub.test",
            transport=httpx.MockTransport(handler),
        )

        with pytest.raises(KMindHubExtractionUnavailable, match="JSONDecodeError"):
            await client.commit_extraction_items(
                workspace_id=workspace_id,
                task_id=task_id,
                items=[{"itemId": None, "fields": {"summary": {"value": "Acme"}}}],
            )

        await client.close()

    asyncio.run(run())


def test_kmindhub_client_reports_commit_http_error_class() -> None:
    async def run() -> None:
        workspace_id = uuid4()
        task_id = uuid4()

        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/extractions/commit":
                return httpx.Response(503, json={"detail": "unavailable"})
            return httpx.Response(404)

        client = HttpKMindHubWorkspaceClient("https://kmindhub.test")
        client._client = httpx.AsyncClient(
            base_url="https://kmindhub.test",
            transport=httpx.MockTransport(handler),
        )

        with pytest.raises(KMindHubExtractionUnavailable, match="HTTPStatusError"):
            await client.commit_extraction_items(
                workspace_id=workspace_id,
                task_id=task_id,
                items=[{"itemId": None, "fields": {"summary": {"value": "Acme"}}}],
            )

        await client.close()

    asyncio.run(run())
