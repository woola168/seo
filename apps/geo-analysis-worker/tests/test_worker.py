import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime
import sys
import types
from uuid import uuid4

fake_aio_pika = types.SimpleNamespace(
    DeliveryMode=types.SimpleNamespace(PERSISTENT=2),
    ExchangeType=types.SimpleNamespace(DIRECT="direct"),
    Message=lambda body, **kwargs: types.SimpleNamespace(body=body, **kwargs),
    connect_robust=None,
)
sys.modules["aio_pika"] = fake_aio_pika

from younilab_geo_analysis_worker.composition import build_dependencies
from younilab_geo_analysis_worker.worker import GeoAnalysisWorker
from younilab_seo.geo_analysis.application import QueryRunJobMessage


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

    dependencies = build_dependencies(
        repository=object(),
        tracking_client=object(),
        provider="gemini",
    )

    assert dependencies.consumer.queue_name == "geo.query-runs.gemini"
    assert dependencies.processor.supported_provider == "gemini"


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
