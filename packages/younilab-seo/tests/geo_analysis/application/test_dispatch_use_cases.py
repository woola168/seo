from dataclasses import dataclass, field
import asyncio
from datetime import UTC, datetime
from uuid import UUID, uuid4

from younilab_seo.geo_analysis.application import (
    DispatchQueryRunJobError,
    DispatchQueryRunJob,
    ExternalRunCallback,
    GeoQueryRunJobDispatchContext,
    PublishResult,
    QueryRunJobMessage,
    ReceiveExternalRunCallback,
)
from younilab_seo.geo_analysis.domain import GeoQueryRunJob, JobStatus


@dataclass
class FakeClock:
    current: datetime = datetime(2026, 6, 22, tzinfo=UTC)

    def now(self) -> datetime:
        return self.current


@dataclass
class FakePublisher:
    result: PublishResult
    messages: list[QueryRunJobMessage] = field(default_factory=list)

    async def publish(self, message: QueryRunJobMessage) -> PublishResult:
        self.messages.append(message)
        return self.result


@dataclass
class FailingPublisher:
    messages: list[QueryRunJobMessage] = field(default_factory=list)

    async def publish(self, message: QueryRunJobMessage) -> PublishResult:
        self.messages.append(message)
        raise RuntimeError("publisher crashed")


@dataclass
class FakeRepository:
    job: GeoQueryRunJob
    context: GeoQueryRunJobDispatchContext
    dispatches: list[PublishResult] = field(default_factory=list)
    callbacks: list[ExternalRunCallback] = field(default_factory=list)

    async def get(self, job_id: UUID) -> GeoQueryRunJob:
        assert job_id == self.job.id
        return self.job

    async def save(self, job: GeoQueryRunJob) -> None:
        self.job = job

    async def get_job_dispatch_context(
        self,
        job_id: UUID,
    ) -> GeoQueryRunJobDispatchContext | None:
        assert job_id == self.job.id
        return self.context

    async def record_dispatch(
        self,
        *,
        job_id: UUID,
        result: PublishResult,
        payload: QueryRunJobMessage,
        occurred_at: datetime,
    ) -> None:
        self.dispatches.append(result)

    async def record_external_callback(
        self,
        *,
        callback: ExternalRunCallback,
        occurred_at: datetime,
    ) -> None:
        self.callbacks.append(callback)

    async def apply_external_callback(
        self,
        *,
        callback: ExternalRunCallback,
        occurred_at: datetime,
    ) -> GeoQueryRunJob:
        self.job.mark_external_status(
            external_run_id=callback.external_run_id,
            external_status=callback.status,
            error_code=callback.error_code,
            error_message=callback.error_message,
            now=occurred_at,
        )
        self.callbacks.append(callback)
        return self.job


def make_job() -> GeoQueryRunJob:
    now = datetime(2026, 6, 22, tzinfo=UTC)
    return GeoQueryRunJob(
        id=uuid4(),
        project_id=uuid4(),
        query_id=uuid4(),
        platform_id=uuid4(),
        schedule_id=None,
        job_type="manual_run",
        priority="normal",
        scheduled_for=now,
        status=JobStatus.PENDING,
        attempt_count=0,
        max_attempts=3,
        dedupe_key="dedupe",
        created_at=now,
        updated_at=now,
    )


def make_message(job: GeoQueryRunJob) -> QueryRunJobMessage:
    return QueryRunJobMessage(
        job_id=job.id,
        project_id=job.project_id,
        seo_task_id=uuid4(),
        query_id=job.query_id,
        query_text="Which suppliers are recommended?",
        topic_name="Supplier evaluation",
        platform="openai",
        region="US",
        language="en-US",
        market_type="b2b_procurement",
        is_branded=False,
        scheduled_for=job.scheduled_for,
        callback_url="https://example.test/callback",
    )


def make_context(job: GeoQueryRunJob) -> GeoQueryRunJobDispatchContext:
    return GeoQueryRunJobDispatchContext(
        job_id=job.id,
        project_id=job.project_id,
        seo_task_id=uuid4(),
        query_id=job.query_id,
        query_text="Which suppliers are recommended?",
        topic_name="Supplier evaluation",
        platform="openai",
        model="gpt-4.1-mini",
        region="US",
        language="en-US",
        market_type="b2b_procurement",
        is_branded=False,
        scheduled_for=job.scheduled_for,
    )


def test_dispatch_records_successful_publish() -> None:
    async def run() -> None:
        job = make_job()
        repository = FakeRepository(job, make_context(job))
        publisher = FakePublisher(
            PublishResult(
                backend="fake",
                destination="geo-jobs",
                message_id="message-1",
                status="published",
            )
        )

        await DispatchQueryRunJob(repository, publisher, FakeClock()).execute(
            job.id,
            "https://example.test",
        )

        assert repository.job.status is JobStatus.PUBLISHED
        assert repository.job.dispatch_message_id == "message-1"
        assert len(repository.dispatches) == 1
        assert len(publisher.messages) == 1
        assert publisher.messages[0].platform == "openai"
        assert publisher.messages[0].model == "gpt-4.1-mini"
        assert publisher.messages[0].topic_name == "Supplier evaluation"
        assert publisher.messages[0].market_type == "b2b_procurement"
        assert publisher.messages[0].is_branded is False
        assert (
            publisher.messages[0].callback_url
            == f"https://example.test/api/geo/jobs/{job.id}/external-callbacks"
        )

    asyncio.run(run())


def test_dispatch_rejects_missing_project_seo_task_id() -> None:
    async def run() -> None:
        job = make_job()
        context = make_context(job).model_copy(update={"seo_task_id": None})
        repository = FakeRepository(job, context)
        publisher = FakePublisher(
            PublishResult(
                backend="fake",
                destination="geo-jobs",
                message_id="message-1",
                status="published",
            )
        )

        try:
            await DispatchQueryRunJob(repository, publisher, FakeClock()).execute(
                job.id,
                "https://example.test",
            )
        except DispatchQueryRunJobError as exc:
            assert str(exc) == "project seoTaskId is required to dispatch job"
        else:
            raise AssertionError("expected missing seoTaskId to reject dispatch")

        assert publisher.messages == []
        assert repository.dispatches == []
        assert repository.job.status is JobStatus.PENDING

    asyncio.run(run())


def test_dispatch_failure_delays_job() -> None:
    async def run() -> None:
        job = make_job()
        repository = FakeRepository(job, make_context(job))
        publisher = FakePublisher(
            PublishResult(
                backend="fake",
                destination="geo-jobs",
                status="failed",
                error_message="broker unavailable",
            )
        )

        await DispatchQueryRunJob(repository, publisher, FakeClock()).execute(
            job.id,
            "https://example.test",
        )

        assert repository.job.status is JobStatus.DELAYED
        assert repository.job.next_retry_at is not None
        assert len(repository.dispatches) == 1

    asyncio.run(run())


def test_dispatch_exception_delays_job_and_records_dispatch() -> None:
    async def run() -> None:
        job = make_job()
        repository = FakeRepository(job, make_context(job))
        publisher = FailingPublisher()

        await DispatchQueryRunJob(repository, publisher, FakeClock()).execute(
            job.id,
            "https://example.test",
        )

        assert repository.job.status is JobStatus.DELAYED
        assert repository.job.next_retry_at is not None
        assert repository.job.last_error_message == "publisher crashed"
        assert len(repository.dispatches) == 1
        assert repository.dispatches[0].backend == "unknown"
        assert repository.dispatches[0].destination == ""
        assert repository.dispatches[0].status == "failed"

    asyncio.run(run())


def test_external_callback_updates_reference_state() -> None:
    async def run() -> None:
        job = make_job()
        job.status = JobStatus.PUBLISHED
        repository = FakeRepository(job, make_context(job))
        callback = ExternalRunCallback(
            job_id=job.id,
            external_run_id="runner-1",
            status="running",
        )

        result = await ReceiveExternalRunCallback(repository, FakeClock()).execute(
            callback,
        )

        assert repository.job.status is JobStatus.RUNNING_EXTERNAL
        assert result is repository.job
        assert repository.job.external_run_id == "runner-1"
        assert repository.callbacks == [callback]

    asyncio.run(run())
