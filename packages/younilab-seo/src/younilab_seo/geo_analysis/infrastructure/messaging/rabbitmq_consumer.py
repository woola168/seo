import json
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

import aio_pika
from pydantic import ValidationError

from younilab_seo.geo_analysis.application import (
    QueryRunJobMessage,
    QueryRunJobMessageRejected,
)

MessageHandler = Callable[[QueryRunJobMessage], Awaitable[None]]

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RabbitMqQueryRunJobConsumer:
    """Consumes provider-specific query run jobs from a durable RabbitMQ queue."""

    url: str
    queue_name: str
    prefetch_count: int = 1

    async def run(self, handler: MessageHandler) -> None:
        connection = await aio_pika.connect_robust(self.url)
        async with connection:
            channel = await connection.channel()
            await channel.set_qos(prefetch_count=self.prefetch_count)
            queue = await channel.declare_queue(self.queue_name, durable=True)
            async with queue.iterator() as queue_iter:
                async for incoming in queue_iter:
                    async with incoming.process(requeue=True):
                        await self._handle_body(incoming.body, handler)

    async def _handle_body(self, body: bytes, handler: MessageHandler) -> None:
        try:
            payload = json.loads(body.decode("utf-8"))
            message = QueryRunJobMessage.model_validate(payload)
        except (UnicodeDecodeError, json.JSONDecodeError, ValidationError):
            logger.exception("dropping malformed GEO query run job message")
            return
        try:
            await handler(message)
        except QueryRunJobMessageRejected:
            logger.warning(
                "dropping non-retryable GEO query run job message",
                exc_info=True,
            )
        except Exception:
            logger.exception("GEO query run worker failed after consuming message")
            raise
