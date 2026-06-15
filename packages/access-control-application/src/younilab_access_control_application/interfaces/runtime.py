from datetime import datetime
from typing import Protocol
from uuid import UUID


class Clock(Protocol):
    def now(self) -> datetime: ...


class IdGenerator(Protocol):
    def new_id(self) -> UUID: ...


class NotificationPublisher(Protocol):
    async def publish(self, notification) -> None: ...
