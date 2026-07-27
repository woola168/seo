from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, runtime_checkable
from uuid import UUID

from younilab_seo.geo_analysis.application.contracts import (
    GeoEntityAliasRecord,
    GeoEntityRecord,
    GeoQueryRecord,
    GeoRunResultAnalysis,
    GeoRunResultEntityDetection,
    GeoRunResultRecord,
    GeoTopicRecord,
    SaveRunResultEntityDetectionCommand,
    SaveSemanticRunResultAnalysisCommand,
)


@dataclass(frozen=True)
class SemanticAnalysisContext:
    """單筆 run result 進行 semantic analysis 所需的已篩選 persistence context。"""

    run_result: GeoRunResultRecord
    query: GeoQueryRecord | None = None
    topic: GeoTopicRecord | None = None
    own_brand: GeoEntityRecord | None = None
    competitors: tuple[GeoEntityRecord, ...] = ()
    aliases: tuple[GeoEntityAliasRecord, ...] = ()


@runtime_checkable
class SemanticAnalysisPersistence(Protocol):
    """載入與保存單筆 semantic analysis workflow 的 persistence interface。"""

    async def load_semantic_analysis_context(
        self,
        tenant_id: UUID,
        run_result_id: UUID,
    ) -> SemanticAnalysisContext | None: ...

    async def get_existing_semantic_analysis(
        self,
        tenant_id: UUID,
        run_result_id: UUID,
    ) -> GeoRunResultAnalysis | None: ...

    async def save_semantic_entity_detection(
        self,
        tenant_id: UUID,
        command: SaveRunResultEntityDetectionCommand,
        occurred_at: datetime,
    ) -> GeoRunResultEntityDetection | None: ...

    async def save_semantic_analysis(
        self,
        tenant_id: UUID,
        command: SaveSemanticRunResultAnalysisCommand,
        occurred_at: datetime,
    ) -> GeoRunResultAnalysis | None: ...
