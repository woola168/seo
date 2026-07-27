import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from younilab_seo.geo_analysis.application import (
    AuthorizedPrincipal,
    GeoProjectRecord,
    ManageQueryPlanning,
    QueryPlanningPersistence,
    QueryResearchCommand,
    QueryResearchRunRecord,
)

TENANT_ID = UUID("00000000-0000-4000-8000-000000000001")
PROJECT_ID = UUID("00000000-0000-4000-8000-000000000002")
RUN_ID = UUID("00000000-0000-4000-8000-000000000003")
NOW = datetime(2026, 7, 27, tzinfo=UTC)


@dataclass
class FakeClock:
    def now(self) -> datetime:
        return NOW


@dataclass
class FakePlanningClient:
    async def research(self, command: QueryResearchCommand) -> dict:
        return {
            "researchContext": "採購方重視供應商導入能力。",
            "searchedKeywords": ["ERP 導入"],
            "sourceUrls": ["https://example.test/erp"],
        }


@dataclass
class FakePlanningPersistence:
    project: GeoProjectRecord
    saved: tuple | None = None

    async def get_project(self, tenant_id: UUID, project_id: UUID):
        if tenant_id == TENANT_ID and project_id == PROJECT_ID:
            return self.project
        return None

    async def create_query_research_run(
        self,
        tenant_id,
        project_id,
        command,
        request_payload,
        result,
        status,
        error_message,
        occurred_at,
    ):
        self.saved = (
            tenant_id,
            project_id,
            command,
            request_payload,
            result,
            status,
            error_message,
            occurred_at,
        )
        return QueryResearchRunRecord(
            id=RUN_ID,
            projectId=project_id,
            provider=command.provider,
            status=status,
            requestPayload=request_payload,
            result=result,
            errorMessage=error_message,
            createdAt=occurred_at,
            completedAt=occurred_at,
        )


def test_query_research_uses_planning_persistence_without_mega_repository() -> None:
    async def run() -> None:
        repository: QueryPlanningPersistence = FakePlanningPersistence(_project())
        command = QueryResearchCommand(
            provider="gemini",
            brandName="Acme",
            keywords=["ERP 導入"],
            region="TW",
            language="zh-TW",
        )

        result = await ManageQueryPlanning(
            repository,
            FakePlanningClient(),
            FakeClock(),
        ).run_query_research(_principal(), PROJECT_ID, command)

        assert result is not None
        assert result.status == "completed"
        assert repository.saved is not None
        assert repository.saved[4]["researchContext"] == "採購方重視供應商導入能力。"

    asyncio.run(run())


def _project() -> GeoProjectRecord:
    return GeoProjectRecord(
        id=PROJECT_ID,
        tenantId=TENANT_ID,
        name="Acme GEO",
        createdAt=NOW,
        updatedAt=NOW,
    )


def _principal() -> AuthorizedPrincipal:
    return AuthorizedPrincipal(
        tenant_id=TENANT_ID,
        permissions=frozenset(),
        has_global_resource_access=True,
        customer_ids=frozenset(),
        task_ids=frozenset(),
    )
