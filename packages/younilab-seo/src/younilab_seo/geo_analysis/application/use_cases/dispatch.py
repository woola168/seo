from dataclasses import dataclass
from datetime import timedelta
from uuid import UUID

from younilab_seo.geo_analysis.application.contracts import (
    ExternalRunCallback,
    PublishResult,
    QueryRunJobMessage,
)
from younilab_seo.geo_analysis.application.interfaces import (
    Clock,
    GeoQueryRunJobRepository,
    MessagePublisher,
)
from younilab_seo.geo_analysis.domain import GeoQueryRunJob


@dataclass(frozen=True)
class DispatchQueryRunJob:
    """派送 pending GEO job，並透過 repository 保存派送 evidence。"""

    repository: GeoQueryRunJobRepository
    publisher: MessagePublisher
    clock: Clock
    retry_delay: timedelta = timedelta(minutes=5)

    async def execute(self, job_id: UUID, callback_base_url: str) -> GeoQueryRunJob:
        now = self.clock.now()
        job = await self.repository.get(job_id)
        context = await self.repository.get_job_dispatch_context(job_id)
        if context is None:
            raise KeyError(job_id)
        message = QueryRunJobMessage(
            job_id=context.job_id,
            project_id=context.project_id,
            query_id=context.query_id,
            query_text=context.query_text,
            platform=context.platform,
            model=context.model,
            region=context.region,
            language=context.language,
            scheduled_for=context.scheduled_for,
            callback_url=_callback_url(callback_base_url, job_id),
        )
        job.mark_publishing(now)
        await self.repository.save(job)

        try:
            result = await self.publisher.publish(message)
        except Exception as exc:
            result = PublishResult(
                backend="unknown",
                destination="",
                status="failed",
                error_message=str(exc),
            )
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
        return job


@dataclass(frozen=True)
class ReceiveExternalRunCallback:
    """接收外部 runner callback，並將 job 狀態與 callback evidence 一起保存。"""

    repository: GeoQueryRunJobRepository
    clock: Clock

    async def execute(self, callback: ExternalRunCallback) -> GeoQueryRunJob:
        return await self.repository.apply_external_callback(
            callback=callback,
            occurred_at=self.clock.now(),
        )


def _callback_url(callback_base_url: str, job_id: UUID) -> str:
    return f"{callback_base_url.rstrip('/')}/api/geo/jobs/{job_id}/external-callbacks"
