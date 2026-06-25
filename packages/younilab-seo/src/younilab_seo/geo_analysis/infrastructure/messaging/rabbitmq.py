from __future__ import annotations

import json
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from uuid import uuid4

import aio_pika

from younilab_seo.geo_analysis.application import PublishResult, QueryRunJobMessage

ConnectionFactory = Callable[[str], Awaitable]


@dataclass
class RabbitMqMessagePublisher:
    """Publishes query run jobs to durable RabbitMQ queues split by provider."""

    url: str
    exchange_name: str = "geo.query-runs"
    queue_prefix: str = "geo.query-runs"
    routing_key_prefix: str = "geo.query-runs"
    connection_factory: ConnectionFactory = aio_pika.connect_robust
    _connection: object | None = field(default=None, init=False, repr=False)
    _channel: object | None = field(default=None, init=False, repr=False)

    async def publish(self, message: QueryRunJobMessage) -> PublishResult:
        provider = _provider_key(message.platform)
        destination = f"{self.queue_prefix}.{provider}"
        routing_key = f"{self.routing_key_prefix}.{provider}"
        message_id = str(uuid4())
        try:
            channel = await self._get_channel()
            exchange = await channel.declare_exchange(
                self.exchange_name,
                aio_pika.ExchangeType.DIRECT,
                durable=True,
            )
            queue = await channel.declare_queue(destination, durable=True)
            await queue.bind(exchange, routing_key=routing_key)
            body = json.dumps(
                message.model_dump(mode="json", by_alias=True),
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode("utf-8")
            await exchange.publish(
                aio_pika.Message(
                    body,
                    content_type="application/json",
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                    message_id=message_id,
                ),
                routing_key=routing_key,
            )
        except Exception as exc:
            self._channel = None
            self._connection = None
            return PublishResult(
                backend="rabbitmq",
                destination=destination,
                status="failed",
                error_message=str(exc),
            )
        return PublishResult(
            backend="rabbitmq",
            destination=destination,
            message_id=message_id,
            status="published",
        )

    async def close(self) -> None:
        if self._connection is None:
            return
        close = getattr(self._connection, "close", None)
        if close is not None:
            await close()
        self._connection = None
        self._channel = None

    async def _get_channel(self):
        if self._connection is None:
            self._connection = await self.connection_factory(self.url)
        if self._channel is None:
            self._channel = await self._connection.channel()
        return self._channel


def _provider_key(platform: str) -> str:
    value = re.sub(r"[^a-z0-9_.-]+", "_", platform.strip().lower())
    return value.strip("_.-") or "unknown"
