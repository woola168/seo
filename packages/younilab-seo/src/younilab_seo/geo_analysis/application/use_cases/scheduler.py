from dataclasses import dataclass
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from younilab_seo.geo_analysis.application.contracts import DailySchedulerTickResult
from younilab_seo.geo_analysis.application.interfaces import Clock, GeoAnalysisRepository
from younilab_seo.geo_analysis.application.use_cases.dispatch import DispatchQueryRunJob


@dataclass(frozen=True)
class RunDailySchedulerTick:
    """展開當日工作、處理逾時狀態，並派送已到期的 jobs。"""

    repository: GeoAnalysisRepository
    dispatcher: DispatchQueryRunJob
    clock: Clock
    callback_base_url: str
    timezone: ZoneInfo = ZoneInfo("Asia/Taipei")
    daily_time: time = time(3, 0)
    stale_after: timedelta = timedelta(minutes=5)
    dispatch_limit: int = 500

    async def execute(self) -> DailySchedulerTickResult:
        now = self.clock.now()
        local_now = now.astimezone(self.timezone)
        business_date = local_now.date()
        due = local_now.time().replace(tzinfo=None) >= self.daily_time
        materialized_batches = 0
        materialized_jobs = 0
        budget_enforced = False
        if due:
            scheduled_for = datetime.combine(
                business_date,
                self.daily_time,
                tzinfo=self.timezone,
            )
            materialized = await self.repository.materialize_daily_runs(
                business_date=business_date,
                scheduled_for=scheduled_for,
                occurred_at=now,
            )
            materialized_batches = materialized.batch_count
            materialized_jobs = materialized.job_count
            budget_enforced = materialized.budget_enforced
        reconciled = await self.repository.reconcile_stale_jobs(
            stale_before=now - self.stale_after,
            occurred_at=now,
        )
        job_ids = await self.repository.list_dispatchable_job_ids(
            occurred_at=now,
            limit=self.dispatch_limit,
        )
        dispatched = 0
        for job_id in job_ids:
            job = await self.dispatcher.execute(job_id, self.callback_base_url)
            if job.status.value == "published":
                dispatched += 1
        return DailySchedulerTickResult(
            due=due,
            business_date=business_date,
            materialized_batches=materialized_batches,
            materialized_jobs=materialized_jobs,
            dispatched_jobs=dispatched,
            reconciled_jobs=reconciled,
            budget_enforced=budget_enforced,
        )
