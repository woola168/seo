# ruff: noqa: E402

import asyncio
import sys
import types
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4

fake_aio_pika = types.SimpleNamespace(
    DeliveryMode=types.SimpleNamespace(PERSISTENT=2),
    ExchangeType=types.SimpleNamespace(DIRECT="direct"),
    Message=lambda body, **kwargs: types.SimpleNamespace(body=body, **kwargs),
    connect_robust=None,
)
sys.modules["aio_pika"] = fake_aio_pika

from younilab_geo_analysis_worker.composition import (
    _build_tracking_client,
    build_dependencies,
)
from younilab_geo_analysis_worker.worker import GeoAnalysisWorker
from younilab_seo.geo_analysis.application import (
    AnalyzeRunResult,
    EvidenceTextRepairCommand,
    EvidenceTextRepairResult,
    NormalizeRunResultCitations,
    QueryRunJobMessage,
)
from younilab_seo.geo_analysis.infrastructure import KMindHubGeoRunResultAnalyzer
from younilab_seo.geo_analysis.infrastructure.citation_resolver import (
    HttpCitationUrlResolver,
)


@dataclass
class FakeConsumer:
    message: QueryRunJobMessage

    async def run(self, handler):
        await handler(self.message)


@dataclass
class FakeProcessor:
    messages: list[QueryRunJobMessage] = field(default_factory=list)

    async def execute(self, message: QueryRunJobMessage) -> None:
        self.messages.append(message)


@dataclass
class FakeEvidenceTextRepairer:
    close_calls: int = 0

    async def repair(
        self,
        command: EvidenceTextRepairCommand,
    ) -> EvidenceTextRepairResult:
        raise AssertionError("repair should not run during composition tests")

    async def close(self) -> None:
        self.close_calls += 1


def test_worker_passes_consumed_message_to_processor() -> None:
    async def run() -> None:
        message = _message()
        processor = FakeProcessor()

        await GeoAnalysisWorker(
            consumer=FakeConsumer(message),
            processor=processor,
        ).run()

        assert processor.messages == [message]

    asyncio.run(run())


def test_composition_builds_provider_queue_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("GEO_ANALYSIS_RABBITMQ_URL", "amqp://example")
    monkeypatch.setenv("GEO_ANALYSIS_DATABASE_URL", "postgresql+asyncpg://example")
    monkeypatch.delenv("GEO_ANALYSIS_WORKER_QUEUE", raising=False)

    repairer = FakeEvidenceTextRepairer()
    dependencies = build_dependencies(
        repository=object(),
        tracking_client=object(),
        evidence_text_repairer=repairer,
        provider="gemini",
    )

    assert dependencies.consumer.queue_name == "geo.query-runs.gemini"
    assert dependencies.processor.supported_provider == "gemini"
    assert isinstance(dependencies.analyze_run_result, AnalyzeRunResult)
    assert isinstance(
        dependencies.normalize_run_result_citations,
        NormalizeRunResultCitations,
    )
    assert isinstance(
        dependencies.analyze_run_result.analyzer,
        KMindHubGeoRunResultAnalyzer,
    )
    assert dependencies.analyze_run_result.analyzer.evidence_text_repairer is repairer
    assert dependencies.evidence_text_repairer is repairer
    assert dependencies.closeables.count(repairer) == 1
    assert isinstance(dependencies.citation_url_resolver, HttpCitationUrlResolver)
    assert (
        dependencies.normalize_run_result_citations.url_resolver
        is dependencies.citation_url_resolver
    )
    assert dependencies.processor.analyze_run_result is dependencies.analyze_run_result
    assert (
        dependencies.processor.normalize_run_result_citations
        is dependencies.normalize_run_result_citations
    )
    assert not hasattr(dependencies.processor, "analysis_extractor")
    workspace_id = uuid4()
    assert dependencies.kmindhub_workspace_client.workspace_headers(workspace_id) == {
        "X-Workspace-Id": str(workspace_id)
    }

    asyncio.run(dependencies.close())

    assert repairer.close_calls == 1


def test_worker_uses_fixed_tracking_run_timeout(monkeypatch) -> None:
    monkeypatch.setenv("GEO_TRACKING_BASE_URL", "http://tracking.example")
    monkeypatch.setenv("GEO_TRACKING_TIMEOUT_SECONDS", "1")

    client = _build_tracking_client()

    assert client.base_url == "http://tracking.example"
    assert client.timeout_seconds == 210.0


def test_composition_builds_google_aio_provider_queue(monkeypatch) -> None:
    monkeypatch.setenv("GEO_ANALYSIS_RABBITMQ_URL", "amqp://example")
    monkeypatch.setenv("GEO_ANALYSIS_DATABASE_URL", "postgresql+asyncpg://example")
    monkeypatch.delenv("GEO_ANALYSIS_WORKER_QUEUE", raising=False)

    dependencies = build_dependencies(
        repository=object(),
        tracking_client=object(),
        provider="google_aio",
    )

    assert dependencies.consumer.queue_name == "geo.query-runs.google_aio"
    assert dependencies.processor.supported_provider == "google_aio"


def _message() -> QueryRunJobMessage:
    return QueryRunJobMessage(
        job_id=uuid4(),
        tenant_id=uuid4(),
        project_id=uuid4(),
        seo_task_id=uuid4(),
        query_id=uuid4(),
        query_text="Which suppliers are recommended?",
        topic_name="Supplier evaluation",
        platform="gemini",
        model="gemini-2.5-flash",
        region="TW",
        language="zh-TW",
        market_type="b2b_procurement",
        is_branded=False,
        scheduled_for=datetime(2026, 6, 25, tzinfo=UTC),
        callback_url="https://example.test/callback",
    )
