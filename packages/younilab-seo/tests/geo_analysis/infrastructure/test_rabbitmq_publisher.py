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

from younilab_seo.geo_analysis.application import QueryRunJobMessage
from younilab_seo.geo_analysis.infrastructure.messaging import RabbitMqMessagePublisher


class FakeExchange:
    def __init__(self) -> None:
        self.published = []

    async def publish(self, message, routing_key: str) -> None:
        self.published.append((message, routing_key))


class FailingExchange:
    async def publish(self, message, routing_key: str) -> None:
        raise RuntimeError("channel closed")


class FakeQueue:
    def __init__(self) -> None:
        self.bindings = []

    async def bind(self, exchange, routing_key: str) -> None:
        self.bindings.append((exchange, routing_key))


class FakeChannel:
    def __init__(self, exchange=None) -> None:
        self.exchange = exchange or FakeExchange()
        self.queue = FakeQueue()
        self.declared_queue_name = ""

    async def declare_exchange(self, *args, **kwargs):
        return self.exchange

    async def declare_queue(self, name: str, **kwargs):
        self.declared_queue_name = name
        return self.queue


class FakeConnection:
    def __init__(self, channel=None) -> None:
        self.channel_instance = channel or FakeChannel()

    async def channel(self):
        return self.channel_instance


def test_rabbitmq_publisher_declares_provider_queue_and_publishes_json() -> None:
    async def run() -> None:
        connection = FakeConnection()

        async def connect(url: str):
            assert url == "amqp://example"
            return connection

        publisher = RabbitMqMessagePublisher(
            url="amqp://example",
            connection_factory=connect,
        )
        result = await publisher.publish(_message(platform="Gemini Chat"))

        assert result.status == "published"
        assert result.backend == "rabbitmq"
        assert result.destination == "geo.query-runs.gemini_chat"
        channel = connection.channel_instance
        assert channel.declared_queue_name == "geo.query-runs.gemini_chat"
        assert channel.queue.bindings[0][1] == "geo.query-runs.gemini_chat"
        published_message, routing_key = channel.exchange.published[0]
        assert routing_key == "geo.query-runs.gemini_chat"
        assert b'"platform":"Gemini Chat"' in published_message.body
        assert b'"marketType":"b2b_procurement"' in published_message.body
        assert published_message.content_type == "application/json"

    asyncio.run(run())


def test_rabbitmq_publisher_returns_failed_result_when_publish_fails() -> None:
    async def run() -> None:
        async def connect(url: str):
            raise RuntimeError("broker unavailable")

        publisher = RabbitMqMessagePublisher(
            url="amqp://example",
            connection_factory=connect,
        )
        result = await publisher.publish(_message(platform="openai"))

        assert result.status == "failed"
        assert result.destination == "geo.query-runs.openai"
        assert result.error_message == "broker unavailable"

    asyncio.run(run())


def test_rabbitmq_publisher_routes_google_aio_to_provider_queue() -> None:
    async def run() -> None:
        connection = FakeConnection()

        async def connect(url: str):
            return connection

        publisher = RabbitMqMessagePublisher(
            url="amqp://example",
            connection_factory=connect,
        )
        result = await publisher.publish(_message(platform="google_aio"))

        assert result.status == "published"
        assert result.destination == "geo.query-runs.google_aio"
        channel = connection.channel_instance
        assert channel.declared_queue_name == "geo.query-runs.google_aio"
        assert channel.queue.bindings[0][1] == "geo.query-runs.google_aio"
        _, routing_key = channel.exchange.published[0]
        assert routing_key == "geo.query-runs.google_aio"

    asyncio.run(run())


def test_rabbitmq_publisher_resets_cached_connection_after_publish_error() -> None:
    async def run() -> None:
        bad_connection = FakeConnection(FakeChannel(FailingExchange()))
        good_connection = FakeConnection()
        connections = [bad_connection, good_connection]

        async def connect(url: str):
            return connections.pop(0)

        publisher = RabbitMqMessagePublisher(
            url="amqp://example",
            connection_factory=connect,
        )

        failed = await publisher.publish(_message(platform="openai"))
        published = await publisher.publish(_message(platform="openai"))

        assert failed.status == "failed"
        assert failed.error_message == "channel closed"
        assert published.status == "published"
        assert good_connection.channel_instance.exchange.published

    asyncio.run(run())


def _message(platform: str) -> QueryRunJobMessage:
    return QueryRunJobMessage(
        job_id=uuid4(),
        project_id=uuid4(),
        seo_task_id=uuid4(),
        query_id=uuid4(),
        query_text="Which supplier should I choose?",
        topic_name="Supplier evaluation",
        platform=platform,
        region="TW",
        language="zh-TW",
        market_type="b2b_procurement",
        is_branded=False,
        scheduled_for=datetime(2026, 6, 25, tzinfo=UTC),
        callback_url="http://geo-analysis-api:8002/api/geo/jobs/callback",
    )
