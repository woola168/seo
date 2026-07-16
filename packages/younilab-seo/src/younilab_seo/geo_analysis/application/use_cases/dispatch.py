from dataclasses import dataclass
from datetime import timedelta
from uuid import UUID

from younilab_seo.geo_analysis.application.contracts import (
    ExternalRunCallback,
    PublishResult,
    QueryRunJobMessage,
)
from younilab_seo.geo_analysis.application.interfaces import (
    AuthorizedPrincipal,
    Clock,
    GeoQueryRunJobRepository,
    MessagePublisher,
)
from younilab_seo.geo_analysis.application.use_cases.access_policy import (
    can_access_project,
)
from younilab_seo.geo_analysis.domain import GeoQueryRunJob


class DispatchQueryRunJobError(ValueError):
    """已保存 job 無法產生有效 dispatch message 時拋出的錯誤。"""


@dataclass(frozen=True)
class DispatchQueryRunJob:
    """將 pending GEO job 發布到 provider queue，並記錄 dispatch evidence。"""

    repository: GeoQueryRunJobRepository
    publisher: MessagePublisher
    clock: Clock
    retry_delays: tuple[timedelta, ...] = (
        timedelta(minutes=5),
        timedelta(minutes=15),
    )

    async def execute(
        self,
        job_id: UUID,
        callback_base_url: str,
        principal: AuthorizedPrincipal | None = None,
    ) -> GeoQueryRunJob:
        now = self.clock.now()
        if principal is not None:
            project = await self.repository.get_job_project(
                principal.tenant_id,
                job_id,
            )
            if project is None or not can_access_project(principal, project):
                raise KeyError(job_id)
        context = await self.repository.get_job_dispatch_context(job_id)
        if context is None:
            raise KeyError(job_id)
        job = await self.repository.claim_job_for_publish(
            job_id=job_id,
            occurred_at=now,
        )
        if job is None:
            return await self.repository.get(job_id)
        message = QueryRunJobMessage(
            job_id=context.job_id,
            tenant_id=context.tenant_id,
            project_id=context.project_id,
            query_id=context.query_id,
            query_text=context.query_text,
            topic_name=context.topic_name,
            platform=context.platform,
            model=context.model,
            region=context.region,
            language=context.language,
            market_type=context.market_type,
            is_branded=context.is_branded,
            scheduled_for=context.scheduled_for,
            callback_url=_callback_url(callback_base_url, job_id),
        )
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
            retry_index = job.attempt_count - 1
            next_retry_at = (
                now + self.retry_delays[retry_index]
                if retry_index < len(self.retry_delays)
                else None
            )
            job.mark_publish_failed(
                error_code="publish_failed",
                error_message=result.error_message or "message publish failed",
                next_retry_at=next_retry_at,
                now=now,
            )
        persisted = await self.repository.record_dispatch(
            job_id=job_id,
            result=result,
            payload=message,
            occurred_at=now,
        )
        return persisted


@dataclass(frozen=True)
class ReceiveExternalRunCallback:
    """處理外部 runner callback，透過 repository 同步更新 job 與 evidence。"""

    repository: GeoQueryRunJobRepository
    clock: Clock

    async def execute(self, callback: ExternalRunCallback) -> GeoQueryRunJob:
        return await self.repository.apply_external_callback(
            callback=callback,
            occurred_at=self.clock.now(),
        )


def _callback_url(callback_base_url: str, job_id: UUID) -> str:
    return f"{callback_base_url.rstrip('/')}/api/geo/jobs/{job_id}/external-callbacks"
