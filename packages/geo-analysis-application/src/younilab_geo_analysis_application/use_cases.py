from dataclasses import dataclass
from datetime import timedelta
from uuid import UUID

from younilab_geo_analysis_application.contracts import (
    ExternalRunCallback,
    QueryRunJobMessage,
)
from younilab_geo_analysis_application.interfaces import (
    Clock,
    GeoQueryRunJobRepository,
    MessagePublisher,
)


@dataclass(frozen=True)
class DispatchQueryRunJob:
    """發布 pending GEO job，並將 broker 細節隔離在 port 後方。"""

    repository: GeoQueryRunJobRepository
    publisher: MessagePublisher
    clock: Clock
    retry_delay: timedelta = timedelta(minutes=5)

    async def execute(self, job_id: UUID, message: QueryRunJobMessage) -> None:
        now = self.clock.now()
        job = await self.repository.get(job_id)
        job.mark_publishing(now)
        await self.repository.save(job)

        result = await self.publisher.publish(message)
        now = self.clock.now()
        if result.status == "published":
            job.mark_published(
                backend=result.backend,
                message_id=result.message_id,
                now=now,
            )
        else:
            job.mark_publish_failed(
                error_code="publish_failed",
                error_message=result.error_message or "message publish failed",
                next_retry_at=now + self.retry_delay,
                now=now,
            )
        await self.repository.save(job)
        await self.repository.record_dispatch(
            job_id=job_id,
            result=result,
            payload=message,
            occurred_at=now,
        )


@dataclass(frozen=True)
class ReceiveExternalRunCallback:
    """套用外部 runner 狀態，但不接收 AI result payload。"""

    repository: GeoQueryRunJobRepository
    clock: Clock

    async def execute(self, callback: ExternalRunCallback) -> None:
        now = self.clock.now()
        job = await self.repository.get(callback.job_id)
        job.mark_external_status(
            external_run_id=callback.external_run_id,
            external_status=callback.status,
            error_code=callback.error_code,
            error_message=callback.error_message,
            now=now,
        )
        await self.repository.save(job)
        await self.repository.record_external_callback(
            callback=callback,
            occurred_at=now,
        )
