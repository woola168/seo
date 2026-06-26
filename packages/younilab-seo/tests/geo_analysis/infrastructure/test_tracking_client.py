import asyncio
import json
from datetime import UTC, datetime
from uuid import uuid4

import httpx

from younilab_seo.geo_analysis.application import QueryRunJobMessage
from younilab_seo.geo_analysis.infrastructure.tracking import HttpTrackingRunClient


def test_tracking_client_posts_run_request_payload() -> None:
    async def run() -> None:
        captured: dict = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["path"] = request.url.path
            captured["payload"] = json.loads(request.content.decode("utf-8"))
            return httpx.Response(
                200,
                json={
                    "id": "tracking-run-1",
                    "seoTaskId": str(_SEO_TASK_ID),
                    "timing": "run_now",
                    "results": [_result_payload(status="completed")],
                },
            )

        client = HttpTrackingRunClient("https://tracking.test")
        client._client = httpx.AsyncClient(
            base_url="https://tracking.test",
            transport=httpx.MockTransport(handler),
        )

        built_payload = client.build_request_payload(_message())
        result = await client.run(_message())

        assert captured["path"] == "/api/v1/geo-tracking/run-requests"
        payload = captured["payload"]
        assert payload == built_payload
        assert payload["seoTaskId"] == str(_SEO_TASK_ID)
        assert payload["provider"] == "gemini"
        assert payload["timing"] == "run_now"
        assert payload["queries"][0]["topicName"] == "Supplier evaluation"
        assert payload["queries"][0]["marketType"] == "b2b_procurement"
        assert payload["queries"][0]["isBranded"] is True
        assert payload["queries"][0]["metadata"]["geoJobId"] == str(_JOB_ID)
        assert payload["queries"][0]["metadata"]["model"] == "gemini-2.5-flash"
        assert result.id == "tracking-run-1"
        assert result.results[0].raw_response == "Raw answer"
        assert result.results[0].references[0].url == "https://example.com/reference"

        await client.close()

    asyncio.run(run())


def test_tracking_client_maps_failed_result() -> None:
    async def run() -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json={
                    "id": "tracking-run-1",
                    "seoTaskId": str(_SEO_TASK_ID),
                    "timing": "run_now",
                    "results": [_result_payload(status="failed", error="timeout")],
                },
            )

        client = HttpTrackingRunClient("https://tracking.test")
        client._client = httpx.AsyncClient(
            base_url="https://tracking.test",
            transport=httpx.MockTransport(handler),
        )

        result = await client.run(_message())

        assert result.id == "tracking-run-1"
        assert result.results[0].status == "failed"
        assert result.results[0].error == "timeout"

        await client.close()

    asyncio.run(run())


_JOB_ID = uuid4()
_PROJECT_ID = uuid4()
_SEO_TASK_ID = uuid4()
_QUERY_ID = uuid4()


def _message() -> QueryRunJobMessage:
    return QueryRunJobMessage(
        job_id=_JOB_ID,
        project_id=_PROJECT_ID,
        seo_task_id=_SEO_TASK_ID,
        query_id=_QUERY_ID,
        query_text="Which suppliers are recommended?",
        topic_name="Supplier evaluation",
        platform="gemini",
        model="gemini-2.5-flash",
        region="TW",
        language="zh-TW",
        market_type="b2b_procurement",
        is_branded=True,
        scheduled_for=datetime(2026, 6, 25, tzinfo=UTC),
        callback_url="https://example.test/callback",
    )


def _result_payload(*, status: str, error: str | None = None) -> dict:
    return {
        "id": "result-1",
        "runRequestId": "tracking-run-1",
        "queryId": str(_QUERY_ID),
        "provider": "gemini",
        "surface": "Gemini",
        "model": "gemini-2.5-flash",
        "region": "TW",
        "language": "zh-TW",
        "status": status,
        "rawResponse": "Raw answer",
        "referenceUrls": ["https://example.com/reference"],
        "references": [
            {
                "url": "https://example.com/reference",
                "title": "Example reference",
            }
        ],
        "error": error,
        "runAt": "2026-06-25T00:00:00Z",
    }
