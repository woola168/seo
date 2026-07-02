import asyncio
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

from younilab_seo.geo_analysis.application import (
    QueryRunJobMessage,
    QueryRunJobMessageRejected,
)
from younilab_seo.geo_analysis.infrastructure.messaging import RabbitMqQueryRunJobConsumer


def test_rabbitmq_consumer_drops_malformed_message() -> None:
    async def run() -> None:
        calls: list[QueryRunJobMessage] = []
        consumer = RabbitMqQueryRunJobConsumer(
            url="amqp://example",
            queue_name="geo.query-runs.gemini",
        )

        async def handler(message: QueryRunJobMessage) -> None:
            calls.append(message)

        await consumer._handle_body(b'{"jobId":"not-a-uuid"}', handler)

        assert calls == []

    asyncio.run(run())


def test_rabbitmq_consumer_reraises_handler_failure() -> None:
    async def run() -> None:
        consumer = RabbitMqQueryRunJobConsumer(
            url="amqp://example",
            queue_name="geo.query-runs.gemini",
        )

        async def handler(message: QueryRunJobMessage) -> None:
            raise RuntimeError("database unavailable")

        try:
            await consumer._handle_body(_message_body(), handler)
        except RuntimeError as exc:
            assert str(exc) == "database unavailable"
        else:
            raise AssertionError("expected handler failure to be re-raised")

    asyncio.run(run())


def test_rabbitmq_consumer_drops_non_retryable_handler_failure() -> None:
    async def run() -> None:
        calls: list[QueryRunJobMessage] = []
        consumer = RabbitMqQueryRunJobConsumer(
            url="amqp://example",
            queue_name="geo.query-runs.gemini",
        )

        async def handler(message: QueryRunJobMessage) -> None:
            calls.append(message)
            raise QueryRunJobMessageRejected("terminal job")

        await consumer._handle_body(_message_body(), handler)

        assert len(calls) == 1

    asyncio.run(run())


def test_rabbitmq_consumer_requeues_unhandled_processing_failure() -> None:
    async def run() -> None:
        incoming = FakeIncoming(_message_body())
        connection = FakeConnection(incoming)

        async def connect_robust(url: str):
            return connection

        fake_aio_pika.connect_robust = connect_robust
        consumer = RabbitMqQueryRunJobConsumer(
            url="amqp://example",
            queue_name="geo.query-runs.gemini",
        )

        async def handler(message: QueryRunJobMessage) -> None:
            raise RuntimeError("database unavailable")

        try:
            await consumer.run(handler)
        except RuntimeError:
            pass
        else:
            raise AssertionError("expected processing failure to leave consumer run")

        assert incoming.process_context.requeue is True

    asyncio.run(run())


class FakeIncoming:
    def __init__(self, body: bytes) -> None:
        self.body = body
        self.process_context = FakeProcessContext()

    def process(self, *, requeue: bool):
        self.process_context.requeue = requeue
        return self.process_context


class FakeProcessContext:
    def __init__(self) -> None:
        self.requeue: bool | None = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False


class FakeQueueIterator:
    def __init__(self, incoming: FakeIncoming) -> None:
        self.incoming = incoming
        self.consumed = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self.consumed:
            raise StopAsyncIteration
        self.consumed = True
        return self.incoming


class FakeQueue:
    def __init__(self, incoming: FakeIncoming) -> None:
        self.incoming = incoming

    def iterator(self):
        return FakeQueueIterator(self.incoming)


class FakeChannel:
    def __init__(self, incoming: FakeIncoming) -> None:
        self.incoming = incoming
        self.prefetch_count: int | None = None

    async def set_qos(self, *, prefetch_count: int) -> None:
        self.prefetch_count = prefetch_count

    async def declare_queue(self, queue_name: str, *, durable: bool):
        return FakeQueue(self.incoming)


class FakeConnection:
    def __init__(self, incoming: FakeIncoming) -> None:
        self.incoming = incoming

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False

    async def channel(self):
        return FakeChannel(self.incoming)


def _message_body() -> bytes:
    message = QueryRunJobMessage(
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
    return message.model_dump_json(by_alias=True).encode("utf-8")
