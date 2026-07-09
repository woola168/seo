from dataclasses import dataclass, field
from typing import Any

import httpx

from younilab_seo.geo_analysis.application import (
    QueryGenerationCommand,
    QueryResearchCommand,
    QueryRunJobMessage,
    TrackingRunResponse,
)


@dataclass
class HttpTrackingRunClient:
    """Calls geo-tracking to run one dispatched query job."""

    base_url: str
    timeout_seconds: float = 60.0
    _client: httpx.AsyncClient | None = field(default=None, init=False, repr=False)

    def build_request_payload(self, message: QueryRunJobMessage) -> dict[str, Any]:
        return _run_request_payload(message)

    async def run(self, message: QueryRunJobMessage) -> TrackingRunResponse:
        response = await self._get_client().post(
            "/api/v1/geo-tracking/run-requests",
            json=self.build_request_payload(message),
        )
        response.raise_for_status()
        payload = response.json()
        return TrackingRunResponse.model_validate(payload)

    async def research(self, command: QueryResearchCommand) -> dict:
        response = await self._get_client().post(
            "/api/v1/geo-tracking/query-research",
            json=command.model_dump(mode="json", by_alias=True),
        )
        response.raise_for_status()
        return response.json()

    async def generate(self, command: QueryGenerationCommand) -> dict:
        response = await self._get_client().post(
            "/api/v1/geo-tracking/query-generation",
            json=command.model_dump(mode="json", by_alias=True),
        )
        response.raise_for_status()
        return response.json()

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url.rstrip("/"),
                timeout=self.timeout_seconds,
            )
        return self._client


def _run_request_payload(message: QueryRunJobMessage) -> dict[str, Any]:
    metadata = {"geoJobId": str(message.job_id)}
    if message.model:
        metadata["model"] = message.model
    payload: dict[str, Any] = {
        "provider": message.platform,
        "timing": "run_now",
        "queries": [
            {
                "id": str(message.query_id),
                "text": message.query_text,
                "topicName": message.topic_name,
                "region": message.region,
                "language": message.language,
                "marketType": message.market_type,
                "isBranded": message.is_branded,
                "metadata": metadata,
            }
        ],
    }
    if message.seo_task_id is not None:
        payload["seoTaskId"] = str(message.seo_task_id)
    return payload


def run_request_payload(message: QueryRunJobMessage) -> dict[str, Any]:
    return _run_request_payload(message)
