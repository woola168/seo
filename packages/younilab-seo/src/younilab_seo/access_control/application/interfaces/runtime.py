from datetime import datetime
from typing import Protocol
from uuid import UUID


class Clock(Protocol):
    """提供 use case orchestration 可控的 application clock。"""

    def now(self) -> datetime: ...


class IdGenerator(Protocol):
    """為 application 擁有的 records 建立穩定識別碼。"""

    def new_id(self) -> UUID: ...


class NotificationPublisher(Protocol):
    """持久化或發送 use cases 產生的 notification requests。"""

    async def publish(self, notification) -> None:
        """發布 notification request，但不暴露實際 delivery 細節。"""
        ...
