from datetime import datetime
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
    async def research(self, command: QueryResearchCommand) -> dict:
        raise NotImplementedError

    async def generate(self, command: QueryGenerationCommand) -> dict:
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

    async def list_job_run_results(self, job_id: UUID) -> list[GeoRunResultRecord]:
        raise NotImplementedError

    async def list_project_run_results(
        self,
        project_id: UUID,
    ) -> list[GeoRunResultRecord]:
        raise NotImplementedError

    async def get_run_result(self, result_id: UUID) -> GeoRunResultRecord | None:
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

    async def create_query_research_run(
        self,
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
        project_id: UUID,
    ) -> list[QueryResearchRunRecord]:
        raise NotImplementedError

    async def get_query_research_run(
        self,
        run_id: UUID,
    ) -> QueryResearchRunRecord | None:
        raise NotImplementedError

    async def create_query_generation_run(
        self,
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
        project_id: UUID,
    ) -> list[QueryGenerationRunRecord]:
        raise NotImplementedError

    async def get_query_generation_run(
        self,
        run_id: UUID,
    ) -> QueryGenerationRunRecord | None:
        raise NotImplementedError

    async def update_query_draft_selection(
        self,
        draft_id: UUID,
        command: QueryDraftSelectionCommand,
    ) -> QueryDraftRecord | None:
        raise NotImplementedError

    async def accept_query_draft(
        self,
        draft_id: UUID,
        command: AcceptQueryDraftCommand,
    ) -> GeoQueryRecord | None:
        raise NotImplementedError
