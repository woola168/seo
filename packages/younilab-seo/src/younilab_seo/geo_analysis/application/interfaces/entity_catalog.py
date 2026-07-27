from typing import Protocol, runtime_checkable
from uuid import UUID

from younilab_seo.geo_analysis.application.contracts import (
    GeoEntityAliasCommand,
    GeoEntityAliasRecord,
    GeoEntityCommand,
    GeoEntityRecord,
    GeoProjectRecord,
)


@runtime_checkable
class EntityCatalogPersistence(Protocol):
    """管理 own brand、competitor 與 alias 的 persistence interface。"""

    async def get_entity_project(
        self,
        tenant_id: UUID,
        entity_id: UUID,
    ) -> GeoProjectRecord | None: ...

    async def list_entities(
        self,
        tenant_id: UUID,
        project_id: UUID,
    ) -> list[GeoEntityRecord]: ...

    async def get_entity(
        self,
        tenant_id: UUID,
        entity_id: UUID,
    ) -> GeoEntityRecord | None: ...

    async def create_entity(
        self,
        tenant_id: UUID,
        project_id: UUID,
        command: GeoEntityCommand,
    ) -> GeoEntityRecord | None: ...

    async def update_entity(
        self,
        tenant_id: UUID,
        entity_id: UUID,
        command: GeoEntityCommand,
    ) -> GeoEntityRecord | None: ...

    async def delete_entity(self, tenant_id: UUID, entity_id: UUID) -> bool: ...

    async def list_aliases(
        self,
        tenant_id: UUID,
        entity_id: UUID,
    ) -> list[GeoEntityAliasRecord]: ...

    async def list_project_aliases(
        self,
        tenant_id: UUID,
        project_id: UUID,
    ) -> list[GeoEntityAliasRecord]: ...

    async def replace_aliases(
        self,
        tenant_id: UUID,
        entity_id: UUID,
        commands: list[GeoEntityAliasCommand],
    ) -> list[GeoEntityAliasRecord] | None: ...
