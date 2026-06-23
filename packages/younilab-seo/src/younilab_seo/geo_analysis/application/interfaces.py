from datetime import datetime
from typing import Protocol
from uuid import UUID

from younilab_seo.geo_analysis.application.contracts import (
    ExternalRunCallback,
    PublishResult,
    QueryRunJobMessage,
)
from younilab_seo.geo_analysis.domain import GeoQueryRunJob


class Clock(Protocol):
    """提供 use case 需要的時間，讓生命週期變更可被測試。"""

    def now(self) -> datetime:
        raise NotImplementedError


class IdGenerator(Protocol):
    """為此 bounded context 擁有的 orchestration record 建立識別碼。"""

    def new_id(self) -> UUID:
        raise NotImplementedError


class MessagePublisher(Protocol):
    """透過已設定的 message broker 發布 GEO query run job。"""

    async def publish(self, message: QueryRunJobMessage) -> PublishResult:
        raise NotImplementedError


class GeoQueryRunJobRepository(Protocol):
    """保存 query run job 狀態與派送證據。"""

    async def get(self, job_id: UUID) -> GeoQueryRunJob:
        raise NotImplementedError

    async def save(self, job: GeoQueryRunJob) -> None:
        raise NotImplementedError

    async def record_dispatch(
        self,
        *,
        job_id: UUID,
        result: PublishResult,
        payload: QueryRunJobMessage,
        occurred_at: datetime,
    ) -> None:
        raise NotImplementedError

    async def record_external_callback(
        self,
        *,
        callback: ExternalRunCallback,
        occurred_at: datetime,
    ) -> None:
        raise NotImplementedError
