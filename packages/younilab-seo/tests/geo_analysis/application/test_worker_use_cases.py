from dataclasses import dataclass, field
import asyncio
from datetime import UTC, datetime
import logging
from uuid import UUID, uuid4

from younilab_seo.geo_analysis.application import (
    ExternalRunCallback,
    ProcessQueryRunJobMessage,
    QueryRunJobMessageRejected,
    QueryRunJobMessage,
    SaveTrackingRunResultCommand,
    TrackingRunReference,
    TrackingRunResponse,
    TrackingRunResultItem,
)
from younilab_seo.geo_analysis.domain import GeoQueryRunJob, JobStatus


TENANT_ID = UUID("00000000-0000-4000-8000-000000000001")
OTHER_TENANT_ID = UUID("00000000-0000-4000-8000-000000000002")


@dataclass
class FakeClock:
    current: datetime = datetime(2026, 6, 25, tzinfo=UTC)

    def now(self) -> datetime:
        return self.current


@dataclass
class FakeRepository:
    job: GeoQueryRunJob
    callbacks: list[ExternalRunCallback] = field(default_factory=list)
    save_commands: list[SaveTrackingRunResultCommand] = field(default_factory=list)
    result_ids: list[UUID] = field(default_factory=list)
    save_error: Exception | None = None

    async def get_job_tenant_id(self, job_id) -> UUID | None:
        if job_id != self.job.id:
            return None
        return TENANT_ID

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

    async def save_tracking_run_result(
        self,
        *,
        command: SaveTrackingRunResultCommand,
        occurred_at: datetime,
    ) -> GeoQueryRunJob:
        if self.save_error is not None:
            raise self.save_error
        external_run_id = command.response.id if command.response is not None else "unknown"
        self.job.mark_external_status(
            external_run_id=external_run_id,
            external_status=command.status,
            error_code=command.error_code,
            error_message=command.error_message,
            now=occurred_at,
        )
        self.save_commands.append(command)
        self.result_ids = [uuid4() for _ in (command.response.results if command.response else [])]
        return self.job

    async def list_job_run_results(self, tenant_id: UUID, job_id: UUID):
        return [
            type("RunResult", (), {"id": result_id})()
            for result_id in self.result_ids
        ]


@dataclass
class FakeTrackingClient:
    result: TrackingRunResponse | None = None
    error: Exception | None = None
    messages: list[QueryRunJobMessage] = field(default_factory=list)

    def build_request_payload(self, message: QueryRunJobMessage) -> dict:
        payload = {
            "provider": message.platform,
            "timing": "run_now",
            "queries": [
                {
                    "id": str(message.query_id),
                    "text": message.query_text,
                    "topicName": message.topic_name,
                }
            ],
        }
        if message.seo_task_id is not None:
            payload["seoTaskId"] = str(message.seo_task_id)
        return payload

    async def run(self, message: QueryRunJobMessage) -> TrackingRunResponse:
        self.messages.append(message)
        if self.error is not None:
            raise self.error
        assert self.result is not None
        return self.result


@dataclass
class FakePipelineStep:
    error_on_calls: set[int] = field(default_factory=set)
    error_message: str = "pipeline unavailable"
    calls: list[tuple[UUID, UUID]] = field(default_factory=list)

    async def execute(self, tenant_id: UUID, result_id: UUID) -> None:
        self.calls.append((tenant_id, result_id))
        if len(self.calls) in self.error_on_calls:
            raise RuntimeError(self.error_message)


def test_worker_marks_completed_tracking_run_succeeded() -> None:
    async def run() -> None:
        job = make_job()
        repository = FakeRepository(job)
        tracking = FakeTrackingClient(make_tracking_response(job, status="completed"))

        result = await ProcessQueryRunJobMessage(
            repository=repository,
            tracking_client=tracking,
            clock=FakeClock(),
            supported_provider="gemini",
        ).execute(make_message(job, platform="gemini"))

        assert result.status is JobStatus.SUCCEEDED
        assert result.external_run_id == "tracking-run-1"
        assert [callback.status for callback in repository.callbacks] == [
            "running",
        ]
        assert repository.save_commands[0].response is not None
        assert repository.save_commands[0].request_payload["provider"] == "gemini"
        assert "jobId" not in repository.save_commands[0].request_payload
        saved = repository.save_commands[0].response.results[0]
        assert saved.raw_response == "Raw answer"
        assert saved.references[0].url == "https://example.com/reference"
        assert len(tracking.messages) == 1

    asyncio.run(run())


def test_worker_runs_report_pipeline_after_completed_tracking_result() -> None:
    async def run() -> None:
        job = make_job()
        repository = FakeRepository(job)
        tracking = FakeTrackingClient(make_tracking_response(job, status="completed"))
        analyzer = FakePipelineStep()
        normalizer = FakePipelineStep()

        await ProcessQueryRunJobMessage(
            repository=repository,
            tracking_client=tracking,
            clock=FakeClock(),
            supported_provider="gemini",
            analyze_run_result=analyzer,
            normalize_run_result_citations=normalizer,
        ).execute(make_message(job, platform="gemini"))

        assert analyzer.calls == [(TENANT_ID, repository.result_ids[0])]
        assert normalizer.calls == [(TENANT_ID, repository.result_ids[0])]

    asyncio.run(run())


def test_worker_keeps_tracking_job_succeeded_when_semantic_analysis_crashes() -> None:
    async def run() -> None:
        job = make_job()
        repository = FakeRepository(job)
        tracking = FakeTrackingClient(
            make_tracking_response(job, status="completed", result_count=2)
        )
        analyzer = FakePipelineStep(error_on_calls={1})
        normalizer = FakePipelineStep()

        result = await ProcessQueryRunJobMessage(
            repository=repository,
            tracking_client=tracking,
            clock=FakeClock(),
            supported_provider="gemini",
            analyze_run_result=analyzer,
            normalize_run_result_citations=normalizer,
        ).execute(make_message(job, platform="gemini"))

        assert result.status is JobStatus.SUCCEEDED
        assert result.last_error_code is None
        assert analyzer.calls == [
            (TENANT_ID, repository.result_ids[0]),
            (TENANT_ID, repository.result_ids[1]),
        ]
        assert normalizer.calls == [(TENANT_ID, repository.result_ids[1])]

    asyncio.run(run())


def test_worker_keeps_tracking_job_succeeded_when_citation_normalization_crashes() -> None:
    async def run() -> None:
        job = make_job()
        repository = FakeRepository(job)
        tracking = FakeTrackingClient(
            make_tracking_response(job, status="completed", result_count=2)
        )
        analyzer = FakePipelineStep()
        normalizer = FakePipelineStep(error_on_calls={1})

        result = await ProcessQueryRunJobMessage(
            repository=repository,
            tracking_client=tracking,
            clock=FakeClock(),
            supported_provider="gemini",
            analyze_run_result=analyzer,
            normalize_run_result_citations=normalizer,
        ).execute(make_message(job, platform="gemini"))

        assert result.status is JobStatus.SUCCEEDED
        assert result.last_error_code is None
        assert analyzer.calls == [
            (TENANT_ID, repository.result_ids[0]),
            (TENANT_ID, repository.result_ids[1]),
        ]
        assert normalizer.calls == [
            (TENANT_ID, repository.result_ids[0]),
            (TENANT_ID, repository.result_ids[1]),
        ]

    asyncio.run(run())


def test_worker_processes_google_aio_message_and_saves_references() -> None:
    async def run() -> None:
        job = make_job()
        repository = FakeRepository(job)
        tracking = FakeTrackingClient(
            make_tracking_response(
                job,
                status="completed",
                provider="google_aio",
                surface="Google AI Overview",
                model="serpapi-google-ai-overview",
            )
        )

        result = await ProcessQueryRunJobMessage(
            repository=repository,
            tracking_client=tracking,
            clock=FakeClock(),
            supported_provider="google_aio",
        ).execute(make_message(job, platform="google_aio"))

        assert result.status is JobStatus.SUCCEEDED
        assert repository.save_commands[0].request_payload["provider"] == "google_aio"
        saved = repository.save_commands[0].response.results[0]
        assert saved.provider == "google_aio"
        assert saved.surface == "Google AI Overview"
        assert saved.model == "serpapi-google-ai-overview"
        assert saved.references[0].title == "Example reference"

    asyncio.run(run())


def test_worker_marks_tracking_failure_failed() -> None:
    async def run() -> None:
        job = make_job()
        repository = FakeRepository(job)
        tracking = FakeTrackingClient(
            make_tracking_response(job, status="failed", error="provider_error")
        )
        analyzer = FakePipelineStep()
        normalizer = FakePipelineStep()

        result = await ProcessQueryRunJobMessage(
            repository=repository,
            tracking_client=tracking,
            clock=FakeClock(),
            supported_provider="gemini",
            analyze_run_result=analyzer,
            normalize_run_result_citations=normalizer,
        ).execute(make_message(job, platform="gemini"))

        assert result.status is JobStatus.FAILED
        assert result.last_error_code == "provider_error"
        assert result.last_error_message == "provider_error"
        assert analyzer.calls == []
        assert normalizer.calls == []

    asyncio.run(run())


def test_worker_marks_tracking_exception_failed() -> None:
    async def run() -> None:
        job = make_job()
        repository = FakeRepository(job)
        tracking = FakeTrackingClient(error=TimeoutError("request timed out"))

        result = await ProcessQueryRunJobMessage(
            repository=repository,
            tracking_client=tracking,
            clock=FakeClock(),
            supported_provider="gemini",
        ).execute(make_message(job, platform="gemini"))

        assert result.status is JobStatus.FAILED
        assert result.last_error_code == "tracking_request_failed"
        assert result.last_error_message == "request timed out"
        assert repository.save_commands[0].response is None
        assert repository.save_commands[0].request_payload["provider"] == "gemini"

    asyncio.run(run())


def test_worker_rejects_tracking_result_persistence_error_without_requeue(
    caplog,
) -> None:
    async def run() -> None:
        job = make_job()
        repository = FakeRepository(
            job,
            save_error=RuntimeError("geo_run_request seo_task_id not null"),
        )
        tracking = FakeTrackingClient(make_tracking_response(job, status="completed"))

        with caplog.at_level(logging.ERROR):
            try:
                await ProcessQueryRunJobMessage(
                    repository=repository,
                    tracking_client=tracking,
                    clock=FakeClock(),
                    supported_provider="gemini",
                ).execute(make_message(job, platform="gemini"))
            except QueryRunJobMessageRejected as exc:
                assert "tracking result persistence failed: RuntimeError" in str(exc)
            else:
                raise AssertionError("expected persistence failure to reject message")

        assert len(tracking.messages) == 1
        record = next(
            item
            for item in caplog.records
            if item.message.startswith(
                "GEO tracking result persistence failed after provider response: "
            )
        )
        assert f"jobId={job.id}" in record.message
        assert "provider=gemini" in record.message
        assert "status=succeeded" in record.message
        assert "exceptionType=RuntimeError" in record.message
        assert record.exc_info is not None

    asyncio.run(run())


def test_worker_marks_unsupported_provider_failed_without_tracking_call() -> None:
    async def run() -> None:
        job = make_job()
        repository = FakeRepository(job)
        tracking = FakeTrackingClient(make_tracking_response(job, status="completed"))
        analyzer = FakePipelineStep()
        normalizer = FakePipelineStep()

        result = await ProcessQueryRunJobMessage(
            repository=repository,
            tracking_client=tracking,
            clock=FakeClock(),
            supported_provider="gemini",
            analyze_run_result=analyzer,
            normalize_run_result_citations=normalizer,
        ).execute(make_message(job, platform="openai"))

        assert result.status is JobStatus.FAILED
        assert result.last_error_code == "unsupported_provider"
        assert tracking.messages == []
        assert analyzer.calls == []
        assert normalizer.calls == []
        assert repository.save_commands[0].response is None
        assert repository.save_commands[0].request_payload["reason"] == (
            "unsupported_provider"
        )
        assert repository.save_commands[0].request_payload["queueMessage"]["platform"] == (
            "openai"
        )

    asyncio.run(run())


def test_worker_rejects_terminal_job_without_tracking_call() -> None:
    async def run() -> None:
        job = make_job()
        job.status = JobStatus.CANCELLED
        repository = FakeRepository(job)
        tracking = FakeTrackingClient(make_tracking_response(job, status="completed"))

        try:
            await ProcessQueryRunJobMessage(
                repository=repository,
                tracking_client=tracking,
                clock=FakeClock(),
                supported_provider="gemini",
            ).execute(make_message(job, platform="gemini"))
        except QueryRunJobMessageRejected as exc:
            assert str(job.id) in str(exc)
        else:
            raise AssertionError("expected terminal job message to be rejected")

        assert tracking.messages == []
        assert repository.save_commands == []

    asyncio.run(run())


def test_worker_marks_tenant_mismatch_failed_without_tracking_call() -> None:
    async def run() -> None:
        job = make_job()
        repository = FakeRepository(job)
        tracking = FakeTrackingClient(make_tracking_response(job, status="completed"))
        analyzer = FakePipelineStep()
        normalizer = FakePipelineStep()

        result = await ProcessQueryRunJobMessage(
            repository=repository,
            tracking_client=tracking,
            clock=FakeClock(),
            supported_provider="gemini",
            analyze_run_result=analyzer,
            normalize_run_result_citations=normalizer,
        ).execute(
            make_message(job, platform="gemini").model_copy(
                update={"tenant_id": OTHER_TENANT_ID}
            )
        )

        assert result.status is JobStatus.FAILED
        assert result.last_error_code == "tenant_mismatch"
        assert tracking.messages == []
        assert analyzer.calls == []
        assert normalizer.calls == []
        assert repository.save_commands[0].request_payload["reason"] == "tenant_mismatch"

    asyncio.run(run())


def make_job() -> GeoQueryRunJob:
    now = datetime(2026, 6, 25, tzinfo=UTC)
    return GeoQueryRunJob(
        id=uuid4(),
        project_id=uuid4(),
        query_id=uuid4(),
        platform_id=uuid4(),
        schedule_id=None,
        job_type="manual_run",
        priority="normal",
        scheduled_for=now,
        status=JobStatus.PUBLISHED,
        attempt_count=1,
        max_attempts=3,
        dedupe_key="dedupe",
        created_at=now,
        updated_at=now,
    )


def make_message(job: GeoQueryRunJob, *, platform: str) -> QueryRunJobMessage:
    return QueryRunJobMessage(
        job_id=job.id,
        tenant_id=TENANT_ID,
        project_id=job.project_id,
        seo_task_id=uuid4(),
        query_id=job.query_id,
        query_text="Which suppliers are recommended?",
        topic_name="Supplier evaluation",
        platform=platform,
        model="gemini-2.5-flash",
        region="TW",
        language="zh-TW",
        market_type="b2b_procurement",
        is_branded=False,
        scheduled_for=job.scheduled_for,
        callback_url="https://example.test/callback",
    )


def make_tracking_response(
    job: GeoQueryRunJob,
    *,
    status: str,
    error: str | None = None,
    provider: str = "gemini",
    surface: str = "Gemini",
    model: str = "gemini-2.5-flash",
    result_count: int = 1,
) -> TrackingRunResponse:
    return TrackingRunResponse(
        id="tracking-run-1",
        seo_task_id=uuid4(),
        timing="run_now",
        results=[
            TrackingRunResultItem(
                id=f"tracking-result-{index}",
                run_request_id="tracking-run-1",
                query_id=job.query_id,
                provider=provider,
                surface=surface,
                model=model,
                region="TW",
                language="zh-TW",
                status=status,
                raw_response="Raw answer",
                reference_urls=["https://example.com/reference"],
                references=[
                    TrackingRunReference(
                        url="https://example.com/reference",
                        title="Example reference",
                    )
                ],
                error=error,
                run_at=job.scheduled_for,
            )
            for index in range(1, result_count + 1)
        ],
    )
