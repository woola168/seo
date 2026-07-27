from typing import Protocol, runtime_checkable
from uuid import UUID

from younilab_seo.geo_analysis.application.contracts import (
    GeoMarketCommand,
    GeoMarketRecord,
    GeoProjectCommand,
    GeoProjectQuerySettingsCommand,
    GeoProjectQuerySettingsRecord,
    GeoProjectRecord,
    GeoProjectStatusCommand,
    GeoProjectSummaryRecord,
)


@runtime_checkable
class ProjectSetupPersistence(Protocol):
    """管理 project、market 與 query settings 的 persistence interface。"""

    async def list_projects(
        self,
        tenant_id: UUID,
        customer_id: UUID | None = None,
    ) -> list[GeoProjectRecord]: ...

    async def list_project_summaries(
        self,
        tenant_id: UUID,
        customer_id: UUID | None = None,
    ) -> list[GeoProjectSummaryRecord]: ...

    async def get_project(
        self,
        tenant_id: UUID,
        project_id: UUID,
    ) -> GeoProjectRecord | None: ...

    async def create_project(self, command: GeoProjectCommand) -> GeoProjectRecord: ...

    async def update_project(
        self,
        tenant_id: UUID,
        project_id: UUID,
        command: GeoProjectCommand,
    ) -> GeoProjectRecord | None: ...

    async def delete_project(self, tenant_id: UUID, project_id: UUID) -> bool: ...

    async def update_project_status(
        self,
        tenant_id: UUID,
        project_id: UUID,
        command: GeoProjectStatusCommand,
    ) -> GeoProjectRecord | None: ...

    async def get_project_query_settings(
        self,
        tenant_id: UUID,
        project_id: UUID,
    ) -> GeoProjectQuerySettingsRecord | None: ...

    async def upsert_project_query_settings(
        self,
        tenant_id: UUID,
        project_id: UUID,
        command: GeoProjectQuerySettingsCommand,
    ) -> GeoProjectQuerySettingsRecord | None: ...

    async def get_market_project(
        self,
        tenant_id: UUID,
        market_id: UUID,
    ) -> GeoProjectRecord | None: ...

    async def list_markets(
        self,
        tenant_id: UUID,
        project_id: UUID,
    ) -> list[GeoMarketRecord]: ...

    async def create_market(
        self,
        tenant_id: UUID,
        project_id: UUID,
        command: GeoMarketCommand,
    ) -> GeoMarketRecord | None: ...

    async def update_market(
        self,
        tenant_id: UUID,
        market_id: UUID,
        command: GeoMarketCommand,
    ) -> GeoMarketRecord | None: ...

    async def delete_market(self, tenant_id: UUID, market_id: UUID) -> bool: ...
