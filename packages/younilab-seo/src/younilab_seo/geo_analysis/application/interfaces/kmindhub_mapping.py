from datetime import datetime
from typing import Protocol, runtime_checkable
from uuid import UUID

from younilab_seo.geo_analysis.application.contracts import (
    GeoRunResultAnalysisRecord,
    GeoRunResultRecord,
    KMindHubExtractionTaskMappingCommand,
    KMindHubExtractionTaskMappingRecord,
    KMindHubWorkspaceMappingCommand,
    KMindHubWorkspaceMappingRecord,
    SaveRunResultAnalysisCommand,
)


@runtime_checkable
class KMindHubWorkspaceMappingPersistence(Protocol):
    """管理 tenant 對 KMindHub workspace mapping 的 persistence interface。"""

    async def get_kmindhub_workspace_mapping(
        self,
        tenant_id: UUID,
    ) -> KMindHubWorkspaceMappingRecord | None: ...

    async def upsert_kmindhub_workspace_mapping(
        self,
        tenant_id: UUID,
        command: KMindHubWorkspaceMappingCommand,
    ) -> KMindHubWorkspaceMappingRecord: ...


@runtime_checkable
class KMindHubTaskMappingPersistence(Protocol):
    """管理 versioned KMindHub extraction task mapping 的 persistence interface。"""

    async def get_kmindhub_extraction_task_mapping(
        self,
        tenant_id: UUID,
        task_key: str,
        schema_version: int,
    ) -> KMindHubExtractionTaskMappingRecord | None: ...

    async def upsert_kmindhub_extraction_task_mapping(
        self,
        tenant_id: UUID,
        command: KMindHubExtractionTaskMappingCommand,
    ) -> KMindHubExtractionTaskMappingRecord: ...


@runtime_checkable
class LegacyAnalysisExtractionPersistence(
    KMindHubTaskMappingPersistence,
    Protocol,
):
    """Legacy KMindHub extraction 讀取 raw result 與保存 analysis 的介面。"""

    async def get_run_result(
        self,
        tenant_id: UUID,
        result_id: UUID,
    ) -> GeoRunResultRecord | None: ...

    async def save_run_result_analysis(
        self,
        tenant_id: UUID,
        command: SaveRunResultAnalysisCommand,
        occurred_at: datetime,
    ) -> GeoRunResultAnalysisRecord | None: ...
