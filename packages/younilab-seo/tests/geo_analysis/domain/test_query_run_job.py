from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from younilab_seo.geo_analysis.domain import (
    GeoQueryRunJob,
    JobStatus,
    QueryRunJobStatusError,
)


def make_job(status: JobStatus = JobStatus.PENDING) -> GeoQueryRunJob:
    now = datetime(2026, 6, 22, tzinfo=UTC)
    return GeoQueryRunJob(
        id=uuid4(),
        project_id=uuid4(),
        query_id=uuid4(),
        platform_id=uuid4(),
        schedule_id=None,
        job_type="scheduled_run",
        priority="normal",
        scheduled_for=now,
        status=status,
        attempt_count=0,
        max_attempts=3,
        dedupe_key="project/query/platform/2026-06-22",
        created_at=now,
        updated_at=now,
    )


def test_publish_success_records_dispatch_reference() -> None:
    job = make_job()
    now = datetime(2026, 6, 22, 1, tzinfo=UTC)

    job.mark_publishing(now)
    job.mark_published(backend="fake", message_id="message-1", now=now)

    assert job.status is JobStatus.PUBLISHED
    assert job.attempt_count == 1
    assert job.dispatch_backend == "fake"
    assert job.dispatch_message_id == "message-1"


def test_publish_failure_delays_retry_until_attempts_are_exhausted() -> None:
    job = make_job()
    now = datetime(2026, 6, 22, 1, tzinfo=UTC)
    retry_at = now + timedelta(minutes=5)

    job.mark_publishing(now)
    job.mark_publish_failed(
        error_code="broker_unavailable",
        error_message="broker unavailable",
        next_retry_at=retry_at,
        now=now,
    )

    assert job.status is JobStatus.DELAYED
    assert job.next_retry_at == retry_at

    job.mark_publishing(now)
    job.mark_publish_failed(
        error_code="broker_unavailable",
        error_message="broker unavailable",
        next_retry_at=retry_at,
        now=now,
    )
    job.mark_publishing(now)
    job.mark_publish_failed(
        error_code="broker_unavailable",
        error_message="broker unavailable",
        next_retry_at=retry_at,
        now=now,
    )

    assert job.status is JobStatus.FAILED


def test_external_callback_moves_published_job_to_terminal_state() -> None:
    job = make_job(JobStatus.PUBLISHED)
    now = datetime(2026, 6, 22, 1, tzinfo=UTC)

    job.mark_external_status(
        external_run_id="external-1",
        external_status="succeeded",
        error_code=None,
        error_message=None,
        now=now,
    )

    assert job.status is JobStatus.SUCCEEDED
    assert job.external_run_id == "external-1"


@pytest.mark.parametrize(
    "status",
    [JobStatus.SUCCEEDED, JobStatus.FAILED, JobStatus.CANCELLED],
)
def test_external_callback_cannot_change_terminal_job(status: JobStatus) -> None:
    job = make_job(status)
    now = datetime(2026, 6, 22, 1, tzinfo=UTC)

    with pytest.raises(QueryRunJobStatusError):
        job.mark_external_status(
            external_run_id="external-1",
            external_status="running",
            error_code=None,
            error_message=None,
            now=now,
        )

    assert job.status is status
    assert job.external_run_id is None


def test_unsupported_external_status_does_not_partially_update_job() -> None:
    job = make_job(JobStatus.PUBLISHED)
    original_updated_at = job.updated_at
    now = datetime(2026, 6, 22, 1, tzinfo=UTC)

    with pytest.raises(QueryRunJobStatusError):
        job.mark_external_status(
            external_run_id="external-1",
            external_status="unknown",
            error_code="runner_error",
            error_message="runner error",
            now=now,
        )

    assert job.status is JobStatus.PUBLISHED
    assert job.external_run_id is None
    assert job.last_error_code is None
    assert job.last_error_message is None
    assert job.updated_at == original_updated_at


def test_cancelled_job_cannot_be_cancelled_again() -> None:
    job = make_job(JobStatus.CANCELLED)

    with pytest.raises(QueryRunJobStatusError):
        job.cancel(datetime(2026, 6, 22, 1, tzinfo=UTC))


def test_invalid_transition_is_rejected() -> None:
    job = make_job(JobStatus.SUCCEEDED)

    with pytest.raises(QueryRunJobStatusError):
        job.mark_publishing(datetime(2026, 6, 22, 1, tzinfo=UTC))
