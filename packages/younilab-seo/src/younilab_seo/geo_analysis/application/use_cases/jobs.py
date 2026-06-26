from dataclasses import dataclass
from uuid import UUID

from younilab_seo.geo_analysis.application.contracts import (
    CreateQueryRunJobCommand,
    ExternalRunCallback,
    GeoRunResultRecord,
)
from younilab_seo.geo_analysis.application.interfaces import (
    Clock,
    GeoAnalysisRepository,
)
from younilab_seo.geo_analysis.domain import GeoQueryRunJob


@dataclass(frozen=True)
class ManageQueryRunJobs:
    """管理 GEO query run job lifecycle，尚不負責 queue dispatch。"""

    repository: GeoAnalysisRepository
    clock: Clock

    async def create_job(
        self,
        query_id: UUID,
        command: CreateQueryRunJobCommand,
    ) -> GeoQueryRunJob | None:
        return await self.repository.create_job(query_id, command)

    async def list_jobs(self, project_id: UUID) -> list[GeoQueryRunJob]:
        return await self.repository.list_jobs(project_id)

    async def get_job(self, job_id: UUID) -> GeoQueryRunJob | None:
        return await self.repository.get_job(job_id)

    async def list_job_run_results(self, job_id: UUID) -> list[GeoRunResultRecord]:
        return await self.repository.list_job_run_results(job_id)

    async def list_project_run_results(
        self,
        project_id: UUID,
    ) -> list[GeoRunResultRecord]:
        return await self.repository.list_project_run_results(project_id)

    async def get_run_result(self, result_id: UUID) -> GeoRunResultRecord | None:
        return await self.repository.get_run_result(result_id)

    async def cancel_job(self, job_id: UUID) -> GeoQueryRunJob | None:
        job = await self.repository.get_job(job_id)
        if job is None:
            return None
        job.cancel(now=self.clock.now())
        await self.repository.save(job)
        return job

    async def apply_external_callback(
        self,
        callback: ExternalRunCallback,
    ) -> GeoQueryRunJob:
        return await self.repository.apply_external_callback(
            callback=callback,
            occurred_at=self.clock.now(),
        )
