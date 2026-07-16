import json
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

import aio_pika
from pydantic import ValidationError

from younilab_seo.geo_analysis.application import (
    QueryRunJobMessage,
    QueryRunJobMessageRejected,
    QueryRunJobResultPersistenceFailed,
)

MessageHandler = Callable[[QueryRunJobMessage], Awaitable[None]]

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RabbitMqQueryRunJobConsumer:
    """從 durable RabbitMQ queue 消費指定 provider 的 query run jobs。"""

    url: str
    queue_name: str
    prefetch_count: int = 1
    max_delivery_attempts: int = 3

    async def run(self, handler: MessageHandler) -> None:
        connection = await aio_pika.connect_robust(self.url)
        async with connection:
            channel = await connection.channel()
            await channel.set_qos(prefetch_count=self.prefetch_count)
            queue = await channel.declare_queue(self.queue_name, durable=True)
            dead_letter_queue_name = f"{self.queue_name}.dlq"
            await channel.declare_queue(
                dead_letter_queue_name,
                durable=True,
            )
            async with queue.iterator() as queue_iter:
                async for incoming in queue_iter:
                    try:
                        await self._handle_body(incoming.body, handler)
                    except QueryRunJobResultPersistenceFailed:
                        logger.warning(
                            "acking GEO query run job after result persistence failure",
                        )
                        await incoming.ack()
                    except Exception:
                        await self._retry_or_dead_letter(
                            incoming,
                            channel,
                            dead_letter_queue_name,
                        )
                    else:
                        await incoming.ack()

    async def _retry_or_dead_letter(
        self,
        incoming,
        channel,
        dead_letter_queue_name: str,
    ) -> None:
        headers = dict(incoming.headers or {})
        attempt = int(headers.get("x-delivery-attempt", 1))
        destination = (
            dead_letter_queue_name
            if attempt >= self.max_delivery_attempts
            else self.queue_name
        )
        headers["x-delivery-attempt"] = attempt + 1
        try:
            await channel.default_exchange.publish(
                aio_pika.Message(
                    incoming.body,
                    headers=headers,
                    content_type=incoming.content_type or "application/json",
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                    message_id=incoming.message_id,
                ),
                routing_key=destination,
            )
        except Exception:
            await incoming.nack(requeue=True)
            raise
        await incoming.ack()

    async def _handle_body(self, body: bytes, handler: MessageHandler) -> None:
        try:
            payload = json.loads(body.decode("utf-8"))
            message = QueryRunJobMessage.model_validate(payload)
        except (UnicodeDecodeError, json.JSONDecodeError, ValidationError):
            logger.exception("dropping malformed GEO query run job message")
            return
        try:
            await handler(message)
        except QueryRunJobResultPersistenceFailed:
            raise
        except QueryRunJobMessageRejected:
            logger.warning(
                "dropping non-retryable GEO query run job message",
                exc_info=True,
            )
        except Exception:
            logger.exception("GEO query run worker failed after consuming message")
            raise
