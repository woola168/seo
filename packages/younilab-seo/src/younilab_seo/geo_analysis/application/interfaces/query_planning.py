from datetime import datetime
from typing import Protocol, runtime_checkable
from uuid import UUID

from younilab_seo.geo_analysis.application.contracts import (
    AcceptQueryDraftCommand,
    GeoProjectRecord,
    GeoQueryRecord,
    QueryDraftRecord,
    QueryDraftSelectionCommand,
    QueryGenerationCommand,
    QueryGenerationRunRecord,
    QueryResearchCommand,
    QueryResearchRunRecord,
)


@runtime_checkable
class QueryPlanningPersistence(Protocol):
    """保存 research、generation 與 draft acceptance workflow 的介面。"""

    async def get_project(
        self,
        tenant_id: UUID,
        project_id: UUID,
    ) -> GeoProjectRecord | None: ...

    async def get_query_research_run_project(
        self,
        tenant_id: UUID,
        run_id: UUID,
    ) -> GeoProjectRecord | None: ...

    async def get_query_generation_run_project(
        self,
        tenant_id: UUID,
        run_id: UUID,
    ) -> GeoProjectRecord | None: ...

    async def get_query_draft_project(
        self,
        tenant_id: UUID,
        draft_id: UUID,
    ) -> GeoProjectRecord | None: ...

    async def create_query_research_run(
        self,
        tenant_id: UUID,
        project_id: UUID,
        command: QueryResearchCommand,
        request_payload: dict,
        result: dict | None,
        status: str,
        error_message: str | None,
        occurred_at: datetime,
    ) -> QueryResearchRunRecord | None: ...

    async def list_query_research_runs(
        self,
        tenant_id: UUID,
        project_id: UUID,
    ) -> list[QueryResearchRunRecord]: ...

    async def get_query_research_run(
        self,
        tenant_id: UUID,
        run_id: UUID,
    ) -> QueryResearchRunRecord | None: ...

    async def create_query_generation_run(
        self,
        tenant_id: UUID,
        project_id: UUID,
        command: QueryGenerationCommand,
        request_payload: dict,
        result: dict | None,
        status: str,
        error_message: str | None,
        occurred_at: datetime,
    ) -> QueryGenerationRunRecord | None: ...

    async def list_query_generation_runs(
        self,
        tenant_id: UUID,
        project_id: UUID,
    ) -> list[QueryGenerationRunRecord]: ...

    async def get_query_generation_run(
        self,
        tenant_id: UUID,
        run_id: UUID,
    ) -> QueryGenerationRunRecord | None: ...

    async def update_query_draft_selection(
        self,
        tenant_id: UUID,
        draft_id: UUID,
        command: QueryDraftSelectionCommand,
    ) -> QueryDraftRecord | None: ...

    async def accept_query_draft(
        self,
        tenant_id: UUID,
        draft_id: UUID,
        command: AcceptQueryDraftCommand,
    ) -> GeoQueryRecord | None: ...
