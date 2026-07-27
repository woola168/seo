from dataclasses import dataclass
from uuid import UUID

from younilab_seo.geo_analysis.application.contracts import (
    AcceptQueryDraftCommand,
    GeoQueryRecord,
    QueryDraftRecord,
    QueryDraftSelectionCommand,
    QueryGenerationCommand,
    QueryGenerationRunRecord,
    QueryResearchCommand,
    QueryResearchRunRecord,
)
from younilab_seo.geo_analysis.application.interfaces import (
    AuthorizedPrincipal,
    Clock,
    QueryPlanningClient,
)
from younilab_seo.geo_analysis.application.interfaces.query_planning import (
    QueryPlanningPersistence,
)
from younilab_seo.geo_analysis.application.use_cases.access_policy import (
    can_access_project,
)


class GeoProjectReferenceError(ValueError):
    """GEO project 綁定的 customer/task reference 不符合規則時使用的錯誤。"""

    pass


@dataclass(frozen=True)
class ManageQueryPlanning:
    """執行 Query Research / Generation，並保存 planning run 與 draft 結果。"""

    repository: QueryPlanningPersistence
    planning_client: QueryPlanningClient
    clock: Clock

    async def run_query_research(
        self,
        principal: AuthorizedPrincipal,
        project_id: UUID,
        command: QueryResearchCommand,
    ) -> QueryResearchRunRecord | None:
        if not await self._can_access_project(principal, project_id):
            return None
        request_payload = command.model_dump(mode="json", by_alias=True)
        try:
            result = await self.planning_client.research(command)
            return await self.repository.create_query_research_run(
                principal.tenant_id,
                project_id,
                command,
                request_payload,
                result,
                "completed",
                None,
                self.clock.now(),
            )
        except Exception as exc:
            return await self.repository.create_query_research_run(
                principal.tenant_id,
                project_id,
                command,
                request_payload,
                None,
                "failed",
                str(exc),
                self.clock.now(),
            )

    async def list_query_research_runs(
        self,
        principal: AuthorizedPrincipal,
        project_id: UUID,
    ) -> list[QueryResearchRunRecord]:
        if not await self._can_access_project(principal, project_id):
            return []
        return await self.repository.list_query_research_runs(
            principal.tenant_id,
            project_id,
        )

    async def get_query_research_run(
        self,
        principal: AuthorizedPrincipal,
        run_id: UUID,
    ) -> QueryResearchRunRecord | None:
        project = await self.repository.get_query_research_run_project(
            principal.tenant_id,
            run_id,
        )
        if project is None or not can_access_project(principal, project):
            return None
        return await self.repository.get_query_research_run(principal.tenant_id, run_id)

    async def run_query_generation(
        self,
        principal: AuthorizedPrincipal,
        project_id: UUID,
        command: QueryGenerationCommand,
    ) -> QueryGenerationRunRecord | None:
        if not await self._can_access_project(principal, project_id):
            return None
        request_payload = command.model_dump(mode="json", by_alias=True)
        try:
            result = await self.planning_client.generate(command)
            return await self.repository.create_query_generation_run(
                principal.tenant_id,
                project_id,
                command,
                request_payload,
                result,
                "completed",
                None,
                self.clock.now(),
            )
        except Exception as exc:
            return await self.repository.create_query_generation_run(
                principal.tenant_id,
                project_id,
                command,
                request_payload,
                None,
                "failed",
                str(exc),
                self.clock.now(),
            )

    async def list_query_generation_runs(
        self,
        principal: AuthorizedPrincipal,
        project_id: UUID,
    ) -> list[QueryGenerationRunRecord]:
        if not await self._can_access_project(principal, project_id):
            return []
        return await self.repository.list_query_generation_runs(
            principal.tenant_id,
            project_id,
        )

    async def get_query_generation_run(
        self,
        principal: AuthorizedPrincipal,
        run_id: UUID,
    ) -> QueryGenerationRunRecord | None:
        project = await self.repository.get_query_generation_run_project(
            principal.tenant_id,
            run_id,
        )
        if project is None or not can_access_project(principal, project):
            return None
        return await self.repository.get_query_generation_run(
            principal.tenant_id, run_id
        )

    async def update_query_draft_selection(
        self,
        principal: AuthorizedPrincipal,
        draft_id: UUID,
        command: QueryDraftSelectionCommand,
    ) -> QueryDraftRecord | None:
        if command.selection_status not in {"shortlisted", "rejected"}:
            raise ValueError("selectionStatus must be shortlisted or rejected")
        project = await self.repository.get_query_draft_project(
            principal.tenant_id,
            draft_id,
        )
        if project is None or not can_access_project(principal, project):
            return None
        return await self.repository.update_query_draft_selection(
            principal.tenant_id,
            draft_id,
            command,
        )

    async def accept_query_draft(
        self,
        principal: AuthorizedPrincipal,
        draft_id: UUID,
        command: AcceptQueryDraftCommand,
    ) -> GeoQueryRecord | None:
        project = await self.repository.get_query_draft_project(
            principal.tenant_id,
            draft_id,
        )
        if project is None or not can_access_project(principal, project):
            return None
        return await self.repository.accept_query_draft(
            principal.tenant_id,
            draft_id,
            command,
        )

    async def _can_access_project(
        self,
        principal: AuthorizedPrincipal,
        project_id: UUID,
    ) -> bool:
        project = await self.repository.get_project(principal.tenant_id, project_id)
        return project is not None and can_access_project(principal, project)
