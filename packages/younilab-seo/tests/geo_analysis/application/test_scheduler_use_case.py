import asyncio
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from younilab_seo.geo_analysis.application import (
    DailyRunMaterializationResult,
    RunDailySchedulerTick,
)
from younilab_seo.geo_analysis.domain import GeoQueryRunJob, JobStatus


@dataclass
class FakeClock:
    current: datetime

    def now(self) -> datetime:
        return self.current


@dataclass
class FakeRepository:
    dispatchable_ids: list[UUID] = field(default_factory=list)
    materializations: list[tuple[date, datetime]] = field(default_factory=list)
    reconciliation_calls: int = 0

    async def materialize_daily_runs(
        self,
        *,
        business_date: date,
        scheduled_for: datetime,
        occurred_at: datetime,
    ) -> DailyRunMaterializationResult:
        self.materializations.append((business_date, scheduled_for))
        return DailyRunMaterializationResult(
            business_date=business_date,
            scheduled_for=scheduled_for,
            batch_count=1,
            job_count=2,
            budget_enforced=False,
        )

    async def reconcile_stale_jobs(self, **kwargs) -> int:
        self.reconciliation_calls += 1
        return 1

    async def list_dispatchable_scheduled_job_ids(self, **kwargs) -> list[UUID]:
        return self.dispatchable_ids


@dataclass
class FakeDispatcher:
    calls: list[UUID] = field(default_factory=list)

    async def execute(self, job_id: UUID, callback_base_url: str) -> GeoQueryRunJob:
        self.calls.append(job_id)
        now = datetime(2026, 7, 15, tzinfo=UTC)
        return GeoQueryRunJob(
            id=job_id,
            project_id=uuid4(),
            query_id=uuid4(),
            platform_id=uuid4(),
            schedule_id=None,
            job_type="scheduled_run",
            priority="normal",
            scheduled_for=now,
            status=JobStatus.PUBLISHED,
            attempt_count=1,
            max_attempts=3,
            dedupe_key=str(job_id),
            created_at=now,
            updated_at=now,
            source="scheduled",
        )


def test_tick_before_cutoff_skips_materialization_but_maintains_existing_jobs() -> None:
    async def run() -> None:
        repository = FakeRepository(dispatchable_ids=[uuid4()])
        dispatcher = FakeDispatcher()
        tick = RunDailySchedulerTick(
            repository=repository,
            dispatcher=dispatcher,
            clock=FakeClock(datetime(2026, 7, 14, 18, 59, tzinfo=UTC)),
            callback_base_url="http://geo-analysis-api:8002",
        )

        result = await tick.execute()

        assert result.due is False
        assert repository.materializations == []
        assert repository.reconciliation_calls == 1
        assert dispatcher.calls == repository.dispatchable_ids
        assert result.dispatched_jobs == 1
        assert result.reconciled_jobs == 1

    asyncio.run(run())


def test_tick_at_cutoff_materializes_today_and_dispatches_due_jobs() -> None:
    async def run() -> None:
        job_ids = [uuid4(), uuid4()]
        repository = FakeRepository(dispatchable_ids=job_ids)
        dispatcher = FakeDispatcher()
        tick = RunDailySchedulerTick(
            repository=repository,
            dispatcher=dispatcher,
            clock=FakeClock(datetime(2026, 7, 14, 19, 0, tzinfo=UTC)),
            callback_base_url="http://geo-analysis-api:8002",
            timezone=ZoneInfo("Asia/Taipei"),
        )

        result = await tick.execute()

        business_date, scheduled_for = repository.materializations[0]
        assert business_date == date(2026, 7, 15)
        assert scheduled_for.isoformat() == "2026-07-15T03:00:00+08:00"
        assert dispatcher.calls == job_ids
        assert result.materialized_batches == 1
        assert result.materialized_jobs == 2
        assert result.dispatched_jobs == 2
        assert result.reconciled_jobs == 1
        assert result.budget_enforced is False

    asyncio.run(run())
