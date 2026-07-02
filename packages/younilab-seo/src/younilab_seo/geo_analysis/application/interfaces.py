from datetime import datetime
from dataclasses import dataclass
from typing import Protocol, runtime_checkable
from uuid import UUID

from younilab_seo.geo_analysis.application.contracts import (
    AcceptQueryDraftCommand,
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
    GeoRunResultRecord,
    GeoTopicCommand,
    GeoTopicRecord,
    PublishResult,
    QueryDraftRecord,
    QueryDraftSelectionCommand,
    QueryGenerationCommand,
    QueryGenerationRunRecord,
    QueryResearchCommand,
    QueryResearchRunRecord,
    QueryRunJobMessage,
    SaveTrackingRunResultCommand,
    TrackingRunResponse,
)
from younilab_seo.geo_analysis.domain import GeoQueryRunJob


class Clock(Protocol):
    """use case 使用的時間來源，讓測試可以固定時間。"""

    def now(self) -> datetime:
        raise NotImplementedError


class IdGenerator(Protocol):
    """application boundary 建立 orchestration record id 的來源。"""

    def new_id(self) -> UUID:
        raise NotImplementedError


class MessagePublisher(Protocol):
    """將 GEO query run job 發布到 message broker 的 port。"""

    async def publish(self, message: QueryRunJobMessage) -> PublishResult:
        raise NotImplementedError


class TrackingRunClient(Protocol):
    """透過已設定的 runner service 執行已發布的 GEO query。"""

    def build_request_payload(self, message: QueryRunJobMessage) -> dict:
        raise NotImplementedError

    async def run(self, message: QueryRunJobMessage) -> TrackingRunResponse:
        raise NotImplementedError


class QueryPlanningClient(Protocol):
    """Query Research / Generation provider 的 application port。"""

    async def research(self, command: QueryResearchCommand) -> dict:
        raise NotImplementedError

    async def generate(self, command: QueryGenerationCommand) -> dict:
        raise NotImplementedError


class ResourceCatalogVerificationDenied(PermissionError):
    """Resource Catalog 拒絕目前 token 驗證 reference ownership。"""

    pass


class ResourceCatalogVerificationUnavailable(RuntimeError):
    """Resource Catalog 無法完成 reference ownership 驗證。"""

    pass


@dataclass(frozen=True)
class AuthorizedPrincipal:
    """Access Control 回傳給 GEO application layer 的授權上下文。"""

    tenant_id: UUID
    permissions: frozenset[str]
    has_global_resource_access: bool
    customer_ids: frozenset[UUID]
    task_ids: frozenset[UUID]


@dataclass(frozen=True)
class ResourceTaskReference:
    """Resource Catalog 回傳的 SEO task reference 與其 customer 歸屬。"""

    id: UUID
    customer_id: UUID


class PermissionAuthorizer(Protocol):
    """從 access token 解析 GEO API 所需權限與租戶資料的 port。"""

    async def require(
        self,
        access_token: str,
        permission: str,
    ) -> AuthorizedPrincipal:
        raise NotImplementedError


class ResourceCatalogReferenceVerifier(Protocol):
    """驗證 GEO project 綁定的 customer/task 是否屬於目前授權範圍。"""

    async def customer_exists(
        self,
        *,
        access_token: str,
        customer_id: UUID,
    ) -> bool:
        raise NotImplementedError

    async def get_task(
        self,
        *,
        access_token: str,
        task_id: UUID,
    ) -> ResourceTaskReference | None:
        raise NotImplementedError


@runtime_checkable
class GeoQueryRunJobRepository(Protocol):
    """query run job lifecycle 與 evidence persistence port。"""

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

    async def save_tracking_run_result(
        self,
        *,
        command: SaveTrackingRunResultCommand,
        occurred_at: datetime,
    ) -> GeoQueryRunJob:
        raise NotImplementedError

    async def get_job_tenant_id(self, job_id: UUID) -> UUID | None:
        raise NotImplementedError

    async def get_job_project(
        self,
        tenant_id: UUID,
        job_id: UUID,
    ) -> GeoProjectRecord | None:
        raise NotImplementedError

    async def list_job_run_results(
        self,
        tenant_id: UUID,
        job_id: UUID,
    ) -> list[GeoRunResultRecord]:
        raise NotImplementedError

    async def list_project_run_results(
        self,
        tenant_id: UUID,
        project_id: UUID,
    ) -> list[GeoRunResultRecord]:
        raise NotImplementedError

    async def get_run_result(
        self,
        tenant_id: UUID,
        result_id: UUID,
    ) -> GeoRunResultRecord | None:
        raise NotImplementedError


@runtime_checkable
class GeoAnalysisRepository(GeoQueryRunJobRepository, Protocol):
    """GEO setup 與 query run job orchestration 的 application repository port。"""

    async def list_projects(
        self,
        tenant_id: UUID,
        customer_id: UUID | None = None,
    ) -> list[GeoProjectRecord]:
        raise NotImplementedError

    async def get_project(
        self,
        tenant_id: UUID,
        project_id: UUID,
    ) -> GeoProjectRecord | None:
        raise NotImplementedError

    async def get_query_project(
        self,
        tenant_id: UUID,
        query_id: UUID,
    ) -> GeoProjectRecord | None:
        raise NotImplementedError

    async def get_market_project(
        self,
        tenant_id: UUID,
        market_id: UUID,
    ) -> GeoProjectRecord | None:
        raise NotImplementedError

    async def get_entity_project(
        self,
        tenant_id: UUID,
        entity_id: UUID,
    ) -> GeoProjectRecord | None:
        raise NotImplementedError

    async def get_alias_project(
        self,
        tenant_id: UUID,
        alias_id: UUID,
    ) -> GeoProjectRecord | None:
        raise NotImplementedError

    async def get_topic_project(
        self,
        tenant_id: UUID,
        topic_id: UUID,
    ) -> GeoProjectRecord | None:
        raise NotImplementedError

    async def get_schedule_project(
        self,
        tenant_id: UUID,
        schedule_id: UUID,
    ) -> GeoProjectRecord | None:
        raise NotImplementedError

    async def get_run_result_project(
        self,
        tenant_id: UUID,
        result_id: UUID,
    ) -> GeoProjectRecord | None:
        raise NotImplementedError

    async def get_query_research_run_project(
        self,
        tenant_id: UUID,
        run_id: UUID,
    ) -> GeoProjectRecord | None:
        raise NotImplementedError

    async def get_query_generation_run_project(
        self,
        tenant_id: UUID,
        run_id: UUID,
    ) -> GeoProjectRecord | None:
        raise NotImplementedError

    async def get_query_draft_project(
        self,
        tenant_id: UUID,
        draft_id: UUID,
    ) -> GeoProjectRecord | None:
        raise NotImplementedError

    async def create_project(self, command: GeoProjectCommand) -> GeoProjectRecord:
        raise NotImplementedError

    async def update_project(
        self,
        tenant_id: UUID,
        project_id: UUID,
        command: GeoProjectCommand,
    ) -> GeoProjectRecord | None:
        raise NotImplementedError

    async def delete_project(self, tenant_id: UUID, project_id: UUID) -> bool:
        raise NotImplementedError

    async def list_markets(self, tenant_id: UUID, project_id: UUID) -> list[GeoMarketRecord]:
        raise NotImplementedError

    async def create_market(
        self,
        tenant_id: UUID,
        project_id: UUID,
        command: GeoMarketCommand,
    ) -> GeoMarketRecord | None:
        raise NotImplementedError

    async def update_market(
        self,
        tenant_id: UUID,
        market_id: UUID,
        command: GeoMarketCommand,
    ) -> GeoMarketRecord | None:
        raise NotImplementedError

    async def delete_market(self, tenant_id: UUID, market_id: UUID) -> bool:
        raise NotImplementedError

    async def list_entities(self, tenant_id: UUID, project_id: UUID) -> list[GeoEntityRecord]:
        raise NotImplementedError

    async def get_entity(self, tenant_id: UUID, entity_id: UUID) -> GeoEntityRecord | None:
        raise NotImplementedError

    async def create_entity(
        self,
        tenant_id: UUID,
        project_id: UUID,
        command: GeoEntityCommand,
    ) -> GeoEntityRecord | None:
        raise NotImplementedError

    async def update_entity(
        self,
        tenant_id: UUID,
        entity_id: UUID,
        command: GeoEntityCommand,
    ) -> GeoEntityRecord | None:
        raise NotImplementedError

    async def delete_entity(self, tenant_id: UUID, entity_id: UUID) -> bool:
        raise NotImplementedError

    async def list_aliases(self, tenant_id: UUID, entity_id: UUID) -> list[GeoEntityAliasRecord]:
        raise NotImplementedError

    async def create_alias(
        self,
        tenant_id: UUID,
        entity_id: UUID,
        command: GeoEntityAliasCommand,
    ) -> GeoEntityAliasRecord | None:
        raise NotImplementedError

    async def update_alias(
        self,
        tenant_id: UUID,
        alias_id: UUID,
        command: GeoEntityAliasCommand,
    ) -> GeoEntityAliasRecord | None:
        raise NotImplementedError

    async def delete_alias(self, tenant_id: UUID, alias_id: UUID) -> bool:
        raise NotImplementedError

    async def list_topics(self, tenant_id: UUID, project_id: UUID) -> list[GeoTopicRecord]:
        raise NotImplementedError

    async def create_topic(
        self,
        tenant_id: UUID,
        project_id: UUID,
        command: GeoTopicCommand,
    ) -> GeoTopicRecord | None:
        raise NotImplementedError

    async def update_topic(
        self,
        tenant_id: UUID,
        topic_id: UUID,
        command: GeoTopicCommand,
    ) -> GeoTopicRecord | None:
        raise NotImplementedError

    async def delete_topic(self, tenant_id: UUID, topic_id: UUID) -> bool:
        raise NotImplementedError

    async def list_queries(self, tenant_id: UUID, project_id: UUID) -> list[GeoQueryRecord]:
        raise NotImplementedError

    async def get_query(self, tenant_id: UUID, query_id: UUID) -> GeoQueryRecord | None:
        raise NotImplementedError

    async def create_query(
        self,
        tenant_id: UUID,
        project_id: UUID,
        command: GeoQueryCommand,
    ) -> GeoQueryRecord | None:
        raise NotImplementedError

    async def update_query(
        self,
        tenant_id: UUID,
        query_id: UUID,
        command: GeoQueryCommand,
    ) -> GeoQueryRecord | None:
        raise NotImplementedError

    async def delete_query(self, tenant_id: UUID, query_id: UUID) -> bool:
        raise NotImplementedError

    async def list_query_platforms(
        self,
        tenant_id: UUID,
        query_id: UUID,
    ) -> list[GeoQueryPlatformRecord]:
        raise NotImplementedError

    async def replace_query_platforms(
        self,
        tenant_id: UUID,
        query_id: UUID,
        commands: list[GeoQueryPlatformCommand],
    ) -> list[GeoQueryPlatformRecord] | None:
        raise NotImplementedError

    async def list_schedules(
        self,
        tenant_id: UUID,
        query_id: UUID,
    ) -> list[GeoQueryScheduleRecord]:
        raise NotImplementedError

    async def create_schedule(
        self,
        tenant_id: UUID,
        query_id: UUID,
        command: GeoQueryScheduleCommand,
    ) -> GeoQueryScheduleRecord | None:
        raise NotImplementedError

    async def update_schedule(
        self,
        tenant_id: UUID,
        schedule_id: UUID,
        command: GeoQueryScheduleCommand,
    ) -> GeoQueryScheduleRecord | None:
        raise NotImplementedError

    async def delete_schedule(self, tenant_id: UUID, schedule_id: UUID) -> bool:
        raise NotImplementedError

    async def create_job(
        self,
        tenant_id: UUID,
        query_id: UUID,
        command: CreateQueryRunJobCommand,
    ) -> GeoQueryRunJob | None:
        raise NotImplementedError

    async def list_jobs(self, tenant_id: UUID, project_id: UUID) -> list[GeoQueryRunJob]:
        raise NotImplementedError

    async def get_job(self, tenant_id: UUID, job_id: UUID) -> GeoQueryRunJob | None:
        raise NotImplementedError

    async def create_query_research_run(
        self,
        tenant_id: UUID,
        project_id: UUID,
        command: QueryResearchCommand,
        request_payload: dict,
        result: dict | None,
        status: str,
        error_message: str | None,
        occurred_at: datetime,
    ) -> QueryResearchRunRecord | None:
        raise NotImplementedError

    async def list_query_research_runs(
        self,
        tenant_id: UUID,
        project_id: UUID,
    ) -> list[QueryResearchRunRecord]:
        raise NotImplementedError

    async def get_query_research_run(
        self,
        tenant_id: UUID,
        run_id: UUID,
    ) -> QueryResearchRunRecord | None:
        raise NotImplementedError

    async def create_query_generation_run(
        self,
        tenant_id: UUID,
        project_id: UUID,
        command: QueryGenerationCommand,
        request_payload: dict,
        result: dict | None,
        status: str,
        error_message: str | None,
        occurred_at: datetime,
    ) -> QueryGenerationRunRecord | None:
        raise NotImplementedError

    async def list_query_generation_runs(
        self,
        tenant_id: UUID,
        project_id: UUID,
    ) -> list[QueryGenerationRunRecord]:
        raise NotImplementedError

    async def get_query_generation_run(
        self,
        tenant_id: UUID,
        run_id: UUID,
    ) -> QueryGenerationRunRecord | None:
        raise NotImplementedError

    async def update_query_draft_selection(
        self,
        tenant_id: UUID,
        draft_id: UUID,
        command: QueryDraftSelectionCommand,
    ) -> QueryDraftRecord | None:
        raise NotImplementedError

    async def accept_query_draft(
        self,
        tenant_id: UUID,
        draft_id: UUID,
        command: AcceptQueryDraftCommand,
    ) -> GeoQueryRecord | None:
        raise NotImplementedError
