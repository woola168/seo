import logging
from dataclasses import dataclass
from uuid import UUID

from younilab_seo.geo_analysis.application.contracts import (
    GeoAiPlatformRecord,
    GeoEntityAliasCommand,
    GeoEntityAliasRecord,
    GeoEntityCommand,
    GeoEntityRecord,
    GeoMarketCommand,
    GeoMarketRecord,
    GeoProjectCommand,
    GeoProjectQuerySettingsCommand,
    GeoProjectQuerySettingsRecord,
    GeoProjectRecord,
    GeoProjectStatusCommand,
    GeoProjectSummaryRecord,
    GeoQueryCommand,
    GeoQueryPlatformCommand,
    GeoQueryPlatformRecord,
    GeoQueryRecord,
    GeoQueryScheduleCommand,
    GeoQueryScheduleRecord,
    GeoQueryStatusCommand,
    GeoTopicCommand,
    GeoTopicRecord,
)
from younilab_seo.geo_analysis.application.errors import ArchivedGeoQueryStatusError
from younilab_seo.geo_analysis.application.interfaces import (
    AuthorizedPrincipal,
    ResourceCatalogCustomerReader,
    ResourceCatalogReferenceVerifier,
    ResourceCatalogVerificationDenied,
    ResourceCatalogVerificationUnavailable,
)
from younilab_seo.geo_analysis.application.interfaces.entity_catalog import (
    EntityCatalogPersistence,
)
from younilab_seo.geo_analysis.application.interfaces.project_setup import (
    ProjectSetupPersistence,
)
from younilab_seo.geo_analysis.application.interfaces.query_catalog import (
    QueryCatalogPersistence,
)
from younilab_seo.geo_analysis.application.use_cases.access_policy import (
    can_access_project,
    filter_accessible_projects,
)
from younilab_seo.geo_analysis.application.use_cases.planning import (
    GeoProjectReferenceError,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ManageGeoSetup:
    """管理 GEO project setup 資料，並套用 tenant 與 resource grant 邊界。"""

    project_persistence: ProjectSetupPersistence
    reference_verifier: ResourceCatalogReferenceVerifier | None = None
    customer_reader: ResourceCatalogCustomerReader | None = None
    entity_persistence: EntityCatalogPersistence | None = None
    query_catalog_persistence: QueryCatalogPersistence | None = None

    def __post_init__(self) -> None:
        if self.entity_persistence is None:
            object.__setattr__(self, "entity_persistence", self.project_persistence)
        if self.query_catalog_persistence is None:
            object.__setattr__(
                self,
                "query_catalog_persistence",
                self.project_persistence,
            )

    async def list_projects(
        self,
        principal: AuthorizedPrincipal,
        customer_id: UUID | None = None,
    ) -> list[GeoProjectRecord]:
        projects = await self.project_persistence.list_projects(
            principal.tenant_id,
            customer_id,
        )
        return filter_accessible_projects(principal, projects)

    async def list_project_summaries(
        self,
        principal: AuthorizedPrincipal,
        customer_id: UUID | None = None,
        *,
        access_token: str | None = None,
    ) -> list[GeoProjectSummaryRecord]:
        summaries = await self.project_persistence.list_project_summaries(
            principal.tenant_id,
            customer_id,
        )
        accessible = [
            summary for summary in summaries if can_access_project(principal, summary)
        ]
        customer_ids = frozenset(
            summary.customer_id
            for summary in accessible
            if summary.customer_id is not None
        )
        if not customer_ids or self.customer_reader is None or access_token is None:
            return accessible
        try:
            names = await self.customer_reader.list_customer_names(
                access_token=access_token,
                customer_ids=customer_ids,
            )
        except (
            ResourceCatalogVerificationDenied,
            ResourceCatalogVerificationUnavailable,
        ) as exc:
            logger.warning(
                "GEO Project customer names unavailable: %s",
                type(exc).__name__,
            )
            return accessible
        return [
            summary.model_copy(update={"customer_name": names.get(summary.customer_id)})
            for summary in accessible
        ]

    async def get_project(
        self,
        principal: AuthorizedPrincipal,
        project_id: UUID,
    ) -> GeoProjectRecord | None:
        project = await self.project_persistence.get_project(
            principal.tenant_id,
            project_id,
        )
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
        return await self.project_persistence.create_project(command)

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
        return await self.project_persistence.update_project(
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
        return await self.project_persistence.delete_project(
            principal.tenant_id,
            project_id,
        )

    async def update_project_status(
        self,
        principal: AuthorizedPrincipal,
        project_id: UUID,
        command: GeoProjectStatusCommand,
    ) -> GeoProjectRecord | None:
        if await self.get_project(principal, project_id) is None:
            return None
        return await self.project_persistence.update_project_status(
            principal.tenant_id,
            project_id,
            command,
        )

    async def get_project_query_settings(
        self,
        principal: AuthorizedPrincipal,
        project_id: UUID,
    ) -> GeoProjectQuerySettingsRecord | None:
        if await self.get_project(principal, project_id) is None:
            return None
        return await self.project_persistence.get_project_query_settings(
            principal.tenant_id,
            project_id,
        )

    async def replace_project_query_settings(
        self,
        principal: AuthorizedPrincipal,
        project_id: UUID,
        command: GeoProjectQuerySettingsCommand,
    ) -> GeoProjectQuerySettingsRecord | None:
        if await self.get_project(principal, project_id) is None:
            return None
        current = await self.project_persistence.get_project_query_settings(
            principal.tenant_id,
            project_id,
        )
        if current is not None and _query_settings_equal(current, command):
            return current
        return await self.project_persistence.upsert_project_query_settings(
            principal.tenant_id,
            project_id,
            command,
        )

    async def list_markets(
        self,
        principal: AuthorizedPrincipal,
        project_id: UUID,
    ) -> list[GeoMarketRecord]:
        if await self.get_project(principal, project_id) is None:
            return []
        return await self.project_persistence.list_markets(
            principal.tenant_id,
            project_id,
        )

    async def create_market(
        self,
        principal: AuthorizedPrincipal,
        project_id: UUID,
        command: GeoMarketCommand,
    ) -> GeoMarketRecord | None:
        if await self.get_project(principal, project_id) is None:
            return None
        return await self.project_persistence.create_market(
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
        project = await self.project_persistence.get_market_project(
            principal.tenant_id,
            market_id,
        )
        if project is None or not can_access_project(principal, project):
            return None
        return await self.project_persistence.update_market(
            principal.tenant_id,
            market_id,
            command,
        )

    async def delete_market(
        self, principal: AuthorizedPrincipal, market_id: UUID
    ) -> bool:
        project = await self.project_persistence.get_market_project(
            principal.tenant_id,
            market_id,
        )
        if project is None or not can_access_project(principal, project):
            return False
        return await self.project_persistence.delete_market(
            principal.tenant_id,
            market_id,
        )

    async def list_entities(
        self,
        principal: AuthorizedPrincipal,
        project_id: UUID,
    ) -> list[GeoEntityRecord]:
        if await self.get_project(principal, project_id) is None:
            return []
        return await self.entity_persistence.list_entities(
            principal.tenant_id,
            project_id,
        )

    async def get_entity(
        self,
        principal: AuthorizedPrincipal,
        entity_id: UUID,
    ) -> GeoEntityRecord | None:
        project = await self.entity_persistence.get_entity_project(
            principal.tenant_id,
            entity_id,
        )
        if project is None or not can_access_project(principal, project):
            return None
        return await self.entity_persistence.get_entity(
            principal.tenant_id,
            entity_id,
        )

    async def create_entity(
        self,
        principal: AuthorizedPrincipal,
        project_id: UUID,
        command: GeoEntityCommand,
    ) -> GeoEntityRecord | None:
        if await self.get_project(principal, project_id) is None:
            return None
        return await self.entity_persistence.create_entity(
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
        return await self.entity_persistence.update_entity(
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
        return await self.entity_persistence.delete_entity(
            principal.tenant_id,
            entity_id,
        )

    async def list_aliases(
        self,
        principal: AuthorizedPrincipal,
        entity_id: UUID,
    ) -> list[GeoEntityAliasRecord] | None:
        if await self.get_entity(principal, entity_id) is None:
            return None
        return await self.entity_persistence.list_aliases(
            principal.tenant_id,
            entity_id,
        )

    async def list_project_aliases(
        self,
        principal: AuthorizedPrincipal,
        project_id: UUID,
    ) -> list[GeoEntityAliasRecord]:
        if await self.get_project(principal, project_id) is None:
            return []
        return await self.entity_persistence.list_project_aliases(
            principal.tenant_id,
            project_id,
        )

    async def replace_aliases(
        self,
        principal: AuthorizedPrincipal,
        entity_id: UUID,
        commands: list[GeoEntityAliasCommand],
    ) -> list[GeoEntityAliasRecord] | None:
        if await self.get_entity(principal, entity_id) is None:
            return None
        return await self.entity_persistence.replace_aliases(
            principal.tenant_id,
            entity_id,
            commands,
        )

    async def list_topics(
        self,
        principal: AuthorizedPrincipal,
        project_id: UUID,
    ) -> list[GeoTopicRecord]:
        if await self.get_project(principal, project_id) is None:
            return []
        return await self.query_catalog_persistence.list_topics(
            principal.tenant_id,
            project_id,
        )

    async def create_topic(
        self,
        principal: AuthorizedPrincipal,
        project_id: UUID,
        command: GeoTopicCommand,
    ) -> GeoTopicRecord | None:
        if await self.get_project(principal, project_id) is None:
            return None
        return await self.query_catalog_persistence.create_topic(
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
        project = await self.query_catalog_persistence.get_topic_project(
            principal.tenant_id,
            topic_id,
        )
        if project is None or not can_access_project(principal, project):
            return None
        return await self.query_catalog_persistence.update_topic(
            principal.tenant_id,
            topic_id,
            command,
        )

    async def delete_topic(
        self, principal: AuthorizedPrincipal, topic_id: UUID
    ) -> bool:
        project = await self.query_catalog_persistence.get_topic_project(
            principal.tenant_id,
            topic_id,
        )
        if project is None or not can_access_project(principal, project):
            return False
        return await self.query_catalog_persistence.delete_topic(
            principal.tenant_id,
            topic_id,
        )

    async def list_queries(
        self,
        principal: AuthorizedPrincipal,
        project_id: UUID,
    ) -> list[GeoQueryRecord]:
        if await self.get_project(principal, project_id) is None:
            return []
        return await self.query_catalog_persistence.list_queries(
            principal.tenant_id,
            project_id,
        )

    async def get_query(
        self,
        principal: AuthorizedPrincipal,
        query_id: UUID,
    ) -> GeoQueryRecord | None:
        project = await self.query_catalog_persistence.get_query_project(
            principal.tenant_id,
            query_id,
        )
        if project is None or not can_access_project(principal, project):
            return None
        return await self.query_catalog_persistence.get_query(
            principal.tenant_id,
            query_id,
        )

    async def create_query(
        self,
        principal: AuthorizedPrincipal,
        project_id: UUID,
        command: GeoQueryCommand,
    ) -> GeoQueryRecord | None:
        if await self.get_project(principal, project_id) is None:
            return None
        return await self.query_catalog_persistence.create_query(
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
        return await self.query_catalog_persistence.update_query(
            principal.tenant_id,
            query_id,
            command,
        )

    async def update_query_status(
        self,
        principal: AuthorizedPrincipal,
        query_id: UUID,
        command: GeoQueryStatusCommand,
    ) -> GeoQueryRecord | None:
        query = await self.get_query(principal, query_id)
        if query is None:
            return None
        if query.status == "archived":
            raise ArchivedGeoQueryStatusError()
        return await self.query_catalog_persistence.update_query_status(
            principal.tenant_id,
            query_id,
            command,
        )

    async def delete_query(
        self, principal: AuthorizedPrincipal, query_id: UUID
    ) -> bool:
        if await self.get_query(principal, query_id) is None:
            return False
        return await self.query_catalog_persistence.delete_query(
            principal.tenant_id,
            query_id,
        )

    async def list_ai_platforms(self) -> list[GeoAiPlatformRecord]:
        return await self.query_catalog_persistence.list_ai_platforms()

    async def list_query_platforms(
        self,
        principal: AuthorizedPrincipal,
        query_id: UUID,
    ) -> list[GeoQueryPlatformRecord]:
        if await self.get_query(principal, query_id) is None:
            return []
        return await self.query_catalog_persistence.list_query_platforms(
            principal.tenant_id,
            query_id,
        )

    async def list_project_query_platforms(
        self,
        principal: AuthorizedPrincipal,
        project_id: UUID,
    ) -> list[GeoQueryPlatformRecord]:
        if await self.get_project(principal, project_id) is None:
            return []
        return await self.query_catalog_persistence.list_project_query_platforms(
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
        return await self.query_catalog_persistence.replace_query_platforms(
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
        return await self.query_catalog_persistence.list_schedules(
            principal.tenant_id,
            query_id,
        )

    async def list_project_schedules(
        self,
        principal: AuthorizedPrincipal,
        project_id: UUID,
    ) -> list[GeoQueryScheduleRecord]:
        if await self.get_project(principal, project_id) is None:
            return []
        return await self.query_catalog_persistence.list_project_schedules(
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
        return await self.query_catalog_persistence.create_schedule(
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
        project = await self.query_catalog_persistence.get_schedule_project(
            principal.tenant_id,
            schedule_id,
        )
        if project is None or not can_access_project(principal, project):
            return None
        return await self.query_catalog_persistence.update_schedule(
            principal.tenant_id,
            schedule_id,
            command,
        )

    async def delete_schedule(
        self,
        principal: AuthorizedPrincipal,
        schedule_id: UUID,
    ) -> bool:
        project = await self.query_catalog_persistence.get_schedule_project(
            principal.tenant_id,
            schedule_id,
        )
        if project is None or not can_access_project(principal, project):
            return False
        return await self.query_catalog_persistence.delete_schedule(
            principal.tenant_id,
            schedule_id,
        )

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


def _validate_project_reference(command: GeoProjectCommand) -> None:
    return None


def _query_settings_equal(
    current: GeoProjectQuerySettingsRecord,
    command: GeoProjectQuerySettingsCommand,
) -> bool:
    return (
        current.model_dump(exclude={"project_id", "created_at", "updated_at"})
        == command.model_dump()
    )


def _can_access_project_reference(
    principal: AuthorizedPrincipal,
    command: GeoProjectCommand,
) -> bool:
    if principal.has_global_resource_access:
        return True
    if (
        command.customer_id is not None
        and command.customer_id in principal.customer_ids
    ):
        return True
    return False
