from dataclasses import dataclass
from uuid import UUID

from younilab_seo.geo_analysis.application.contracts import (
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
    GeoQueryScheduleCommand,
    GeoQueryScheduleRecord,
    GeoTopicCommand,
    GeoTopicRecord,
)
from younilab_seo.geo_analysis.application.interfaces import GeoAnalysisRepository


@dataclass(frozen=True)
class ManageGeoSetup:
    """管理 GEO project setup、tracked query 與 schedule metadata。"""

    repository: GeoAnalysisRepository

    async def list_projects(self, customer_id: UUID | None = None) -> list[GeoProjectRecord]:
        return await self.repository.list_projects(customer_id)

    async def get_project(self, project_id: UUID) -> GeoProjectRecord | None:
        return await self.repository.get_project(project_id)

    async def create_project(self, command: GeoProjectCommand) -> GeoProjectRecord:
        return await self.repository.create_project(command)

    async def update_project(
        self,
        project_id: UUID,
        command: GeoProjectCommand,
    ) -> GeoProjectRecord | None:
        return await self.repository.update_project(project_id, command)

    async def delete_project(self, project_id: UUID) -> bool:
        return await self.repository.delete_project(project_id)

    async def list_markets(self, project_id: UUID) -> list[GeoMarketRecord]:
        return await self.repository.list_markets(project_id)

    async def create_market(
        self,
        project_id: UUID,
        command: GeoMarketCommand,
    ) -> GeoMarketRecord | None:
        return await self.repository.create_market(project_id, command)

    async def update_market(
        self,
        market_id: UUID,
        command: GeoMarketCommand,
    ) -> GeoMarketRecord | None:
        return await self.repository.update_market(market_id, command)

    async def delete_market(self, market_id: UUID) -> bool:
        return await self.repository.delete_market(market_id)

    async def list_entities(self, project_id: UUID) -> list[GeoEntityRecord]:
        return await self.repository.list_entities(project_id)

    async def get_entity(self, entity_id: UUID) -> GeoEntityRecord | None:
        return await self.repository.get_entity(entity_id)

    async def create_entity(
        self,
        project_id: UUID,
        command: GeoEntityCommand,
    ) -> GeoEntityRecord | None:
        return await self.repository.create_entity(project_id, command)

    async def update_entity(
        self,
        entity_id: UUID,
        command: GeoEntityCommand,
    ) -> GeoEntityRecord | None:
        return await self.repository.update_entity(entity_id, command)

    async def delete_entity(self, entity_id: UUID) -> bool:
        return await self.repository.delete_entity(entity_id)

    async def list_aliases(self, entity_id: UUID) -> list[GeoEntityAliasRecord]:
        return await self.repository.list_aliases(entity_id)

    async def create_alias(
        self,
        entity_id: UUID,
        command: GeoEntityAliasCommand,
    ) -> GeoEntityAliasRecord | None:
        return await self.repository.create_alias(entity_id, command)

    async def update_alias(
        self,
        alias_id: UUID,
        command: GeoEntityAliasCommand,
    ) -> GeoEntityAliasRecord | None:
        return await self.repository.update_alias(alias_id, command)

    async def delete_alias(self, alias_id: UUID) -> bool:
        return await self.repository.delete_alias(alias_id)

    async def list_topics(self, project_id: UUID) -> list[GeoTopicRecord]:
        return await self.repository.list_topics(project_id)

    async def create_topic(
        self,
        project_id: UUID,
        command: GeoTopicCommand,
    ) -> GeoTopicRecord | None:
        return await self.repository.create_topic(project_id, command)

    async def update_topic(
        self,
        topic_id: UUID,
        command: GeoTopicCommand,
    ) -> GeoTopicRecord | None:
        return await self.repository.update_topic(topic_id, command)

    async def delete_topic(self, topic_id: UUID) -> bool:
        return await self.repository.delete_topic(topic_id)

    async def list_queries(self, project_id: UUID) -> list[GeoQueryRecord]:
        return await self.repository.list_queries(project_id)

    async def get_query(self, query_id: UUID) -> GeoQueryRecord | None:
        return await self.repository.get_query(query_id)

    async def create_query(
        self,
        project_id: UUID,
        command: GeoQueryCommand,
    ) -> GeoQueryRecord | None:
        return await self.repository.create_query(project_id, command)

    async def update_query(
        self,
        query_id: UUID,
        command: GeoQueryCommand,
    ) -> GeoQueryRecord | None:
        return await self.repository.update_query(query_id, command)

    async def delete_query(self, query_id: UUID) -> bool:
        return await self.repository.delete_query(query_id)

    async def list_query_platforms(self, query_id: UUID) -> list[GeoQueryPlatformRecord]:
        return await self.repository.list_query_platforms(query_id)

    async def replace_query_platforms(
        self,
        query_id: UUID,
        commands: list[GeoQueryPlatformCommand],
    ) -> list[GeoQueryPlatformRecord] | None:
        return await self.repository.replace_query_platforms(query_id, commands)

    async def list_schedules(self, query_id: UUID) -> list[GeoQueryScheduleRecord]:
        return await self.repository.list_schedules(query_id)

    async def create_schedule(
        self,
        query_id: UUID,
        command: GeoQueryScheduleCommand,
    ) -> GeoQueryScheduleRecord | None:
        return await self.repository.create_schedule(query_id, command)

    async def update_schedule(
        self,
        schedule_id: UUID,
        command: GeoQueryScheduleCommand,
    ) -> GeoQueryScheduleRecord | None:
        return await self.repository.update_schedule(schedule_id, command)

    async def delete_schedule(self, schedule_id: UUID) -> bool:
        return await self.repository.delete_schedule(schedule_id)
