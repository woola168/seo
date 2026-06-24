from dataclasses import dataclass
from datetime import timedelta
from uuid import UUID

from younilab_seo.geo_analysis.application.contracts import (
    ExternalRunCallback,
    QueryRunJobMessage,
)
from younilab_seo.geo_analysis.application.interfaces import (
    Clock,
    GeoQueryRunJobRepository,
    MessagePublisher,
)


@dataclass(frozen=True)
class DispatchQueryRunJob:
    """派送 pending GEO job，並透過 repository 保存派送 evidence。"""

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
    """接收外部 runner callback，並將 job 狀態與 callback evidence 一起保存。"""

    repository: GeoQueryRunJobRepository
    clock: Clock

    async def execute(self, callback: ExternalRunCallback) -> None:
        await self.repository.apply_external_callback(
            callback=callback,
            occurred_at=self.clock.now(),
        )
