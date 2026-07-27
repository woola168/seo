from datetime import date, datetime
from typing import Protocol, runtime_checkable
from uuid import UUID

from younilab_seo.geo_analysis.application.contracts import (
    CreateQueryRunJobCommand,
    DailyRunMaterializationResult,
    ExternalRunCallback,
    GeoProjectRecord,
    GeoQueryRunJobDispatchContext,
    GeoRunResultAnalysis,
    GeoRunResultRecord,
    PublishResult,
    QueryRunJobMessage,
    SaveTrackingRunResultCommand,
)
from younilab_seo.geo_analysis.domain import GeoQueryRunJob


@runtime_checkable
class RunDispatchPersistence(Protocol):
    """Claim、組裝並保存單筆 run job dispatch 的 persistence interface。"""

    async def get(self, job_id: UUID) -> GeoQueryRunJob: ...

    async def get_job_project(
        self,
        tenant_id: UUID,
        job_id: UUID,
    ) -> GeoProjectRecord | None: ...

    async def get_job_dispatch_context(
        self,
        job_id: UUID,
    ) -> GeoQueryRunJobDispatchContext | None: ...

    async def claim_job_for_publish(
        self,
        *,
        job_id: UUID,
        occurred_at: datetime,
    ) -> GeoQueryRunJob | None: ...

    async def record_dispatch(
        self,
        *,
        job_id: UUID,
        result: PublishResult,
        payload: QueryRunJobMessage,
        occurred_at: datetime,
    ) -> GeoQueryRunJob: ...


@runtime_checkable
class RunCallbackPersistence(Protocol):
    """原子套用外部 runner callback 的 persistence interface。"""

    async def apply_external_callback(
        self,
        *,
        callback: ExternalRunCallback,
        occurred_at: datetime,
    ) -> GeoQueryRunJob: ...


@runtime_checkable
class RunExecutionPersistence(Protocol):
    """Claim provider execution 並保存 tracking 結果的 persistence interface。"""

    async def get_job_tenant_id(self, job_id: UUID) -> UUID | None: ...

    async def claim_job_for_execution(
        self,
        *,
        job_id: UUID,
        tenant_id: UUID,
        external_run_id: str,
        occurred_at: datetime,
    ) -> bool: ...

    async def save_tracking_run_result(
        self,
        *,
        command: SaveTrackingRunResultCommand,
        occurred_at: datetime,
    ) -> GeoQueryRunJob: ...

    async def list_job_run_results(
        self,
        tenant_id: UUID,
        job_id: UUID,
    ) -> list[GeoRunResultRecord]: ...


@runtime_checkable
class RunResultReadPersistence(Protocol):
    """讀取 tenant-scoped jobs、raw results 與 semantic result 的介面。"""

    async def get_job_project(
        self,
        tenant_id: UUID,
        job_id: UUID,
    ) -> GeoProjectRecord | None: ...

    async def list_job_run_results(
        self,
        tenant_id: UUID,
        job_id: UUID,
    ) -> list[GeoRunResultRecord]: ...

    async def list_project_run_results(
        self,
        tenant_id: UUID,
        project_id: UUID,
    ) -> list[GeoRunResultRecord]: ...

    async def get_run_result(
        self,
        tenant_id: UUID,
        result_id: UUID,
    ) -> GeoRunResultRecord | None: ...

    async def get_semantic_run_result_analysis(
        self,
        tenant_id: UUID,
        result_id: UUID,
    ) -> GeoRunResultAnalysis | None: ...


@runtime_checkable
class RunJobManagementPersistence(
    RunCallbackPersistence,
    RunResultReadPersistence,
    Protocol,
):
    """管理 run job 與 cancellation 所需的 tenant-scoped persistence 介面。"""

    async def get_project(
        self,
        tenant_id: UUID,
        project_id: UUID,
    ) -> GeoProjectRecord | None: ...

    async def get_query_project(
        self,
        tenant_id: UUID,
        query_id: UUID,
    ) -> GeoProjectRecord | None: ...

    async def get_run_result_project(
        self,
        tenant_id: UUID,
        result_id: UUID,
    ) -> GeoProjectRecord | None: ...

    async def create_job(
        self,
        tenant_id: UUID,
        query_id: UUID,
        command: CreateQueryRunJobCommand,
    ) -> tuple[GeoQueryRunJob, bool] | None: ...

    async def list_jobs(
        self,
        tenant_id: UUID,
        project_id: UUID,
    ) -> list[GeoQueryRunJob]: ...

    async def get_job(
        self,
        tenant_id: UUID,
        job_id: UUID,
    ) -> GeoQueryRunJob | None: ...

    async def save(self, job: GeoQueryRunJob) -> None: ...


@runtime_checkable
class RunSchedulerPersistence(Protocol):
    """每日 materialization、逾時修復與待派送查詢的 persistence interface。"""

    async def materialize_daily_runs(
        self,
        *,
        business_date: date,
        scheduled_for: datetime,
        occurred_at: datetime,
    ) -> DailyRunMaterializationResult: ...

    async def list_dispatchable_job_ids(
        self,
        *,
        occurred_at: datetime,
        limit: int,
    ) -> list[UUID]: ...

    async def reconcile_stale_jobs(
        self,
        *,
        stale_before: datetime,
        occurred_at: datetime,
    ) -> int: ...
