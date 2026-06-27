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
    Clock,
    GeoAnalysisRepository,
    QueryPlanningClient,
)


class GeoProjectReferenceError(ValueError):
    pass


@dataclass(frozen=True)
class ManageQueryPlanning:
    repository: GeoAnalysisRepository
    planning_client: QueryPlanningClient
    clock: Clock

    async def run_query_research(
        self,
        project_id: UUID,
        command: QueryResearchCommand,
    ) -> QueryResearchRunRecord | None:
        if await self.repository.get_project(project_id) is None:
            return None
        request_payload = command.model_dump(mode="json", by_alias=True)
        try:
            result = await self.planning_client.research(command)
            return await self.repository.create_query_research_run(
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
        project_id: UUID,
    ) -> list[QueryResearchRunRecord]:
        return await self.repository.list_query_research_runs(project_id)

    async def get_query_research_run(
        self,
        run_id: UUID,
    ) -> QueryResearchRunRecord | None:
        return await self.repository.get_query_research_run(run_id)

    async def run_query_generation(
        self,
        project_id: UUID,
        command: QueryGenerationCommand,
    ) -> QueryGenerationRunRecord | None:
        if await self.repository.get_project(project_id) is None:
            return None
        request_payload = command.model_dump(mode="json", by_alias=True)
        try:
            result = await self.planning_client.generate(command)
            return await self.repository.create_query_generation_run(
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
        project_id: UUID,
    ) -> list[QueryGenerationRunRecord]:
        return await self.repository.list_query_generation_runs(project_id)

    async def get_query_generation_run(
        self,
        run_id: UUID,
    ) -> QueryGenerationRunRecord | None:
        return await self.repository.get_query_generation_run(run_id)

    async def update_query_draft_selection(
        self,
        draft_id: UUID,
        command: QueryDraftSelectionCommand,
    ) -> QueryDraftRecord | None:
        if command.selection_status not in {"shortlisted", "rejected"}:
            raise ValueError("selectionStatus must be shortlisted or rejected")
        return await self.repository.update_query_draft_selection(draft_id, command)

    async def accept_query_draft(
        self,
        draft_id: UUID,
        command: AcceptQueryDraftCommand,
    ) -> GeoQueryRecord | None:
        return await self.repository.accept_query_draft(draft_id, command)
