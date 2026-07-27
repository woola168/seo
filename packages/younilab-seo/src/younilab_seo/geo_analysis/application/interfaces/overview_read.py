from datetime import date
from typing import Protocol, runtime_checkable
from uuid import UUID

from younilab_seo.geo_analysis.application.contracts import (
    GeoQueryRecord,
    GeoRunResultRecord,
    GeoTopicRecord,
)


@runtime_checkable
class OverviewReadPersistence(Protocol):
    """載入 Overview filters、準備狀態與 response page 所需資料。"""

    async def list_queries(
        self,
        tenant_id: UUID,
        project_id: UUID,
    ) -> list[GeoQueryRecord]: ...

    async def list_topics(
        self,
        tenant_id: UUID,
        project_id: UUID,
    ) -> list[GeoTopicRecord]: ...

    async def is_project_data_preparing(
        self,
        tenant_id: UUID,
        project_id: UUID,
        business_date: date,
    ) -> bool: ...

    async def list_project_run_results(
        self,
        tenant_id: UUID,
        project_id: UUID,
    ) -> list[GeoRunResultRecord]: ...
