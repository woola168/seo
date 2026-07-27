from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, runtime_checkable
from uuid import UUID

from younilab_seo.geo_analysis.application.contracts import (
    GeoRunResultCitationNormalization,
    GeoRunResultRecord,
    SaveRunResultCitationNormalizationCommand,
)


@dataclass(frozen=True)
class CitationNormalizationContext:
    """單筆 run result 進行 citation normalization 所需的 persistence context。"""

    run_result: GeoRunResultRecord
    project_id: UUID | None = None
    owned_website_urls: tuple[str, ...] = ()


@runtime_checkable
class CitationNormalizationPersistence(Protocol):
    """載入與保存單筆 citation normalization workflow 的 persistence interface。"""

    async def load_citation_normalization_context(
        self,
        tenant_id: UUID,
        run_result_id: UUID,
    ) -> CitationNormalizationContext | None: ...

    async def get_existing_citation_normalization(
        self,
        tenant_id: UUID,
        run_result_id: UUID,
        normalizer_version: str,
    ) -> GeoRunResultCitationNormalization | None: ...

    async def save_citation_normalization(
        self,
        tenant_id: UUID,
        command: SaveRunResultCitationNormalizationCommand,
        occurred_at: datetime,
    ) -> GeoRunResultCitationNormalization | None: ...
