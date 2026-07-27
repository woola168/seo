from typing import Protocol, runtime_checkable
from uuid import UUID

from younilab_seo.geo_analysis.application.contracts import (
    GeoAiPlatformRecord,
    GeoProjectRecord,
    GeoQueryCommand,
    GeoQueryPlatformCommand,
    GeoQueryPlatformRecord,
    GeoQueryRecord,
    GeoQueryScheduleCommand,
    GeoQueryScheduleRecord,
    GeoTopicCommand,
    GeoTopicRecord,
)


@runtime_checkable
class QueryCatalogPersistence(Protocol):
    """管理 topic、query、platform assignment 與 schedule 的介面。"""

    async def get_topic_project(
        self,
        tenant_id: UUID,
        topic_id: UUID,
    ) -> GeoProjectRecord | None: ...

    async def get_query_project(
        self,
        tenant_id: UUID,
        query_id: UUID,
    ) -> GeoProjectRecord | None: ...

    async def get_schedule_project(
        self,
        tenant_id: UUID,
        schedule_id: UUID,
    ) -> GeoProjectRecord | None: ...

    async def list_topics(
        self,
        tenant_id: UUID,
        project_id: UUID,
    ) -> list[GeoTopicRecord]: ...

    async def create_topic(
        self,
        tenant_id: UUID,
        project_id: UUID,
        command: GeoTopicCommand,
    ) -> GeoTopicRecord | None: ...

    async def update_topic(
        self,
        tenant_id: UUID,
        topic_id: UUID,
        command: GeoTopicCommand,
    ) -> GeoTopicRecord | None: ...

    async def delete_topic(self, tenant_id: UUID, topic_id: UUID) -> bool: ...

    async def list_queries(
        self,
        tenant_id: UUID,
        project_id: UUID,
    ) -> list[GeoQueryRecord]: ...

    async def get_query(
        self,
        tenant_id: UUID,
        query_id: UUID,
    ) -> GeoQueryRecord | None: ...

    async def create_query(
        self,
        tenant_id: UUID,
        project_id: UUID,
        command: GeoQueryCommand,
    ) -> GeoQueryRecord | None: ...

    async def update_query(
        self,
        tenant_id: UUID,
        query_id: UUID,
        command: GeoQueryCommand,
    ) -> GeoQueryRecord | None: ...

    async def delete_query(self, tenant_id: UUID, query_id: UUID) -> bool: ...

    async def list_ai_platforms(self) -> list[GeoAiPlatformRecord]: ...

    async def list_query_platforms(
        self,
        tenant_id: UUID,
        query_id: UUID,
    ) -> list[GeoQueryPlatformRecord]: ...

    async def list_project_query_platforms(
        self,
        tenant_id: UUID,
        project_id: UUID,
    ) -> list[GeoQueryPlatformRecord]: ...

    async def replace_query_platforms(
        self,
        tenant_id: UUID,
        query_id: UUID,
        commands: list[GeoQueryPlatformCommand],
    ) -> list[GeoQueryPlatformRecord] | None: ...

    async def list_schedules(
        self,
        tenant_id: UUID,
        query_id: UUID,
    ) -> list[GeoQueryScheduleRecord]: ...

    async def list_project_schedules(
        self,
        tenant_id: UUID,
        project_id: UUID,
    ) -> list[GeoQueryScheduleRecord]: ...

    async def create_schedule(
        self,
        tenant_id: UUID,
        query_id: UUID,
        command: GeoQueryScheduleCommand,
    ) -> GeoQueryScheduleRecord | None: ...

    async def update_schedule(
        self,
        tenant_id: UUID,
        schedule_id: UUID,
        command: GeoQueryScheduleCommand,
    ) -> GeoQueryScheduleRecord | None: ...

    async def delete_schedule(self, tenant_id: UUID, schedule_id: UUID) -> bool: ...
