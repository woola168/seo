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
from younilab_seo.geo_analysis.application.interfaces import (
    AuthorizedPrincipal,
    GeoAnalysisRepository,
    ResourceCatalogReferenceVerifier,
)
from younilab_seo.geo_analysis.application.use_cases.access_policy import (
    can_access_project,
    filter_accessible_projects,
)
from younilab_seo.geo_analysis.application.use_cases.planning import (
    GeoProjectReferenceError,
)


@dataclass(frozen=True)
class ManageGeoSetup:
    """管理 GEO project setup 資料，並套用 tenant 與 resource grant 邊界。"""

    repository: GeoAnalysisRepository
    reference_verifier: ResourceCatalogReferenceVerifier | None = None

    async def list_projects(
        self,
        principal: AuthorizedPrincipal,
        customer_id: UUID | None = None,
    ) -> list[GeoProjectRecord]:
        projects = await self.repository.list_projects(principal.tenant_id, customer_id)
        return filter_accessible_projects(principal, projects)

    async def get_project(
        self,
        principal: AuthorizedPrincipal,
        project_id: UUID,
    ) -> GeoProjectRecord | None:
        project = await self.repository.get_project(principal.tenant_id, project_id)
        if project is None or not can_access_project(principal, project):
            return None
        return project

    async def create_project(
        self,
        command: GeoProjectCommand,
        principal: AuthorizedPrincipal,
        access_token: str | None = None,
    ) -> GeoProjectRecord:
        if command.tenant_id != principal.tenant_id:
            raise GeoProjectReferenceError("project tenant does not match principal")
        if not _can_access_project_reference(principal, command):
            raise GeoProjectReferenceError(
                "project reference is not available to current principal"
            )
        await self._validate_project_reference(command, access_token)
        return await self.repository.create_project(command)

    async def update_project(
        self,
        principal: AuthorizedPrincipal,
        project_id: UUID,
        command: GeoProjectCommand,
        access_token: str | None = None,
    ) -> GeoProjectRecord | None:
        if await self.get_project(principal, project_id) is None:
            return None
        if command.tenant_id != principal.tenant_id:
            raise GeoProjectReferenceError("project tenant does not match principal")
        if not _can_access_project_reference(principal, command):
            raise GeoProjectReferenceError(
                "project reference is not available to current principal"
            )
        await self._validate_project_reference(command, access_token)
        return await self.repository.update_project(
            principal.tenant_id,
            project_id,
            command,
        )

    async def delete_project(
        self,
        principal: AuthorizedPrincipal,
        project_id: UUID,
    ) -> bool:
        if await self.get_project(principal, project_id) is None:
            return False
        return await self.repository.delete_project(principal.tenant_id, project_id)

    async def list_markets(
        self,
        principal: AuthorizedPrincipal,
        project_id: UUID,
    ) -> list[GeoMarketRecord]:
        if await self.get_project(principal, project_id) is None:
            return []
        return await self.repository.list_markets(principal.tenant_id, project_id)

    async def create_market(
        self,
        principal: AuthorizedPrincipal,
        project_id: UUID,
        command: GeoMarketCommand,
    ) -> GeoMarketRecord | None:
        if await self.get_project(principal, project_id) is None:
            return None
        return await self.repository.create_market(
            principal.tenant_id,
            project_id,
            command,
        )

    async def update_market(
        self,
        principal: AuthorizedPrincipal,
        market_id: UUID,
        command: GeoMarketCommand,
    ) -> GeoMarketRecord | None:
        project = await self.repository.get_market_project(
            principal.tenant_id,
            market_id,
        )
        if project is None or not can_access_project(principal, project):
            return None
        return await self.repository.update_market(
            principal.tenant_id,
            market_id,
            command,
        )

    async def delete_market(self, principal: AuthorizedPrincipal, market_id: UUID) -> bool:
        project = await self.repository.get_market_project(
            principal.tenant_id,
            market_id,
        )
        if project is None or not can_access_project(principal, project):
            return False
        return await self.repository.delete_market(principal.tenant_id, market_id)

    async def list_entities(
        self,
        principal: AuthorizedPrincipal,
        project_id: UUID,
    ) -> list[GeoEntityRecord]:
        if await self.get_project(principal, project_id) is None:
            return []
        return await self.repository.list_entities(principal.tenant_id, project_id)

    async def get_entity(
        self,
        principal: AuthorizedPrincipal,
        entity_id: UUID,
    ) -> GeoEntityRecord | None:
        project = await self.repository.get_entity_project(
            principal.tenant_id,
            entity_id,
        )
        if project is None or not can_access_project(principal, project):
            return None
        return await self.repository.get_entity(principal.tenant_id, entity_id)

    async def create_entity(
        self,
        principal: AuthorizedPrincipal,
        project_id: UUID,
        command: GeoEntityCommand,
    ) -> GeoEntityRecord | None:
        if await self.get_project(principal, project_id) is None:
            return None
        return await self.repository.create_entity(
            principal.tenant_id,
            project_id,
            command,
        )

    async def update_entity(
        self,
        principal: AuthorizedPrincipal,
        entity_id: UUID,
        command: GeoEntityCommand,
    ) -> GeoEntityRecord | None:
        if await self.get_entity(principal, entity_id) is None:
            return None
        return await self.repository.update_entity(
            principal.tenant_id,
            entity_id,
            command,
        )

    async def delete_entity(
        self,
        principal: AuthorizedPrincipal,
        entity_id: UUID,
    ) -> bool:
        if await self.get_entity(principal, entity_id) is None:
            return False
        return await self.repository.delete_entity(principal.tenant_id, entity_id)

    async def list_aliases(
        self,
        principal: AuthorizedPrincipal,
        entity_id: UUID,
    ) -> list[GeoEntityAliasRecord]:
        if await self.get_entity(principal, entity_id) is None:
            return []
        return await self.repository.list_aliases(principal.tenant_id, entity_id)

    async def list_project_aliases(
        self,
        principal: AuthorizedPrincipal,
        project_id: UUID,
    ) -> list[GeoEntityAliasRecord]:
        if await self.get_project(principal, project_id) is None:
            return []
        return await self.repository.list_project_aliases(
            principal.tenant_id,
            project_id,
        )

    async def create_alias(
        self,
        principal: AuthorizedPrincipal,
        entity_id: UUID,
        command: GeoEntityAliasCommand,
    ) -> GeoEntityAliasRecord | None:
        if await self.get_entity(principal, entity_id) is None:
            return None
        return await self.repository.create_alias(
            principal.tenant_id,
            entity_id,
            command,
        )

    async def update_alias(
        self,
        principal: AuthorizedPrincipal,
        alias_id: UUID,
        command: GeoEntityAliasCommand,
    ) -> GeoEntityAliasRecord | None:
        project = await self.repository.get_alias_project(principal.tenant_id, alias_id)
        if project is None or not can_access_project(principal, project):
            return None
        return await self.repository.update_alias(
            principal.tenant_id,
            alias_id,
            command,
        )

    async def delete_alias(self, principal: AuthorizedPrincipal, alias_id: UUID) -> bool:
        project = await self.repository.get_alias_project(principal.tenant_id, alias_id)
        if project is None or not can_access_project(principal, project):
            return False
        return await self.repository.delete_alias(principal.tenant_id, alias_id)

    async def list_topics(
        self,
        principal: AuthorizedPrincipal,
        project_id: UUID,
    ) -> list[GeoTopicRecord]:
        if await self.get_project(principal, project_id) is None:
            return []
        return await self.repository.list_topics(principal.tenant_id, project_id)

    async def create_topic(
        self,
        principal: AuthorizedPrincipal,
        project_id: UUID,
        command: GeoTopicCommand,
    ) -> GeoTopicRecord | None:
        if await self.get_project(principal, project_id) is None:
            return None
        return await self.repository.create_topic(
            principal.tenant_id,
            project_id,
            command,
        )

    async def update_topic(
        self,
        principal: AuthorizedPrincipal,
        topic_id: UUID,
        command: GeoTopicCommand,
    ) -> GeoTopicRecord | None:
        project = await self.repository.get_topic_project(principal.tenant_id, topic_id)
        if project is None or not can_access_project(principal, project):
            return None
        return await self.repository.update_topic(
            principal.tenant_id,
            topic_id,
            command,
        )

    async def delete_topic(self, principal: AuthorizedPrincipal, topic_id: UUID) -> bool:
        project = await self.repository.get_topic_project(principal.tenant_id, topic_id)
        if project is None or not can_access_project(principal, project):
            return False
        return await self.repository.delete_topic(principal.tenant_id, topic_id)

    async def list_queries(
        self,
        principal: AuthorizedPrincipal,
        project_id: UUID,
    ) -> list[GeoQueryRecord]:
        if await self.get_project(principal, project_id) is None:
            return []
        return await self.repository.list_queries(principal.tenant_id, project_id)

    async def get_query(
        self,
        principal: AuthorizedPrincipal,
        query_id: UUID,
    ) -> GeoQueryRecord | None:
        project = await self.repository.get_query_project(principal.tenant_id, query_id)
        if project is None or not can_access_project(principal, project):
            return None
        return await self.repository.get_query(principal.tenant_id, query_id)

    async def create_query(
        self,
        principal: AuthorizedPrincipal,
        project_id: UUID,
        command: GeoQueryCommand,
    ) -> GeoQueryRecord | None:
        if await self.get_project(principal, project_id) is None:
            return None
        return await self.repository.create_query(
            principal.tenant_id,
            project_id,
            command,
        )

    async def update_query(
        self,
        principal: AuthorizedPrincipal,
        query_id: UUID,
        command: GeoQueryCommand,
    ) -> GeoQueryRecord | None:
        if await self.get_query(principal, query_id) is None:
            return None
        return await self.repository.update_query(
            principal.tenant_id,
            query_id,
            command,
        )

    async def delete_query(self, principal: AuthorizedPrincipal, query_id: UUID) -> bool:
        if await self.get_query(principal, query_id) is None:
            return False
        return await self.repository.delete_query(principal.tenant_id, query_id)

    async def list_query_platforms(
        self,
        principal: AuthorizedPrincipal,
        query_id: UUID,
    ) -> list[GeoQueryPlatformRecord]:
        if await self.get_query(principal, query_id) is None:
            return []
        return await self.repository.list_query_platforms(principal.tenant_id, query_id)

    async def list_project_query_platforms(
        self,
        principal: AuthorizedPrincipal,
        project_id: UUID,
    ) -> list[GeoQueryPlatformRecord]:
        if await self.get_project(principal, project_id) is None:
            return []
        return await self.repository.list_project_query_platforms(
            principal.tenant_id,
            project_id,
        )

    async def replace_query_platforms(
        self,
        principal: AuthorizedPrincipal,
        query_id: UUID,
        commands: list[GeoQueryPlatformCommand],
    ) -> list[GeoQueryPlatformRecord] | None:
        if await self.get_query(principal, query_id) is None:
            return None
        return await self.repository.replace_query_platforms(
            principal.tenant_id,
            query_id,
            commands,
        )

    async def list_schedules(
        self,
        principal: AuthorizedPrincipal,
        query_id: UUID,
    ) -> list[GeoQueryScheduleRecord]:
        if await self.get_query(principal, query_id) is None:
            return []
        return await self.repository.list_schedules(principal.tenant_id, query_id)

    async def list_project_schedules(
        self,
        principal: AuthorizedPrincipal,
        project_id: UUID,
    ) -> list[GeoQueryScheduleRecord]:
        if await self.get_project(principal, project_id) is None:
            return []
        return await self.repository.list_project_schedules(
            principal.tenant_id,
            project_id,
        )

    async def create_schedule(
        self,
        principal: AuthorizedPrincipal,
        query_id: UUID,
        command: GeoQueryScheduleCommand,
    ) -> GeoQueryScheduleRecord | None:
        if await self.get_query(principal, query_id) is None:
            return None
        return await self.repository.create_schedule(
            principal.tenant_id,
            query_id,
            command,
        )

    async def update_schedule(
        self,
        principal: AuthorizedPrincipal,
        schedule_id: UUID,
        command: GeoQueryScheduleCommand,
    ) -> GeoQueryScheduleRecord | None:
        project = await self.repository.get_schedule_project(
            principal.tenant_id,
            schedule_id,
        )
        if project is None or not can_access_project(principal, project):
            return None
        return await self.repository.update_schedule(
            principal.tenant_id,
            schedule_id,
            command,
        )

    async def delete_schedule(
        self,
        principal: AuthorizedPrincipal,
        schedule_id: UUID,
    ) -> bool:
        project = await self.repository.get_schedule_project(
            principal.tenant_id,
            schedule_id,
        )
        if project is None or not can_access_project(principal, project):
            return False
        return await self.repository.delete_schedule(principal.tenant_id, schedule_id)

    async def _validate_project_reference(
        self,
        command: GeoProjectCommand,
        access_token: str | None,
    ) -> None:
        _validate_project_reference(command)
        if self.reference_verifier is None:
            return
        if access_token is None:
            raise GeoProjectReferenceError(
                "access token is required to verify project references"
            )
        if command.customer_id is not None:
            exists = await self.reference_verifier.customer_exists(
                access_token=access_token,
                customer_id=command.customer_id,
            )
            if not exists:
                raise GeoProjectReferenceError(
                    "customerId is not available in current tenant"
                )
        if command.seo_task_id is not None:
            task = await self.reference_verifier.get_task(
                access_token=access_token,
                task_id=command.seo_task_id,
            )
            if task is None:
                raise GeoProjectReferenceError(
                    "seoTaskId is not available in current tenant"
                )
            if command.customer_id is not None and task.customer_id != command.customer_id:
                raise GeoProjectReferenceError("seoTaskId does not belong to customerId")


def _validate_project_reference(command: GeoProjectCommand) -> None:
    if command.customer_id is None and command.seo_task_id is not None:
        raise GeoProjectReferenceError("seoTaskId requires customerId")


def _can_access_project_reference(
    principal: AuthorizedPrincipal,
    command: GeoProjectCommand,
) -> bool:
    if principal.has_global_resource_access:
        return True
    if command.customer_id is not None and command.customer_id in principal.customer_ids:
        return True
    return command.seo_task_id is not None and command.seo_task_id in principal.task_ids
