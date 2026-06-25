from datetime import datetime
from typing import Protocol, runtime_checkable
from uuid import UUID

from younilab_seo.geo_analysis.application.contracts import (
    CreateQueryRunJobCommand,
    ExternalRunCallback,
    GeoEntityAliasCommand,
    GeoEntityAliasRecord,
    GeoEntityCommand,
    GeoEntityRecord,
    GeoMarketCommand,
    GeoMarketRecord,
    GeoProjectCommand,
    GeoProjectRecord,
    GeoQueryCommand,
    GeoQueryPlatformCommand,
    GeoQueryPlatformRecord,
    GeoQueryRecord,
    GeoQueryRunJobDispatchContext,
    GeoQueryScheduleCommand,
    GeoQueryScheduleRecord,
    GeoTopicCommand,
    GeoTopicRecord,
    PublishResult,
    QueryRunJobMessage,
)
from younilab_seo.geo_analysis.domain import GeoQueryRunJob


class Clock(Protocol):
    """讓 use case 取得可測試的目前時間。"""

    def now(self) -> datetime:
        raise NotImplementedError


class IdGenerator(Protocol):
    """跨 boundary 建立 orchestration record id 的抽象。"""

    def new_id(self) -> UUID:
        raise NotImplementedError


class MessagePublisher(Protocol):
    """將 GEO query run job 發送到 message broker 的 port。"""

    async def publish(self, message: QueryRunJobMessage) -> PublishResult:
        raise NotImplementedError


@runtime_checkable
class GeoQueryRunJobRepository(Protocol):
    """query run job lifecycle 與派送 evidence 的 persistence port。"""

    async def get(self, job_id: UUID) -> GeoQueryRunJob:
        raise NotImplementedError

    async def save(self, job: GeoQueryRunJob) -> None:
        raise NotImplementedError

    async def record_dispatch(
        self,
        *,
        job_id: UUID,
        result: PublishResult,
        payload: QueryRunJobMessage,
        occurred_at: datetime,
    ) -> None:
        raise NotImplementedError

    async def record_external_callback(
        self,
        *,
        callback: ExternalRunCallback,
        occurred_at: datetime,
    ) -> None:
        raise NotImplementedError

    async def get_job_dispatch_context(
        self,
        job_id: UUID,
    ) -> GeoQueryRunJobDispatchContext | None:
        raise NotImplementedError

    async def apply_external_callback(
        self,
        *,
        callback: ExternalRunCallback,
        occurred_at: datetime,
    ) -> GeoQueryRunJob:
        raise NotImplementedError


@runtime_checkable
class GeoAnalysisRepository(GeoQueryRunJobRepository, Protocol):
    """GEO setup 與 query run job orchestration 的 application repository port。"""

    async def list_projects(self, customer_id: UUID | None = None) -> list[GeoProjectRecord]:
        raise NotImplementedError

    async def get_project(self, project_id: UUID) -> GeoProjectRecord | None:
        raise NotImplementedError

    async def create_project(self, command: GeoProjectCommand) -> GeoProjectRecord:
        raise NotImplementedError

    async def update_project(
        self,
        project_id: UUID,
        command: GeoProjectCommand,
    ) -> GeoProjectRecord | None:
        raise NotImplementedError

    async def delete_project(self, project_id: UUID) -> bool:
        raise NotImplementedError

    async def list_markets(self, project_id: UUID) -> list[GeoMarketRecord]:
        raise NotImplementedError

    async def create_market(
        self,
        project_id: UUID,
        command: GeoMarketCommand,
    ) -> GeoMarketRecord | None:
        raise NotImplementedError

    async def update_market(
        self,
        market_id: UUID,
        command: GeoMarketCommand,
    ) -> GeoMarketRecord | None:
        raise NotImplementedError

    async def delete_market(self, market_id: UUID) -> bool:
        raise NotImplementedError

    async def list_entities(self, project_id: UUID) -> list[GeoEntityRecord]:
        raise NotImplementedError

    async def get_entity(self, entity_id: UUID) -> GeoEntityRecord | None:
        raise NotImplementedError

    async def create_entity(
        self,
        project_id: UUID,
        command: GeoEntityCommand,
    ) -> GeoEntityRecord | None:
        raise NotImplementedError

    async def update_entity(
        self,
        entity_id: UUID,
        command: GeoEntityCommand,
    ) -> GeoEntityRecord | None:
        raise NotImplementedError

    async def delete_entity(self, entity_id: UUID) -> bool:
        raise NotImplementedError

    async def list_aliases(self, entity_id: UUID) -> list[GeoEntityAliasRecord]:
        raise NotImplementedError

    async def create_alias(
        self,
        entity_id: UUID,
        command: GeoEntityAliasCommand,
    ) -> GeoEntityAliasRecord | None:
        raise NotImplementedError

    async def update_alias(
        self,
        alias_id: UUID,
        command: GeoEntityAliasCommand,
    ) -> GeoEntityAliasRecord | None:
        raise NotImplementedError

    async def delete_alias(self, alias_id: UUID) -> bool:
        raise NotImplementedError

    async def list_topics(self, project_id: UUID) -> list[GeoTopicRecord]:
        raise NotImplementedError

    async def create_topic(
        self,
        project_id: UUID,
        command: GeoTopicCommand,
    ) -> GeoTopicRecord | None:
        raise NotImplementedError

    async def update_topic(
        self,
        topic_id: UUID,
        command: GeoTopicCommand,
    ) -> GeoTopicRecord | None:
        raise NotImplementedError

    async def delete_topic(self, topic_id: UUID) -> bool:
        raise NotImplementedError

    async def list_queries(self, project_id: UUID) -> list[GeoQueryRecord]:
        raise NotImplementedError

    async def get_query(self, query_id: UUID) -> GeoQueryRecord | None:
        raise NotImplementedError

    async def create_query(
        self,
        project_id: UUID,
        command: GeoQueryCommand,
    ) -> GeoQueryRecord | None:
        raise NotImplementedError

    async def update_query(
        self,
        query_id: UUID,
        command: GeoQueryCommand,
    ) -> GeoQueryRecord | None:
        raise NotImplementedError

    async def delete_query(self, query_id: UUID) -> bool:
        raise NotImplementedError

    async def list_query_platforms(self, query_id: UUID) -> list[GeoQueryPlatformRecord]:
        raise NotImplementedError

    async def replace_query_platforms(
        self,
        query_id: UUID,
        commands: list[GeoQueryPlatformCommand],
    ) -> list[GeoQueryPlatformRecord] | None:
        raise NotImplementedError

    async def list_schedules(self, query_id: UUID) -> list[GeoQueryScheduleRecord]:
        raise NotImplementedError

    async def create_schedule(
        self,
        query_id: UUID,
        command: GeoQueryScheduleCommand,
    ) -> GeoQueryScheduleRecord | None:
        raise NotImplementedError

    async def update_schedule(
        self,
        schedule_id: UUID,
        command: GeoQueryScheduleCommand,
    ) -> GeoQueryScheduleRecord | None:
        raise NotImplementedError

    async def delete_schedule(self, schedule_id: UUID) -> bool:
        raise NotImplementedError

    async def create_job(
        self,
        query_id: UUID,
        command: CreateQueryRunJobCommand,
    ) -> GeoQueryRunJob | None:
        raise NotImplementedError

    async def list_jobs(self, project_id: UUID) -> list[GeoQueryRunJob]:
        raise NotImplementedError

    async def get_job(self, job_id: UUID) -> GeoQueryRunJob | None:
        raise NotImplementedError
