import json

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from younilab_seo.access_control.application import Notification
from younilab_seo.access_control.infrastructure.persistence.postgres.models import (
    NotificationOutboxRow,
)


class MemoryNotificationPublisher:
    """將 notifications 存在 process 內的 NotificationPublisher adapter。"""

    def __init__(self) -> None:
        self.notifications: list[Notification] = []

    async def publish(self, notification: Notification) -> None:
        self.notifications.append(notification)


class PostgresOutboxPublisher:
    """將 notifications 記錄到 outbox 的 NotificationPublisher adapter。"""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._session_factory = session_factory

    async def publish(self, notification: Notification) -> None:
        payload = json.dumps(notification.parameters, ensure_ascii=False)
        async with self._session_factory() as session:
            session.add(
                NotificationOutboxRow(
                    id=notification.id,
                    recipient=notification.recipient,
                    template=notification.template,
                    payload_ciphertext=payload,
                    status="pending",
                    attempts=0,
                    created_at=notification.created_at,
                )
            )
            await session.commit()
