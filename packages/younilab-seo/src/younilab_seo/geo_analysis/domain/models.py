from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum
from uuid import UUID


class JobStatus(StrEnum):
    """GEO query run job lifecycle state."""

    PENDING = "pending"
    PUBLISHING = "publishing"
    PUBLISHED = "published"
    RUNNING_EXTERNAL = "running_external"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    DELAYED = "delayed"
    CANCELLED = "cancelled"


class QueryRunJobStatusError(ValueError):
    """Raised when a query run job receives an invalid state transition."""


@dataclass
class GeoQueryRunJob:
    """A GEO query task tracked through dispatch and external runner states."""

    id: UUID
    project_id: UUID
    query_id: UUID
    platform_id: UUID
    schedule_id: UUID | None
    job_type: str
    priority: str
    scheduled_for: datetime
    status: JobStatus
    attempt_count: int
    max_attempts: int
    dedupe_key: str
    created_at: datetime
    updated_at: datetime
    batch_id: UUID | None = None
    source: str = "manual"
    execution_snapshot: dict | None = None
    next_retry_at: datetime | None = None
    dispatch_backend: str | None = None
    dispatch_message_id: str | None = None
    external_run_id: str | None = None
    last_error_code: str | None = None
    last_error_message: str | None = None

    def mark_publishing(self, now: datetime) -> None:
        self._require_status(JobStatus.PENDING, JobStatus.DELAYED)
        self.status = JobStatus.PUBLISHING
        self.attempt_count += 1
        self.updated_at = now

    def mark_published(
        self,
        *,
        backend: str,
        message_id: str | None,
        now: datetime,
    ) -> None:
        self._require_status(JobStatus.PUBLISHING)
        self.status = JobStatus.PUBLISHED
        self.dispatch_backend = backend
        self.dispatch_message_id = message_id
        self.last_error_code = None
        self.last_error_message = None
        self.updated_at = now

    def mark_publish_failed(
        self,
        *,
        error_code: str,
        error_message: str,
        next_retry_at: datetime | None,
        now: datetime,
    ) -> None:
        self._require_status(JobStatus.PUBLISHING)
        self.last_error_code = error_code
        self.last_error_message = error_message
        self.next_retry_at = next_retry_at
        self.status = (
            JobStatus.DELAYED
            if next_retry_at is not None and self.attempt_count < self.max_attempts
            else JobStatus.FAILED
        )
        self.updated_at = now

    def mark_stale(self, *, error_code: str, now: datetime) -> None:
        self._require_status(JobStatus.PUBLISHING, JobStatus.RUNNING_EXTERNAL)
        self.status = JobStatus.FAILED
        self.last_error_code = error_code
        self.last_error_message = error_code
        self.next_retry_at = None
        self.updated_at = now

    def mark_external_status(
        self,
        *,
        external_run_id: str,
        external_status: str,
        error_code: str | None,
        error_message: str | None,
        now: datetime,
    ) -> None:
        next_status = _external_status_to_job_status(external_status)
        if self.status not in {
            JobStatus.PUBLISHING,
            JobStatus.PUBLISHED,
            JobStatus.RUNNING_EXTERNAL,
        }:
            raise QueryRunJobStatusError(
                f"cannot apply external status from {self.status}"
            )
        self.external_run_id = external_run_id
        self.last_error_code = error_code
        self.last_error_message = error_message
        self.updated_at = now
        self.status = next_status

    def cancel(self, now: datetime) -> None:
        if self.status in {JobStatus.SUCCEEDED, JobStatus.FAILED, JobStatus.CANCELLED}:
            raise QueryRunJobStatusError(f"cannot cancel {self.status} job")
        self.status = JobStatus.CANCELLED
        self.updated_at = now

    def _require_status(self, *allowed: JobStatus) -> None:
        if self.status not in set(allowed):
            expected = ", ".join(status.value for status in allowed)
            raise QueryRunJobStatusError(
                f"expected job status {expected}, got {self.status}"
            )


@dataclass(frozen=True)
class GeoDailyRunBatch:
    """單一 Project 每日排程展開後的批次結果。"""

    id: UUID
    project_id: UUID
    business_date: date
    scheduled_for: datetime
    status: str
    candidate_count: int
    job_count: int
    budget_enforced: bool
    created_at: datetime
    updated_at: datetime


def _external_status_to_job_status(external_status: str) -> JobStatus:
    match external_status:
        case "accepted" | "running":
            return JobStatus.RUNNING_EXTERNAL
        case "succeeded":
            return JobStatus.SUCCEEDED
        case "failed":
            return JobStatus.FAILED
        case _:
            raise QueryRunJobStatusError(
                f"unsupported external status {external_status}"
            )
