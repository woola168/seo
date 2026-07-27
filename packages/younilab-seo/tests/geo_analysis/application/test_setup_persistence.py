import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from younilab_seo.geo_analysis.application import (
    AuthorizedPrincipal,
    EntityCatalogPersistence,
    GeoProjectRecord,
    ManageGeoSetup,
    ProjectSetupPersistence,
    QueryCatalogPersistence,
)

TENANT_ID = UUID("00000000-0000-4000-8000-000000000001")
PROJECT_ID = UUID("00000000-0000-4000-8000-000000000002")
NOW = datetime(2026, 7, 27, tzinfo=UTC)


@dataclass
class FakeProjectSetupPersistence:
    project_calls: int = 0

    async def list_projects(self, tenant_id, customer_id=None):
        self.project_calls += 1
        return [_project()]

    async def get_project(self, tenant_id, project_id):
        self.project_calls += 1
        if tenant_id == TENANT_ID and project_id == PROJECT_ID:
            return _project()
        return None


@dataclass
class FakeEntityCatalogPersistence:
    calls: int = 0

    async def list_entities(self, tenant_id, project_id):
        self.calls += 1
        return []


@dataclass
class FakeQueryCatalogPersistence:
    calls: int = 0

    async def list_topics(self, tenant_id, project_id):
        self.calls += 1
        return []


def test_setup_routes_each_catalog_to_its_own_persistence_port() -> None:
    async def run() -> None:
        project: ProjectSetupPersistence = FakeProjectSetupPersistence()
        entities: EntityCatalogPersistence = FakeEntityCatalogPersistence()
        queries: QueryCatalogPersistence = FakeQueryCatalogPersistence()
        setup = ManageGeoSetup(
            project,
            entity_persistence=entities,
            query_catalog_persistence=queries,
        )
        principal = _principal()

        await setup.list_projects(principal)
        await setup.list_entities(principal, PROJECT_ID)
        await setup.list_topics(principal, PROJECT_ID)

        assert project.project_calls == 3
        assert entities.calls == 1
        assert queries.calls == 1

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
