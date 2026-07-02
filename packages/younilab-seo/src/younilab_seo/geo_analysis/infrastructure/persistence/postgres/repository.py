from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from urllib.parse import urlparse
from uuid import UUID, uuid4

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

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
    GeoRunResultReferenceRecord,
    GeoTopicCommand,
    GeoTopicRecord,
    PublishResult,
    QueryDraftRecord,
    QueryDraftSelectionCommand,
    QueryGenerationCommand,
    QueryGenerationRunRecord,
    QueryResearchCommand,
    QueryResearchResultRecord,
    QueryResearchRunRecord,
    QueryRunJobMessage,
    SaveTrackingRunResultCommand,
)
from younilab_seo.geo_analysis.domain import GeoQueryRunJob, JobStatus
from younilab_seo.geo_analysis.infrastructure.persistence.postgres.models import (
    GeoAiPlatformRow,
    GeoEntityAliasRow,
    GeoEntityRow,
    GeoExternalRunReferenceRow,
    GeoJobDispatchEventRow,
    GeoMarketRow,
    GeoMessageDispatchLogRow,
    GeoProjectRow,
    GeoQueryPlatformRow,
    GeoQueryDraftRow,
    GeoQueryDraftSelectionRow,
    GeoQueryGenerationRunRow,
    GeoQueryResearchRunRow,
    GeoQueryRow,
    GeoQueryRunJobRow,
    GeoQueryScheduleRow,
    GeoRunRequestRow,
    GeoRunResultReferenceRow,
    GeoRunResultRow,
    GeoTopicRow,
)


class PostgresGeoAnalysisRepository:
    """GEO setup 與 job orchestration 的 PostgreSQL persistence adapter。"""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def list_projects(
        self,
        tenant_id: UUID,
        customer_id: UUID | None = None,
    ) -> list[GeoProjectRecord]:
        statement = (
            select(GeoProjectRow)
            .where(GeoProjectRow.tenant_id == tenant_id)
            .order_by(GeoProjectRow.created_at.desc())
        )
        if customer_id is not None:
            statement = statement.where(GeoProjectRow.customer_id == customer_id)
        async with self._session_scope() as session:
            rows = (await session.scalars(statement)).all()
            return [_project_record(row) for row in rows]

    async def get_project(
        self,
        tenant_id: UUID,
        project_id: UUID,
    ) -> GeoProjectRecord | None:
        async with self._session_scope() as session:
            row = await self._get_project_row(session, tenant_id, project_id)
            return _project_record(row) if row is not None else None

    async def get_query_project(
        self,
        tenant_id: UUID,
        query_id: UUID,
    ) -> GeoProjectRecord | None:
        statement = (
            select(GeoProjectRow)
            .join(GeoQueryRow, GeoQueryRow.project_id == GeoProjectRow.id)
            .where(GeoProjectRow.tenant_id == tenant_id, GeoQueryRow.id == query_id)
        )
        return await self._project_record_for(statement)

    async def get_market_project(
        self,
        tenant_id: UUID,
        market_id: UUID,
    ) -> GeoProjectRecord | None:
        statement = (
            select(GeoProjectRow)
            .join(GeoMarketRow, GeoMarketRow.project_id == GeoProjectRow.id)
            .where(GeoProjectRow.tenant_id == tenant_id, GeoMarketRow.id == market_id)
        )
        return await self._project_record_for(statement)

    async def get_entity_project(
        self,
        tenant_id: UUID,
        entity_id: UUID,
    ) -> GeoProjectRecord | None:
        statement = (
            select(GeoProjectRow)
            .join(GeoEntityRow, GeoEntityRow.project_id == GeoProjectRow.id)
            .where(GeoProjectRow.tenant_id == tenant_id, GeoEntityRow.id == entity_id)
        )
        return await self._project_record_for(statement)

    async def get_alias_project(
        self,
        tenant_id: UUID,
        alias_id: UUID,
    ) -> GeoProjectRecord | None:
        statement = (
            select(GeoProjectRow)
            .join(GeoEntityRow, GeoEntityRow.project_id == GeoProjectRow.id)
            .join(GeoEntityAliasRow, GeoEntityAliasRow.entity_id == GeoEntityRow.id)
            .where(
                GeoProjectRow.tenant_id == tenant_id,
                GeoEntityAliasRow.id == alias_id,
            )
        )
        return await self._project_record_for(statement)

    async def get_topic_project(
        self,
        tenant_id: UUID,
        topic_id: UUID,
    ) -> GeoProjectRecord | None:
        statement = (
            select(GeoProjectRow)
            .join(GeoTopicRow, GeoTopicRow.project_id == GeoProjectRow.id)
            .where(GeoProjectRow.tenant_id == tenant_id, GeoTopicRow.id == topic_id)
        )
        return await self._project_record_for(statement)

    async def get_schedule_project(
        self,
        tenant_id: UUID,
        schedule_id: UUID,
    ) -> GeoProjectRecord | None:
        statement = (
            select(GeoProjectRow)
            .join(GeoQueryRow, GeoQueryRow.project_id == GeoProjectRow.id)
            .join(GeoQueryScheduleRow, GeoQueryScheduleRow.query_id == GeoQueryRow.id)
            .where(
                GeoProjectRow.tenant_id == tenant_id,
                GeoQueryScheduleRow.id == schedule_id,
            )
        )
        return await self._project_record_for(statement)

    async def get_job_project(
        self,
        tenant_id: UUID,
        job_id: UUID,
    ) -> GeoProjectRecord | None:
        statement = (
            select(GeoProjectRow)
            .join(GeoQueryRunJobRow, GeoQueryRunJobRow.project_id == GeoProjectRow.id)
            .where(GeoProjectRow.tenant_id == tenant_id, GeoQueryRunJobRow.id == job_id)
        )
        return await self._project_record_for(statement)

    async def get_run_result_project(
        self,
        tenant_id: UUID,
        result_id: UUID,
    ) -> GeoProjectRecord | None:
        statement = (
            select(GeoProjectRow)
            .join(GeoQueryRunJobRow, GeoQueryRunJobRow.project_id == GeoProjectRow.id)
            .join(GeoRunResultRow, GeoRunResultRow.job_id == GeoQueryRunJobRow.id)
            .where(GeoProjectRow.tenant_id == tenant_id, GeoRunResultRow.id == result_id)
        )
        return await self._project_record_for(statement)

    async def get_query_research_run_project(
        self,
        tenant_id: UUID,
        run_id: UUID,
    ) -> GeoProjectRecord | None:
        statement = (
            select(GeoProjectRow)
            .join(GeoQueryResearchRunRow, GeoQueryResearchRunRow.project_id == GeoProjectRow.id)
            .where(
                GeoProjectRow.tenant_id == tenant_id,
                GeoQueryResearchRunRow.id == run_id,
            )
        )
        return await self._project_record_for(statement)

    async def get_query_generation_run_project(
        self,
        tenant_id: UUID,
        run_id: UUID,
    ) -> GeoProjectRecord | None:
        statement = (
            select(GeoProjectRow)
            .join(GeoQueryGenerationRunRow, GeoQueryGenerationRunRow.project_id == GeoProjectRow.id)
            .where(
                GeoProjectRow.tenant_id == tenant_id,
                GeoQueryGenerationRunRow.id == run_id,
            )
        )
        return await self._project_record_for(statement)

    async def get_query_draft_project(
        self,
        tenant_id: UUID,
        draft_id: UUID,
    ) -> GeoProjectRecord | None:
        statement = (
            select(GeoProjectRow)
            .join(GeoQueryDraftRow, GeoQueryDraftRow.project_id == GeoProjectRow.id)
            .where(GeoProjectRow.tenant_id == tenant_id, GeoQueryDraftRow.id == draft_id)
        )
        return await self._project_record_for(statement)

    async def create_project(self, command: GeoProjectCommand) -> GeoProjectRecord:
        now = _now()
        row = GeoProjectRow(
            id=uuid4(),
            tenant_id=command.tenant_id,
            customer_id=command.customer_id,
            seo_task_id=command.seo_task_id,
            name=command.name,
            default_region=command.default_region,
            default_language=command.default_language,
            status=command.status,
            daily_run_budget=command.daily_run_budget,
            created_at=now,
            updated_at=now,
        )
        async with self._session_scope() as session:
            session.add(row)
        return _project_record(row)

    async def update_project(
        self,
        tenant_id: UUID,
        project_id: UUID,
        command: GeoProjectCommand,
    ) -> GeoProjectRecord | None:
        async with self._session_scope() as session:
            row = await self._get_project_row(session, tenant_id, project_id)
            if row is None:
                return None
            row.tenant_id = tenant_id
            row.customer_id = command.customer_id
            row.seo_task_id = command.seo_task_id
            row.name = command.name
            row.default_region = command.default_region
            row.default_language = command.default_language
            row.status = command.status
            row.daily_run_budget = command.daily_run_budget
            row.updated_at = _now()
            return _project_record(row)

    async def delete_project(self, tenant_id: UUID, project_id: UUID) -> bool:
        async with self._session_scope() as session:
            row = await self._get_project_row(session, tenant_id, project_id)
            if row is None:
                return False
            await session.delete(row)
            return True

    async def list_markets(self, tenant_id: UUID, project_id: UUID) -> list[GeoMarketRecord]:
        if not await self._project_exists(tenant_id, project_id):
            return []
        return await self._list_scoped(
            GeoMarketRow,
            GeoMarketRow.project_id == project_id,
            _market_record,
        )

    async def create_market(
        self,
        tenant_id: UUID,
        project_id: UUID,
        command: GeoMarketCommand,
    ) -> GeoMarketRecord | None:
        if not await self._project_exists(tenant_id, project_id):
            return None
        now = _now()
        row = GeoMarketRow(
            id=uuid4(),
            project_id=project_id,
            region=command.region,
            language=command.language,
            market_name=command.market_name,
            prompt_locale_hint=command.prompt_locale_hint,
            serp_gl=command.serp_gl,
            serp_hl=command.serp_hl,
            serp_location=command.serp_location,
            status=command.status,
            created_at=now,
            updated_at=now,
        )
        async with self._session_scope() as session:
            session.add(row)
        return _market_record(row)

    async def update_market(
        self,
        tenant_id: UUID,
        market_id: UUID,
        command: GeoMarketCommand,
    ) -> GeoMarketRecord | None:
        async with self._session_scope() as session:
            row = await session.get(GeoMarketRow, market_id)
            if row is None or not await self._project_row_matches(session, tenant_id, row.project_id):
                return None
            row.region = command.region
            row.language = command.language
            row.market_name = command.market_name
            row.prompt_locale_hint = command.prompt_locale_hint
            row.serp_gl = command.serp_gl
            row.serp_hl = command.serp_hl
            row.serp_location = command.serp_location
            row.status = command.status
            row.updated_at = _now()
            return _market_record(row)

    async def delete_market(self, tenant_id: UUID, market_id: UUID) -> bool:
        return await self._delete_project_child(
            GeoMarketRow,
            market_id,
            tenant_id,
        )

    async def list_entities(
        self,
        tenant_id: UUID,
        project_id: UUID,
    ) -> list[GeoEntityRecord]:
        if not await self._project_exists(tenant_id, project_id):
            return []
        return await self._list_scoped(
            GeoEntityRow,
            GeoEntityRow.project_id == project_id,
            _entity_record,
        )

    async def get_entity(
        self,
        tenant_id: UUID,
        entity_id: UUID,
    ) -> GeoEntityRecord | None:
        async with self._session_scope() as session:
            row = await session.get(GeoEntityRow, entity_id)
            if row is None or not await self._project_row_matches(
                session,
                tenant_id,
                row.project_id,
            ):
                return None
            return _entity_record(row) if row is not None else None

    async def create_entity(
        self,
        tenant_id: UUID,
        project_id: UUID,
        command: GeoEntityCommand,
    ) -> GeoEntityRecord | None:
        if not await self._project_exists(tenant_id, project_id):
            return None
        now = _now()
        row = GeoEntityRow(
            id=uuid4(),
            project_id=project_id,
            entity_type=command.entity_type,
            name=command.name,
            website_url=command.website_url,
            description=command.description,
            status=command.status,
            created_at=now,
            updated_at=now,
        )
        async with self._session_scope() as session:
            session.add(row)
        return _entity_record(row)

    async def update_entity(
        self,
        tenant_id: UUID,
        entity_id: UUID,
        command: GeoEntityCommand,
    ) -> GeoEntityRecord | None:
        async with self._session_scope() as session:
            row = await session.get(GeoEntityRow, entity_id)
            if row is None or not await self._project_row_matches(
                session,
                tenant_id,
                row.project_id,
            ):
                return None
            row.entity_type = command.entity_type
            row.name = command.name
            row.website_url = command.website_url
            row.description = command.description
            row.status = command.status
            row.updated_at = _now()
            return _entity_record(row)

    async def delete_entity(self, tenant_id: UUID, entity_id: UUID) -> bool:
        return await self._delete_project_child(GeoEntityRow, entity_id, tenant_id)

    async def list_aliases(
        self,
        tenant_id: UUID,
        entity_id: UUID,
    ) -> list[GeoEntityAliasRecord]:
        if await self.get_entity(tenant_id, entity_id) is None:
            return []
        return await self._list_scoped(
            GeoEntityAliasRow,
            GeoEntityAliasRow.entity_id == entity_id,
            _alias_record,
        )

    async def create_alias(
        self,
        tenant_id: UUID,
        entity_id: UUID,
        command: GeoEntityAliasCommand,
    ) -> GeoEntityAliasRecord | None:
        if await self.get_entity(tenant_id, entity_id) is None:
            return None
        row = GeoEntityAliasRow(
            id=uuid4(),
            entity_id=entity_id,
            alias=command.alias,
            match_type=command.match_type,
            created_at=_now(),
        )
        async with self._session_scope() as session:
            session.add(row)
        return _alias_record(row)

    async def update_alias(
        self,
        tenant_id: UUID,
        alias_id: UUID,
        command: GeoEntityAliasCommand,
    ) -> GeoEntityAliasRecord | None:
        async with self._session_scope() as session:
            row = await session.get(GeoEntityAliasRow, alias_id)
            entity = (
                await session.get(GeoEntityRow, row.entity_id)
                if row is not None
                else None
            )
            if (
                row is None
                or entity is None
                or not await self._project_row_matches(
                    session,
                    tenant_id,
                    entity.project_id,
                )
            ):
                return None
            row.alias = command.alias
            row.match_type = command.match_type
            return _alias_record(row)

    async def delete_alias(self, tenant_id: UUID, alias_id: UUID) -> bool:
        async with self._session_scope() as session:
            row = await session.get(GeoEntityAliasRow, alias_id)
            entity = (
                await session.get(GeoEntityRow, row.entity_id)
                if row is not None
                else None
            )
            if (
                row is None
                or entity is None
                or not await self._project_row_matches(
                    session,
                    tenant_id,
                    entity.project_id,
                )
            ):
                return False
            await session.delete(row)
            return True

    async def list_topics(self, tenant_id: UUID, project_id: UUID) -> list[GeoTopicRecord]:
        if not await self._project_exists(tenant_id, project_id):
            return []
        return await self._list_scoped(
            GeoTopicRow,
            GeoTopicRow.project_id == project_id,
            _topic_record,
        )

    async def create_topic(
        self,
        tenant_id: UUID,
        project_id: UUID,
        command: GeoTopicCommand,
    ) -> GeoTopicRecord | None:
        if not await self._project_exists(tenant_id, project_id):
            return None
        now = _now()
        row = GeoTopicRow(
            id=uuid4(),
            project_id=project_id,
            name=command.name,
            description=command.description,
            status=command.status,
            created_at=now,
            updated_at=now,
        )
        async with self._session_scope() as session:
            session.add(row)
        return _topic_record(row)

    async def update_topic(
        self,
        tenant_id: UUID,
        topic_id: UUID,
        command: GeoTopicCommand,
    ) -> GeoTopicRecord | None:
        async with self._session_scope() as session:
            row = await session.get(GeoTopicRow, topic_id)
            if row is None or not await self._project_row_matches(
                session,
                tenant_id,
                row.project_id,
            ):
                return None
            row.name = command.name
            row.description = command.description
            row.status = command.status
            row.updated_at = _now()
            return _topic_record(row)

    async def delete_topic(self, tenant_id: UUID, topic_id: UUID) -> bool:
        return await self._delete_project_child(GeoTopicRow, topic_id, tenant_id)

    async def list_queries(self, tenant_id: UUID, project_id: UUID) -> list[GeoQueryRecord]:
        if not await self._project_exists(tenant_id, project_id):
            return []
        return await self._list_scoped(
            GeoQueryRow,
            GeoQueryRow.project_id == project_id,
            _query_record,
        )

    async def get_query(self, tenant_id: UUID, query_id: UUID) -> GeoQueryRecord | None:
        async with self._session_scope() as session:
            row = await self._get_query_row(session, tenant_id, query_id)
            return _query_record(row) if row is not None else None

    async def create_query(
        self,
        tenant_id: UUID,
        project_id: UUID,
        command: GeoQueryCommand,
    ) -> GeoQueryRecord | None:
        if not await self._project_exists(tenant_id, project_id):
            return None
        now = _now()
        row = GeoQueryRow(
            id=uuid4(),
            project_id=project_id,
            topic_id=command.topic_id,
            query_text=command.query_text,
            region=command.region,
            language=command.language,
            market_type=command.market_type,
            intent=command.intent,
            buyer_stage=command.buyer_stage,
            is_branded=command.is_branded,
            priority=command.priority,
            status=command.status,
            metadata_json=command.metadata,
            created_at=now,
            updated_at=now,
        )
        async with self._session_scope() as session:
            session.add(row)
        return _query_record(row)

    async def update_query(
        self,
        tenant_id: UUID,
        query_id: UUID,
        command: GeoQueryCommand,
    ) -> GeoQueryRecord | None:
        async with self._session_scope() as session:
            row = await self._get_query_row(session, tenant_id, query_id)
            if row is None:
                return None
            row.topic_id = command.topic_id
            row.query_text = command.query_text
            row.region = command.region
            row.language = command.language
            row.market_type = command.market_type
            row.intent = command.intent
            row.buyer_stage = command.buyer_stage
            row.is_branded = command.is_branded
            row.priority = command.priority
            row.status = command.status
            row.metadata_json = command.metadata
            row.updated_at = _now()
            return _query_record(row)

    async def delete_query(self, tenant_id: UUID, query_id: UUID) -> bool:
        async with self._session_scope() as session:
            row = await self._get_query_row(session, tenant_id, query_id)
            if row is None:
                return False
            await session.delete(row)
            return True

    async def list_query_platforms(
        self,
        tenant_id: UUID,
        query_id: UUID,
    ) -> list[GeoQueryPlatformRecord]:
        if await self.get_query(tenant_id, query_id) is None:
            return []
        return await self._list_scoped(
            GeoQueryPlatformRow,
            GeoQueryPlatformRow.query_id == query_id,
            _query_platform_record,
        )

    async def replace_query_platforms(
        self,
        tenant_id: UUID,
        query_id: UUID,
        commands: list[GeoQueryPlatformCommand],
    ) -> list[GeoQueryPlatformRecord] | None:
        if await self.get_query(tenant_id, query_id) is None:
            return None
        now = _now()
        rows = [
            GeoQueryPlatformRow(
                id=uuid4(),
                query_id=query_id,
                platform_id=command.platform_id,
                model=command.model,
                status=command.status,
                created_at=now,
                updated_at=now,
            )
            for command in commands
        ]
        async with self._session_scope() as session:
            await session.execute(
                delete(GeoQueryPlatformRow).where(
                    GeoQueryPlatformRow.query_id == query_id
                )
            )
            session.add_all(rows)
        return [_query_platform_record(row) for row in rows]

    async def list_schedules(
        self,
        tenant_id: UUID,
        query_id: UUID,
    ) -> list[GeoQueryScheduleRecord]:
        if await self.get_query(tenant_id, query_id) is None:
            return []
        return await self._list_scoped(
            GeoQueryScheduleRow,
            GeoQueryScheduleRow.query_id == query_id,
            _schedule_record,
        )

    async def create_schedule(
        self,
        tenant_id: UUID,
        query_id: UUID,
        command: GeoQueryScheduleCommand,
    ) -> GeoQueryScheduleRecord | None:
        if await self.get_query(tenant_id, query_id) is None:
            return None
        now = _now()
        row = GeoQueryScheduleRow(
            id=uuid4(),
            query_id=query_id,
            platform_id=command.platform_id,
            frequency=command.frequency,
            priority=command.priority,
            timezone=command.timezone,
            next_run_at=command.next_run_at,
            last_scheduled_at=None,
            status=command.status,
            created_at=now,
            updated_at=now,
        )
        async with self._session_scope() as session:
            session.add(row)
        return _schedule_record(row)

    async def update_schedule(
        self,
        tenant_id: UUID,
        schedule_id: UUID,
        command: GeoQueryScheduleCommand,
    ) -> GeoQueryScheduleRecord | None:
        async with self._session_scope() as session:
            row = await session.get(GeoQueryScheduleRow, schedule_id)
            if row is None or await self._get_query_row(session, tenant_id, row.query_id) is None:
                return None
            row.platform_id = command.platform_id
            row.frequency = command.frequency
            row.priority = command.priority
            row.timezone = command.timezone
            row.next_run_at = command.next_run_at
            row.status = command.status
            row.updated_at = _now()
            return _schedule_record(row)

    async def delete_schedule(self, tenant_id: UUID, schedule_id: UUID) -> bool:
        async with self._session_scope() as session:
            row = await session.get(GeoQueryScheduleRow, schedule_id)
            if row is None or await self._get_query_row(session, tenant_id, row.query_id) is None:
                return False
            await session.delete(row)
            return True

    async def create_job(
        self,
        tenant_id: UUID,
        query_id: UUID,
        command: CreateQueryRunJobCommand,
    ) -> GeoQueryRunJob | None:
        query = await self.get_query(tenant_id, query_id)
        if query is None:
            return None
        now = _now()
        scheduled_for = _normalize_datetime(command.scheduled_for or now)
        job = GeoQueryRunJob(
            id=uuid4(),
            project_id=query.project_id,
            query_id=query_id,
            platform_id=command.platform_id,
            schedule_id=None,
            job_type=command.job_type,
            priority=command.priority,
            scheduled_for=scheduled_for,
            status=JobStatus.PENDING,
            attempt_count=0,
            max_attempts=3,
            dedupe_key=(
                f"{query.project_id}:{query_id}:{command.platform_id}:"
                f"{scheduled_for.isoformat()}"
            ),
            created_at=now,
            updated_at=now,
        )
        async with self._session_scope() as session:
            session.add(_job_row(job))
        return job

    async def list_jobs(self, tenant_id: UUID, project_id: UUID) -> list[GeoQueryRunJob]:
        if not await self._project_exists(tenant_id, project_id):
            return []
        statement = (
            select(GeoQueryRunJobRow)
            .where(GeoQueryRunJobRow.project_id == project_id)
            .order_by(GeoQueryRunJobRow.created_at.desc())
        )
        async with self._session_scope() as session:
            rows = (await session.scalars(statement)).all()
            return [_job_from_row(row) for row in rows]

    async def get(self, job_id: UUID) -> GeoQueryRunJob:
        async with self._session_scope() as session:
            row = await session.get(GeoQueryRunJobRow, job_id)
            if row is None:
                raise KeyError(job_id)
            return _job_from_row(row)

    async def get_job(self, tenant_id: UUID, job_id: UUID) -> GeoQueryRunJob | None:
        async with self._session_scope() as session:
            row = await self._get_job_row(session, tenant_id, job_id)
            return _job_from_row(row) if row is not None else None

    async def get_job_tenant_id(self, job_id: UUID) -> UUID | None:
        async with self._session_scope() as session:
            return await session.scalar(
                select(GeoProjectRow.tenant_id)
                .join(GeoQueryRunJobRow, GeoQueryRunJobRow.project_id == GeoProjectRow.id)
                .where(GeoQueryRunJobRow.id == job_id)
            )

    async def get_job_dispatch_context(
        self,
        job_id: UUID,
    ) -> GeoQueryRunJobDispatchContext | None:
        async with self._session_scope() as session:
            row = await session.get(GeoQueryRunJobRow, job_id)
            if row is None:
                return None
            query = await session.get(GeoQueryRow, row.query_id)
            project = await session.get(GeoProjectRow, row.project_id)
            platform = await session.get(GeoAiPlatformRow, row.platform_id)
            if query is None or project is None or platform is None:
                return None
            topic_name = ""
            if query.topic_id is not None:
                topic = await session.get(GeoTopicRow, query.topic_id)
                topic_name = topic.name if topic is not None else ""
            query_platform = await session.scalar(
                select(GeoQueryPlatformRow).where(
                    GeoQueryPlatformRow.query_id == row.query_id,
                    GeoQueryPlatformRow.platform_id == row.platform_id,
                )
            )
            return GeoQueryRunJobDispatchContext(
                job_id=row.id,
                tenant_id=project.tenant_id,
                project_id=row.project_id,
                seo_task_id=project.seo_task_id,
                query_id=row.query_id,
                query_text=query.query_text,
                topic_name=topic_name,
                platform=platform.code,
                model=(
                    query_platform.model
                    if query_platform is not None and query_platform.model
                    else platform.default_model
                ),
                region=query.region,
                language=query.language,
                market_type=query.market_type,
                is_branded=query.is_branded,
                scheduled_for=row.scheduled_for,
            )

    async def save(self, job: GeoQueryRunJob) -> None:
        async with self._session_scope() as session:
            row = await session.get(GeoQueryRunJobRow, job.id)
            if row is None:
                row = _job_row(job)
                session.add(row)
            else:
                _apply_job(row, job)

    async def record_dispatch(
        self,
        *,
        job_id: UUID,
        result: PublishResult,
        payload: QueryRunJobMessage,
        occurred_at: datetime,
    ) -> None:
        row = GeoMessageDispatchLogRow(
            id=uuid4(),
            job_id=job_id,
            message_backend=result.backend,
            destination=result.destination,
            message_id=result.message_id,
            payload=payload.model_dump(mode="json", by_alias=True),
            publish_status=result.status,
            published_at=occurred_at if result.status == "published" else None,
            error_message=result.error_message,
            created_at=occurred_at,
        )
        event = GeoJobDispatchEventRow(
            id=uuid4(),
            job_id=job_id,
            event_type="published" if result.status == "published" else "publish_failed",
            occurred_at=occurred_at,
            actor="broker",
            metadata_json={"destination": result.destination},
        )
        async with self._session_scope() as session:
            session.add(row)
            session.add(event)

    async def record_external_callback(
        self,
        *,
        callback: ExternalRunCallback,
        occurred_at: datetime,
    ) -> None:
        async with self._session_scope() as session:
            session.add(_external_reference_row(callback, occurred_at))
            session.add(_external_callback_event_row(callback, occurred_at))

    async def apply_external_callback(
        self,
        *,
        callback: ExternalRunCallback,
        occurred_at: datetime,
    ) -> GeoQueryRunJob:
        async with self._session_scope() as session:
            row = await session.get(GeoQueryRunJobRow, callback.job_id)
            if row is None:
                raise KeyError(callback.job_id)
            job = _job_from_row(row)
            job.mark_external_status(
                external_run_id=callback.external_run_id,
                external_status=callback.status,
                error_code=callback.error_code,
                error_message=callback.error_message,
                now=occurred_at,
            )
            _apply_job(row, job)
            session.add(_external_reference_row(callback, occurred_at))
            session.add(_external_callback_event_row(callback, occurred_at))
            return job

    async def save_tracking_run_result(
        self,
        *,
        command: SaveTrackingRunResultCommand,
        occurred_at: datetime,
    ) -> GeoQueryRunJob:
        callback = _tracking_command_callback(command)
        async with self._session_scope() as session:
            row = await session.get(GeoQueryRunJobRow, command.message.job_id)
            if row is None:
                raise KeyError(command.message.job_id)
            project = await session.get(GeoProjectRow, row.project_id)
            if project is None or project.tenant_id != command.message.tenant_id:
                raise KeyError(command.message.job_id)
            job = _job_from_row(row)
            job.mark_external_status(
                external_run_id=callback.external_run_id,
                external_status=callback.status,
                error_code=callback.error_code,
                error_message=callback.error_message,
                now=occurred_at,
            )
            _apply_job(row, job)
            run_request = _run_request_row(command, occurred_at)
            session.add(run_request)
            for result in command.response.results if command.response else []:
                result_row = _run_result_row(
                    run_request_id=run_request.id,
                    job_id=command.message.job_id,
                    result=result,
                    occurred_at=occurred_at,
                )
                session.add(result_row)
                await session.flush()
                for position, reference in enumerate(
                    _result_references(result),
                    start=1,
                ):
                    session.add(
                        _run_result_reference_row(
                            run_result_id=result_row.id,
                            url=reference[0],
                            title=reference[1],
                            position=position,
                        )
                    )
            session.add(_external_reference_row(callback, occurred_at))
            session.add(_external_callback_event_row(callback, occurred_at))
            return job

    async def list_job_run_results(
        self,
        tenant_id: UUID,
        job_id: UUID,
    ) -> list[GeoRunResultRecord]:
        async with self._session_scope() as session:
            rows = (
                await session.scalars(
                    select(GeoRunResultRow)
                    .join(
                        GeoQueryRunJobRow,
                        GeoRunResultRow.job_id == GeoQueryRunJobRow.id,
                    )
                    .join(GeoProjectRow, GeoQueryRunJobRow.project_id == GeoProjectRow.id)
                    .where(
                        GeoRunResultRow.job_id == job_id,
                        GeoProjectRow.tenant_id == tenant_id,
                    )
                    .order_by(GeoRunResultRow.run_at.desc())
                )
            ).all()
            return [await _run_result_record(session, row) for row in rows]

    async def list_project_run_results(
        self,
        tenant_id: UUID,
        project_id: UUID,
    ) -> list[GeoRunResultRecord]:
        async with self._session_scope() as session:
            rows = (
                await session.scalars(
                    select(GeoRunResultRow)
                    .join(
                        GeoQueryRunJobRow,
                        GeoRunResultRow.job_id == GeoQueryRunJobRow.id,
                    )
                    .join(GeoProjectRow, GeoQueryRunJobRow.project_id == GeoProjectRow.id)
                    .where(
                        GeoQueryRunJobRow.project_id == project_id,
                        GeoProjectRow.tenant_id == tenant_id,
                    )
                    .order_by(GeoRunResultRow.run_at.desc())
                )
            ).all()
            return [await _run_result_record(session, row) for row in rows]

    async def get_run_result(
        self,
        tenant_id: UUID,
        result_id: UUID,
    ) -> GeoRunResultRecord | None:
        async with self._session_scope() as session:
            row = await session.scalar(
                select(GeoRunResultRow)
                .join(
                    GeoQueryRunJobRow,
                    GeoRunResultRow.job_id == GeoQueryRunJobRow.id,
                )
                .join(GeoProjectRow, GeoQueryRunJobRow.project_id == GeoProjectRow.id)
                .where(
                    GeoRunResultRow.id == result_id,
                    GeoProjectRow.tenant_id == tenant_id,
                )
            )
            if row is None:
                return None
            return await _run_result_record(session, row)

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
        if not await self._project_exists(tenant_id, project_id):
            return None
        row = GeoQueryResearchRunRow(
            id=uuid4(),
            project_id=project_id,
            provider=command.provider,
            status=status,
            request_payload=request_payload,
            research_context=(result or {}).get("researchContext"),
            searched_keywords=(result or {}).get("searchedKeywords", []),
            source_urls=(result or {}).get("sourceUrls", []),
            error_code="query_research_failed" if error_message else None,
            error_message=error_message,
            created_at=occurred_at,
            completed_at=occurred_at,
        )
        async with self._session_scope() as session:
            session.add(row)
            return _research_run_record(row)

    async def list_query_research_runs(
        self,
        tenant_id: UUID,
        project_id: UUID,
    ) -> list[QueryResearchRunRecord]:
        async with self._session_scope() as session:
            rows = (
                await session.scalars(
                    select(GeoQueryResearchRunRow)
                    .join(
                        GeoProjectRow,
                        GeoQueryResearchRunRow.project_id == GeoProjectRow.id,
                    )
                    .where(
                        GeoQueryResearchRunRow.project_id == project_id,
                        GeoProjectRow.tenant_id == tenant_id,
                    )
                    .order_by(GeoQueryResearchRunRow.created_at.desc())
                )
            ).all()
            return [_research_run_record(row) for row in rows]

    async def get_query_research_run(
        self,
        tenant_id: UUID,
        run_id: UUID,
    ) -> QueryResearchRunRecord | None:
        async with self._session_scope() as session:
            row = await session.scalar(
                select(GeoQueryResearchRunRow)
                .join(GeoProjectRow, GeoQueryResearchRunRow.project_id == GeoProjectRow.id)
                .where(
                    GeoQueryResearchRunRow.id == run_id,
                    GeoProjectRow.tenant_id == tenant_id,
                )
            )
            return _research_run_record(row) if row is not None else None

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
        if not await self._project_exists(tenant_id, project_id):
            return None
        run = GeoQueryGenerationRunRow(
            id=uuid4(),
            project_id=project_id,
            provider=command.provider,
            status=status,
            request_payload=request_payload,
            error_code="query_generation_failed" if error_message else None,
            error_message=error_message,
            created_at=occurred_at,
            completed_at=occurred_at,
        )
        async with self._session_scope() as session:
            session.add(run)
            await session.flush()
            draft_rows = [
                _draft_row(
                    project_id,
                    run.id,
                    query,
                    occurred_at,
                    await _existing_topic_id(session, query.get("topicId")),
                )
                for query in (result or {}).get("queries", [])
            ]
            session.add_all(draft_rows)
            return _generation_run_record(run, draft_rows)

    async def list_query_generation_runs(
        self,
        tenant_id: UUID,
        project_id: UUID,
    ) -> list[QueryGenerationRunRecord]:
        async with self._session_scope() as session:
            rows = (
                await session.scalars(
                    select(GeoQueryGenerationRunRow)
                    .join(
                        GeoProjectRow,
                        GeoQueryGenerationRunRow.project_id == GeoProjectRow.id,
                    )
                    .where(
                        GeoQueryGenerationRunRow.project_id == project_id,
                        GeoProjectRow.tenant_id == tenant_id,
                    )
                    .order_by(GeoQueryGenerationRunRow.created_at.desc())
                )
            ).all()
            return [_generation_run_record(row, []) for row in rows]

    async def get_query_generation_run(
        self,
        tenant_id: UUID,
        run_id: UUID,
    ) -> QueryGenerationRunRecord | None:
        async with self._session_scope() as session:
            row = await session.scalar(
                select(GeoQueryGenerationRunRow)
                .join(GeoProjectRow, GeoQueryGenerationRunRow.project_id == GeoProjectRow.id)
                .where(
                    GeoQueryGenerationRunRow.id == run_id,
                    GeoProjectRow.tenant_id == tenant_id,
                )
            )
            if row is None:
                return None
            drafts = (
                await session.scalars(
                    select(GeoQueryDraftRow)
                    .where(GeoQueryDraftRow.generation_run_id == run_id)
                    .order_by(GeoQueryDraftRow.created_at)
                )
            ).all()
            return _generation_run_record(row, drafts)

    async def update_query_draft_selection(
        self,
        tenant_id: UUID,
        draft_id: UUID,
        command: QueryDraftSelectionCommand,
    ) -> QueryDraftRecord | None:
        async with self._session_scope() as session:
            row = await session.scalar(
                select(GeoQueryDraftRow)
                .join(GeoProjectRow, GeoQueryDraftRow.project_id == GeoProjectRow.id)
                .where(
                    GeoQueryDraftRow.id == draft_id,
                    GeoProjectRow.tenant_id == tenant_id,
                )
            )
            if row is None:
                return None
            if row.accepted_query_id is not None:
                raise ValueError("query draft already accepted")
            row.selection_status = command.selection_status
            row.updated_at = _now()
            session.add(
                GeoQueryDraftSelectionRow(
                    id=uuid4(),
                    draft_id=draft_id,
                    selection_status=command.selection_status,
                    query_id=None,
                    created_at=row.updated_at,
                )
            )
            return _draft_record(row)

    async def accept_query_draft(
        self,
        tenant_id: UUID,
        draft_id: UUID,
        command: AcceptQueryDraftCommand,
    ) -> GeoQueryRecord | None:
        async with self._session_scope() as session:
            draft = await session.scalar(
                select(GeoQueryDraftRow)
                .join(GeoProjectRow, GeoQueryDraftRow.project_id == GeoProjectRow.id)
                .where(
                    GeoQueryDraftRow.id == draft_id,
                    GeoProjectRow.tenant_id == tenant_id,
                )
            )
            if draft is None:
                return None
            if draft.accepted_query_id is not None:
                raise ValueError("query draft already accepted")
            topic_id = await _resolve_draft_topic(session, draft, command)
            now = _now()
            query = GeoQueryRow(
                id=uuid4(),
                project_id=draft.project_id,
                topic_id=topic_id,
                query_text=draft.query_text,
                region=draft.region,
                language=draft.language,
                market_type=draft.market_type,
                intent=draft.intent,
                buyer_stage=None,
                is_branded=draft.is_branded,
                priority="normal",
                status=command.status,
                metadata_json=draft.metadata_json,
                created_at=now,
                updated_at=now,
            )
            session.add(query)
            await session.flush()
            draft.selection_status = "accepted"
            draft.accepted_query_id = query.id
            draft.updated_at = now
            session.add(
                GeoQueryDraftSelectionRow(
                    id=uuid4(),
                    draft_id=draft.id,
                    selection_status="accepted",
                    query_id=query.id,
                    created_at=now,
                )
            )
            return _query_record(query)

    async def _exists(self, model, item_id: UUID) -> bool:
        async with self._session_scope() as session:
            return await session.get(model, item_id) is not None

    async def _project_exists(self, tenant_id: UUID, project_id: UUID) -> bool:
        async with self._session_scope() as session:
            return await self._get_project_row(session, tenant_id, project_id) is not None

    async def _project_record_for(self, statement) -> GeoProjectRecord | None:
        async with self._session_scope() as session:
            row = await session.scalar(statement)
            return _project_record(row) if row is not None else None

    async def _get_project_row(
        self,
        session: AsyncSession,
        tenant_id: UUID,
        project_id: UUID,
    ) -> GeoProjectRow | None:
        return await session.scalar(
            select(GeoProjectRow).where(
                GeoProjectRow.id == project_id,
                GeoProjectRow.tenant_id == tenant_id,
            )
        )

    async def _project_row_matches(
        self,
        session: AsyncSession,
        tenant_id: UUID,
        project_id: UUID,
    ) -> bool:
        return await self._get_project_row(session, tenant_id, project_id) is not None

    async def _get_query_row(
        self,
        session: AsyncSession,
        tenant_id: UUID,
        query_id: UUID,
    ) -> GeoQueryRow | None:
        return await session.scalar(
            select(GeoQueryRow)
            .join(GeoProjectRow, GeoProjectRow.id == GeoQueryRow.project_id)
            .where(
                GeoQueryRow.id == query_id,
                GeoProjectRow.tenant_id == tenant_id,
            )
        )

    async def _delete_project_child(self, model, item_id: UUID, tenant_id: UUID) -> bool:
        async with self._session_scope() as session:
            row = await session.get(model, item_id)
            if (
                row is None
                or not await self._project_row_matches(session, tenant_id, row.project_id)
            ):
                return False
            await session.delete(row)
            return True

    async def _get_job_row(
        self,
        session: AsyncSession,
        tenant_id: UUID,
        job_id: UUID,
    ) -> GeoQueryRunJobRow | None:
        return await session.scalar(
            select(GeoQueryRunJobRow)
            .join(GeoProjectRow, GeoProjectRow.id == GeoQueryRunJobRow.project_id)
            .where(
                GeoQueryRunJobRow.id == job_id,
                GeoProjectRow.tenant_id == tenant_id,
            )
        )

    async def _delete(self, model, item_id: UUID) -> bool:
        async with self._session_scope() as session:
            row = await session.get(model, item_id)
            if row is None:
                return False
            await session.delete(row)
            return True

    async def _list_scoped(self, model, criterion, mapper):
        statement = select(model).where(criterion)
        async with self._session_scope() as session:
            rows = (await session.scalars(statement)).all()
            return [mapper(row) for row in rows]

    @asynccontextmanager
    async def _session_scope(self) -> AsyncIterator[AsyncSession]:
        async with self._session_factory() as session:
            async with session.begin():
                yield session


def _now() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


def _normalize_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).replace(microsecond=0)


def _project_record(row: GeoProjectRow) -> GeoProjectRecord:
    return GeoProjectRecord(
        id=row.id,
        tenant_id=row.tenant_id,
        customer_id=row.customer_id,
        seo_task_id=row.seo_task_id,
        name=row.name,
        default_region=row.default_region,
        default_language=row.default_language,
        status=row.status,
        daily_run_budget=row.daily_run_budget,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _market_record(row: GeoMarketRow) -> GeoMarketRecord:
    return GeoMarketRecord(
        id=row.id,
        project_id=row.project_id,
        region=row.region,
        language=row.language,
        market_name=row.market_name,
        prompt_locale_hint=row.prompt_locale_hint,
        serp_gl=row.serp_gl,
        serp_hl=row.serp_hl,
        serp_location=row.serp_location,
        status=row.status,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _entity_record(row: GeoEntityRow) -> GeoEntityRecord:
    return GeoEntityRecord(
        id=row.id,
        project_id=row.project_id,
        entity_type=row.entity_type,
        name=row.name,
        website_url=row.website_url,
        description=row.description,
        status=row.status,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _alias_record(row: GeoEntityAliasRow) -> GeoEntityAliasRecord:
    return GeoEntityAliasRecord(
        id=row.id,
        entity_id=row.entity_id,
        alias=row.alias,
        match_type=row.match_type,
        created_at=row.created_at,
    )


def _topic_record(row: GeoTopicRow) -> GeoTopicRecord:
    return GeoTopicRecord(
        id=row.id,
        project_id=row.project_id,
        name=row.name,
        description=row.description,
        status=row.status,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _query_record(row: GeoQueryRow) -> GeoQueryRecord:
    return GeoQueryRecord(
        id=row.id,
        project_id=row.project_id,
        topic_id=row.topic_id,
        query_text=row.query_text,
        region=row.region,
        language=row.language,
        market_type=row.market_type,
        intent=row.intent,
        buyer_stage=row.buyer_stage,
        is_branded=row.is_branded,
        priority=row.priority,
        status=row.status,
        metadata=row.metadata_json,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _research_run_record(row: GeoQueryResearchRunRow) -> QueryResearchRunRecord:
    return QueryResearchRunRecord(
        id=row.id,
        project_id=row.project_id,
        provider=row.provider,
        status=row.status,
        request_payload=row.request_payload,
        result=(
            QueryResearchResultRecord(
                research_context=row.research_context or "",
                searched_keywords=row.searched_keywords,
                source_urls=row.source_urls,
            )
            if row.research_context is not None
            else None
        ),
        error_code=row.error_code,
        error_message=row.error_message,
        created_at=row.created_at,
        completed_at=row.completed_at,
    )


def _generation_run_record(
    row: GeoQueryGenerationRunRow,
    drafts: list[GeoQueryDraftRow],
) -> QueryGenerationRunRecord:
    return QueryGenerationRunRecord(
        id=row.id,
        project_id=row.project_id,
        provider=row.provider,
        status=row.status,
        request_payload=row.request_payload,
        error_code=row.error_code,
        error_message=row.error_message,
        created_at=row.created_at,
        completed_at=row.completed_at,
        drafts=[_draft_record(draft) for draft in drafts],
    )


def _draft_row(
    project_id: UUID,
    run_id: UUID,
    query: dict,
    occurred_at: datetime,
    topic_id: UUID | None,
) -> GeoQueryDraftRow:
    attributes = query.get("attributes") or {}
    intent = attributes.get("intent") or {}
    return GeoQueryDraftRow(
        id=uuid4(),
        generation_run_id=run_id,
        project_id=project_id,
        topic_id=topic_id,
        topic_name=query.get("topicName") or attributes.get("topicName") or "",
        query_text=query.get("queryText") or query.get("text") or query.get("query") or "",
        keywords=query.get("keywords", []),
        region=query.get("region", "TW"),
        language=query.get("language", "zh-TW"),
        market_type=query.get("marketType", "b2b_procurement"),
        intent=intent.get("category"),
        is_branded=query.get("isBranded", False),
        status="draft",
        metadata_json=query.get("metadata", {}),
        created_at=occurred_at,
        updated_at=occurred_at,
    )


async def _existing_topic_id(
    session: AsyncSession,
    value: object,
) -> UUID | None:
    if value is None:
        return None
    try:
        topic_id = value if isinstance(value, UUID) else UUID(str(value))
    except (TypeError, ValueError):
        return None
    return topic_id if await session.get(GeoTopicRow, topic_id) is not None else None


def _draft_record(row: GeoQueryDraftRow) -> QueryDraftRecord:
    return QueryDraftRecord(
        id=row.id,
        generation_run_id=row.generation_run_id,
        project_id=row.project_id,
        topic_id=row.topic_id,
        topic_name=row.topic_name,
        query_text=row.query_text,
        keywords=row.keywords,
        region=row.region,
        language=row.language,
        market_type=row.market_type,
        intent=row.intent,
        is_branded=row.is_branded,
        status=row.status,
        selection_status=row.selection_status,
        accepted_query_id=row.accepted_query_id,
        metadata=row.metadata_json,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


async def _resolve_draft_topic(
    session: AsyncSession,
    draft: GeoQueryDraftRow,
    command: AcceptQueryDraftCommand,
) -> UUID | None:
    if draft.topic_id is not None:
        return draft.topic_id
    if not draft.topic_name:
        return None
    topic = await session.scalar(
        select(GeoTopicRow).where(
            GeoTopicRow.project_id == draft.project_id,
            GeoTopicRow.name == draft.topic_name,
        )
    )
    if topic is not None:
        return topic.id
    if not command.create_topic_if_missing:
        return None
    now = _now()
    topic = GeoTopicRow(
        id=uuid4(),
        project_id=draft.project_id,
        name=draft.topic_name,
        description="",
        status="active",
        created_at=now,
        updated_at=now,
    )
    session.add(topic)
    await session.flush()
    return topic.id


def _query_platform_record(row: GeoQueryPlatformRow) -> GeoQueryPlatformRecord:
    return GeoQueryPlatformRecord(
        id=row.id,
        query_id=row.query_id,
        platform_id=row.platform_id,
        model=row.model,
        status=row.status,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _schedule_record(row: GeoQueryScheduleRow) -> GeoQueryScheduleRecord:
    return GeoQueryScheduleRecord(
        id=row.id,
        query_id=row.query_id,
        platform_id=row.platform_id,
        frequency=row.frequency,
        priority=row.priority,
        timezone=row.timezone,
        next_run_at=row.next_run_at,
        last_scheduled_at=row.last_scheduled_at,
        status=row.status,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _job_row(job: GeoQueryRunJob) -> GeoQueryRunJobRow:
    return GeoQueryRunJobRow(
        id=job.id,
        project_id=job.project_id,
        query_id=job.query_id,
        platform_id=job.platform_id,
        schedule_id=job.schedule_id,
        job_type=job.job_type,
        priority=job.priority,
        scheduled_for=job.scheduled_for,
        status=job.status.value,
        attempt_count=job.attempt_count,
        max_attempts=job.max_attempts,
        next_retry_at=job.next_retry_at,
        dedupe_key=job.dedupe_key,
        dispatch_backend=job.dispatch_backend,
        dispatch_message_id=job.dispatch_message_id,
        external_run_id=job.external_run_id,
        last_error_code=job.last_error_code,
        last_error_message=job.last_error_message,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


def _external_reference_row(
    callback: ExternalRunCallback,
    occurred_at: datetime,
) -> GeoExternalRunReferenceRow:
    return GeoExternalRunReferenceRow(
        id=uuid4(),
        job_id=callback.job_id,
        external_system="geo-tracking",
        external_run_id=callback.external_run_id,
        external_status=callback.status,
        callback_received_at=occurred_at,
        result_location=callback.result_location,
        metadata_json={
            "errorCode": callback.error_code,
            "errorMessage": callback.error_message,
        },
        created_at=occurred_at,
        updated_at=occurred_at,
    )


def _external_callback_event_row(
    callback: ExternalRunCallback,
    occurred_at: datetime,
) -> GeoJobDispatchEventRow:
    return GeoJobDispatchEventRow(
        id=uuid4(),
        job_id=callback.job_id,
        event_type=f"callback_{callback.status}",
        occurred_at=occurred_at,
        actor="external_runner",
        metadata_json={"externalRunId": callback.external_run_id},
    )


def _tracking_command_callback(
    command: SaveTrackingRunResultCommand,
) -> ExternalRunCallback:
    external_run_id = command.response.id if command.response is not None else "unknown"
    return ExternalRunCallback(
        job_id=command.message.job_id,
        external_run_id=external_run_id,
        status=command.status,
        error_code=command.error_code,
        error_message=command.error_message,
    )


def _run_request_row(
    command: SaveTrackingRunResultCommand,
    occurred_at: datetime,
) -> GeoRunRequestRow:
    response = command.response
    return GeoRunRequestRow(
        id=uuid4(),
        job_id=command.message.job_id,
        tracking_run_request_id=response.id if response is not None else "unknown",
        seo_task_id=command.message.seo_task_id,
        provider=command.message.platform,
        timing=response.timing if response is not None else "run_now",
        status=command.status,
        error_code=command.error_code,
        error_message=command.error_message,
        request_payload=command.request_payload,
        created_at=occurred_at,
        completed_at=occurred_at,
    )


def _run_result_row(
    *,
    run_request_id: UUID,
    job_id: UUID,
    result,
    occurred_at: datetime,
) -> GeoRunResultRow:
    return GeoRunResultRow(
        id=uuid4(),
        run_request_id=run_request_id,
        job_id=job_id,
        tracking_result_id=result.id,
        query_id=result.query_id,
        provider=result.provider,
        surface=result.surface,
        model=result.model,
        region=result.region,
        language=result.language,
        status=result.status,
        raw_response=result.raw_response,
        error=result.error,
        run_at=result.run_at,
        created_at=occurred_at,
    )


def _run_result_reference_row(
    *,
    run_result_id: UUID,
    url: str,
    title: str | None,
    position: int,
) -> GeoRunResultReferenceRow:
    return GeoRunResultReferenceRow(
        id=uuid4(),
        run_result_id=run_result_id,
        url=url,
        title=title,
        domain=_url_domain(url),
        position=position,
    )


def _result_references(result) -> list[tuple[str, str | None]]:
    if result.references:
        return [(reference.url, reference.title) for reference in result.references]
    return [(url, None) for url in result.reference_urls]


async def _run_result_record(
    session: AsyncSession,
    row: GeoRunResultRow,
) -> GeoRunResultRecord:
    references = (
        await session.scalars(
            select(GeoRunResultReferenceRow)
            .where(GeoRunResultReferenceRow.run_result_id == row.id)
            .order_by(GeoRunResultReferenceRow.position)
        )
    ).all()
    return GeoRunResultRecord(
        id=row.id,
        run_request_id=row.run_request_id,
        job_id=row.job_id,
        tracking_result_id=row.tracking_result_id,
        query_id=row.query_id,
        provider=row.provider,
        surface=row.surface,
        model=row.model,
        region=row.region,
        language=row.language,
        status=row.status,
        raw_response=row.raw_response,
        error=row.error,
        run_at=row.run_at,
        references=[
            GeoRunResultReferenceRecord(
                id=reference.id,
                run_result_id=reference.run_result_id,
                url=reference.url,
                title=reference.title,
                domain=reference.domain,
                position=reference.position,
            )
            for reference in references
        ],
        created_at=row.created_at,
    )


def _url_domain(url: str) -> str | None:
    parsed = urlparse(url)
    return parsed.netloc.lower() or None


def _job_from_row(row: GeoQueryRunJobRow) -> GeoQueryRunJob:
    return GeoQueryRunJob(
        id=row.id,
        project_id=row.project_id,
        query_id=row.query_id,
        platform_id=row.platform_id,
        schedule_id=row.schedule_id,
        job_type=row.job_type,
        priority=row.priority,
        scheduled_for=row.scheduled_for,
        status=JobStatus(row.status),
        attempt_count=row.attempt_count,
        max_attempts=row.max_attempts,
        dedupe_key=row.dedupe_key,
        created_at=row.created_at,
        updated_at=row.updated_at,
        next_retry_at=row.next_retry_at,
        dispatch_backend=row.dispatch_backend,
        dispatch_message_id=row.dispatch_message_id,
        external_run_id=row.external_run_id,
        last_error_code=row.last_error_code,
        last_error_message=row.last_error_message,
    )


def _apply_job(row: GeoQueryRunJobRow, job: GeoQueryRunJob) -> None:
    row.project_id = job.project_id
    row.query_id = job.query_id
    row.platform_id = job.platform_id
    row.schedule_id = job.schedule_id
    row.job_type = job.job_type
    row.priority = job.priority
    row.scheduled_for = job.scheduled_for
    row.status = job.status.value
    row.attempt_count = job.attempt_count
    row.max_attempts = job.max_attempts
    row.next_retry_at = job.next_retry_at
    row.dedupe_key = job.dedupe_key
    row.dispatch_backend = job.dispatch_backend
    row.dispatch_message_id = job.dispatch_message_id
    row.external_run_id = job.external_run_id
    row.last_error_code = job.last_error_code
    row.last_error_message = job.last_error_message
    row.created_at = job.created_at
    row.updated_at = job.updated_at
