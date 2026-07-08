from dataclasses import dataclass
from uuid import UUID

from younilab_seo.geo_analysis.application.contracts import (
    CreateQueryRunJobCommand,
    ExternalRunCallback,
    GeoRunResultAnalysis,
    GeoRunResultRecord,
)
from younilab_seo.geo_analysis.application.interfaces import (
    AuthorizedPrincipal,
    Clock,
    GeoAnalysisRepository,
)
from younilab_seo.geo_analysis.application.use_cases.access_policy import (
    can_access_project,
)
from younilab_seo.geo_analysis.domain import GeoQueryRunJob


@dataclass(frozen=True)
class ManageQueryRunJobs:
    """管理 GEO query run job lifecycle，尚不負責 queue dispatch。"""

    repository: GeoAnalysisRepository
    clock: Clock

    async def create_job(
        self,
        principal: AuthorizedPrincipal,
        query_id: UUID,
        command: CreateQueryRunJobCommand,
    ) -> GeoQueryRunJob | None:
        project = await self.repository.get_query_project(principal.tenant_id, query_id)
        if project is None or not can_access_project(principal, project):
            return None
        return await self.repository.create_job(principal.tenant_id, query_id, command)

    async def list_jobs(
        self,
        principal: AuthorizedPrincipal,
        project_id: UUID,
    ) -> list[GeoQueryRunJob]:
        if not await self._can_access_project(principal, project_id):
            return []
        return await self.repository.list_jobs(principal.tenant_id, project_id)

    async def get_job(
        self,
        principal: AuthorizedPrincipal,
        job_id: UUID,
    ) -> GeoQueryRunJob | None:
        project = await self.repository.get_job_project(principal.tenant_id, job_id)
        if project is None or not can_access_project(principal, project):
            return None
        return await self.repository.get_job(principal.tenant_id, job_id)

    async def list_job_run_results(
        self,
        principal: AuthorizedPrincipal,
        job_id: UUID,
    ) -> list[GeoRunResultRecord]:
        if await self.get_job(principal, job_id) is None:
            return []
        return await self.repository.list_job_run_results(principal.tenant_id, job_id)

    async def list_project_run_results(
        self,
        principal: AuthorizedPrincipal,
        project_id: UUID,
    ) -> list[GeoRunResultRecord]:
        if not await self._can_access_project(principal, project_id):
            return []
        return await self.repository.list_project_run_results(
            principal.tenant_id,
            project_id,
        )

    async def get_run_result(
        self,
        principal: AuthorizedPrincipal,
        result_id: UUID,
    ) -> GeoRunResultRecord | None:
        project = await self.repository.get_run_result_project(
            principal.tenant_id,
            result_id,
        )
        if project is None or not can_access_project(principal, project):
            return None
        return await self.repository.get_run_result(principal.tenant_id, result_id)

    async def get_run_result_semantic_analysis(
        self,
        principal: AuthorizedPrincipal,
        result_id: UUID,
    ) -> GeoRunResultAnalysis | None:
        if await self.get_run_result(principal, result_id) is None:
            return None
        return await self.repository.get_semantic_run_result_analysis(
            principal.tenant_id,
            result_id,
        )

    async def cancel_job(
        self,
        principal: AuthorizedPrincipal,
        job_id: UUID,
    ) -> GeoQueryRunJob | None:
        job = await self.get_job(principal, job_id)
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

    async def _can_access_project(
        self,
        principal: AuthorizedPrincipal,
        project_id: UUID,
    ) -> bool:
        project = await self.repository.get_project(principal.tenant_id, project_id)
        return project is not None and can_access_project(principal, project)
