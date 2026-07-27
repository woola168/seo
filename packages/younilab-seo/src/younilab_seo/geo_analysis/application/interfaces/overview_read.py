from datetime import date
from typing import Protocol, runtime_checkable
from uuid import UUID

from younilab_seo.geo_analysis.application.contracts import (
    GeoOverviewQuery,
    GeoOverviewReportSource,
    GeoOverviewResponsePage,
    GeoOverviewResponsePageQuery,
)


@runtime_checkable
class OverviewReportReadModel(Protocol):
    """一次載入 Overview 報表所需的 filtered read source。"""

    async def load_overview_report_source(
        self,
        tenant_id: UUID,
        project_id: UUID,
        query: GeoOverviewQuery,
        business_date: date,
        normalizer_version: str,
    ) -> GeoOverviewReportSource | None: ...


@runtime_checkable
class OverviewResponseReadModel(Protocol):
    """回傳已篩選、排序並分頁的 Overview 回答摘要。"""

    async def load_overview_response_page(
        self,
        tenant_id: UUID,
        project_id: UUID,
        query: GeoOverviewResponsePageQuery,
    ) -> GeoOverviewResponsePage | None: ...
