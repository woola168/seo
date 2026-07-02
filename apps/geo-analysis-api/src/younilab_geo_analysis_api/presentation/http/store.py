from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from urllib.parse import urlparse
from uuid import UUID, uuid4

from younilab_seo.geo_analysis.application import (
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


@dataclass
class GeoApiStore:
    """測試用 in-memory GEO repository fake。"""

    projects: dict[UUID, GeoProjectRecord] = field(default_factory=dict)
    markets: dict[UUID, GeoMarketRecord] = field(default_factory=dict)
    entities: dict[UUID, GeoEntityRecord] = field(default_factory=dict)
    aliases: dict[UUID, GeoEntityAliasRecord] = field(default_factory=dict)
    topics: dict[UUID, GeoTopicRecord] = field(default_factory=dict)
    queries: dict[UUID, GeoQueryRecord] = field(default_factory=dict)
    query_platforms: dict[UUID, GeoQueryPlatformRecord] = field(default_factory=dict)
    schedules: dict[UUID, GeoQueryScheduleRecord] = field(default_factory=dict)
    jobs: dict[UUID, GeoQueryRunJob] = field(default_factory=dict)
    run_results: dict[UUID, GeoRunResultRecord] = field(default_factory=dict)
    query_research_runs: dict[UUID, QueryResearchRunRecord] = field(
        default_factory=dict
    )
    query_generation_runs: dict[UUID, QueryGenerationRunRecord] = field(
        default_factory=dict
    )
    query_drafts: dict[UUID, QueryDraftRecord] = field(default_factory=dict)
    platform_codes: dict[UUID, str] = field(default_factory=dict)
    platform_models: dict[UUID, str | None] = field(default_factory=dict)
    dispatches: list[tuple[UUID, PublishResult, QueryRunJobMessage, datetime]] = field(
        default_factory=list
    )
    callbacks: list[tuple[ExternalRunCallback, datetime]] = field(default_factory=list)

    async def list_projects(
        self,
        tenant_id: UUID,
        customer_id: UUID | None = None,
    ) -> list[GeoProjectRecord]:
        items = [
            item for item in self.projects.values() if item.tenant_id == tenant_id
        ]
        if customer_id is not None:
            items = [item for item in items if item.customer_id == customer_id]
        return items

    async def get_project(
        self,
        tenant_id: UUID,
        project_id: UUID,
    ) -> GeoProjectRecord | None:
        project = self.projects.get(project_id)
        if project is None or project.tenant_id != tenant_id:
            return None
        return project

    async def get_query_project(
        self,
        tenant_id: UUID,
        query_id: UUID,
    ) -> GeoProjectRecord | None:
        query = self.queries.get(query_id)
        if query is None:
            return None
        return await self.get_project(tenant_id, query.project_id)

    async def get_market_project(
        self,
        tenant_id: UUID,
        market_id: UUID,
    ) -> GeoProjectRecord | None:
        market = self.markets.get(market_id)
        if market is None:
            return None
        return await self.get_project(tenant_id, market.project_id)

    async def get_entity_project(
        self,
        tenant_id: UUID,
        entity_id: UUID,
    ) -> GeoProjectRecord | None:
        entity = self.entities.get(entity_id)
        if entity is None:
            return None
        return await self.get_project(tenant_id, entity.project_id)

    async def get_alias_project(
        self,
        tenant_id: UUID,
        alias_id: UUID,
    ) -> GeoProjectRecord | None:
        alias = self.aliases.get(alias_id)
        if alias is None:
            return None
        return await self.get_entity_project(tenant_id, alias.entity_id)

    async def get_topic_project(
        self,
        tenant_id: UUID,
        topic_id: UUID,
    ) -> GeoProjectRecord | None:
        topic = self.topics.get(topic_id)
        if topic is None:
            return None
        return await self.get_project(tenant_id, topic.project_id)

    async def get_schedule_project(
        self,
        tenant_id: UUID,
        schedule_id: UUID,
    ) -> GeoProjectRecord | None:
        schedule = self.schedules.get(schedule_id)
        if schedule is None:
            return None
        return await self.get_query_project(tenant_id, schedule.query_id)

    async def get_job_project(
        self,
        tenant_id: UUID,
        job_id: UUID,
    ) -> GeoProjectRecord | None:
        job = self.jobs.get(job_id)
        if job is None:
            return None
        return await self.get_project(tenant_id, job.project_id)

    async def get_run_result_project(
        self,
        tenant_id: UUID,
        result_id: UUID,
    ) -> GeoProjectRecord | None:
        result = self.run_results.get(result_id)
        if result is None:
            return None
        return await self.get_job_project(tenant_id, result.job_id)

    async def get_query_research_run_project(
        self,
        tenant_id: UUID,
        run_id: UUID,
    ) -> GeoProjectRecord | None:
        run = self.query_research_runs.get(run_id)
        if run is None:
            return None
        return await self.get_project(tenant_id, run.project_id)

    async def get_query_generation_run_project(
        self,
        tenant_id: UUID,
        run_id: UUID,
    ) -> GeoProjectRecord | None:
        run = self.query_generation_runs.get(run_id)
        if run is None:
            return None
        return await self.get_project(tenant_id, run.project_id)

    async def get_query_draft_project(
        self,
        tenant_id: UUID,
        draft_id: UUID,
    ) -> GeoProjectRecord | None:
        draft = self.query_drafts.get(draft_id)
        if draft is None:
            return None
        return await self.get_project(tenant_id, draft.project_id)

    async def create_project(self, command: GeoProjectCommand) -> GeoProjectRecord:
        now = _now()
        project = GeoProjectRecord(
            **command.model_dump(),
            id=uuid4(),
            created_at=now,
            updated_at=now,
        )
        self.projects[project.id] = project
        return project

    async def update_project(
        self,
        tenant_id: UUID,
        project_id: UUID,
        command: GeoProjectCommand,
    ) -> GeoProjectRecord | None:
        if await self.get_project(tenant_id, project_id) is None:
            return None
        project = GeoProjectRecord(
            **command.model_dump(exclude={"tenant_id"}),
            tenant_id=tenant_id,
            id=project_id,
            created_at=self.projects[project_id].created_at,
            updated_at=_now(),
        )
        self.projects[project_id] = project
        return project

    async def delete_project(self, tenant_id: UUID, project_id: UUID) -> bool:
        if await self.get_project(tenant_id, project_id) is None:
            return False
        return self.projects.pop(project_id, None) is not None

    async def list_markets(
        self,
        tenant_id: UUID,
        project_id: UUID,
    ) -> list[GeoMarketRecord]:
        if not self._project_matches(tenant_id, project_id):
            return []
        return [item for item in self.markets.values() if item.project_id == project_id]

    async def create_market(
        self,
        tenant_id: UUID,
        project_id: UUID,
        command: GeoMarketCommand,
    ) -> GeoMarketRecord | None:
        if not self._project_matches(tenant_id, project_id):
            return None
        now = _now()
        market = GeoMarketRecord(
            **command.model_dump(),
            id=uuid4(),
            project_id=project_id,
            created_at=now,
            updated_at=now,
        )
        self.markets[market.id] = market
        return market

    async def update_market(
        self,
        tenant_id: UUID,
        market_id: UUID,
        command: GeoMarketCommand,
    ) -> GeoMarketRecord | None:
        existing = self.markets.get(market_id)
        if existing is None or not self._project_matches(tenant_id, existing.project_id):
            return None
        return self._replace_record(
            market_id,
            command,
            self.markets,
            GeoMarketRecord,
        )

    async def delete_market(self, tenant_id: UUID, market_id: UUID) -> bool:
        existing = self.markets.get(market_id)
        if existing is None or not self._project_matches(tenant_id, existing.project_id):
            return False
        return self.markets.pop(market_id, None) is not None

    async def list_entities(
        self,
        tenant_id: UUID,
        project_id: UUID,
    ) -> list[GeoEntityRecord]:
        if not self._project_matches(tenant_id, project_id):
            return []
        return [item for item in self.entities.values() if item.project_id == project_id]

    async def get_entity(
        self,
        tenant_id: UUID,
        entity_id: UUID,
    ) -> GeoEntityRecord | None:
        entity = self.entities.get(entity_id)
        if entity is None or not self._project_matches(tenant_id, entity.project_id):
            return None
        return entity

    async def create_entity(
        self,
        tenant_id: UUID,
        project_id: UUID,
        command: GeoEntityCommand,
    ) -> GeoEntityRecord | None:
        if not self._project_matches(tenant_id, project_id):
            return None
        now = _now()
        entity = GeoEntityRecord(
            **command.model_dump(),
            id=uuid4(),
            project_id=project_id,
            created_at=now,
            updated_at=now,
        )
        self.entities[entity.id] = entity
        return entity

    async def update_entity(
        self,
        tenant_id: UUID,
        entity_id: UUID,
        command: GeoEntityCommand,
    ) -> GeoEntityRecord | None:
        if await self.get_entity(tenant_id, entity_id) is None:
            return None
        return self._replace_record(
            entity_id,
            command,
            self.entities,
            GeoEntityRecord,
        )

    async def delete_entity(self, tenant_id: UUID, entity_id: UUID) -> bool:
        if await self.get_entity(tenant_id, entity_id) is None:
            return False
        return self.entities.pop(entity_id, None) is not None

    async def list_aliases(
        self,
        tenant_id: UUID,
        entity_id: UUID,
    ) -> list[GeoEntityAliasRecord]:
        if await self.get_entity(tenant_id, entity_id) is None:
            return []
        return [item for item in self.aliases.values() if item.entity_id == entity_id]

    async def create_alias(
        self,
        tenant_id: UUID,
        entity_id: UUID,
        command: GeoEntityAliasCommand,
    ) -> GeoEntityAliasRecord | None:
        if await self.get_entity(tenant_id, entity_id) is None:
            return None
        alias = GeoEntityAliasRecord(
            **command.model_dump(),
            id=uuid4(),
            entity_id=entity_id,
            created_at=_now(),
        )
        self.aliases[alias.id] = alias
        return alias

    async def update_alias(
        self,
        tenant_id: UUID,
        alias_id: UUID,
        command: GeoEntityAliasCommand,
    ) -> GeoEntityAliasRecord | None:
        existing = self.aliases.get(alias_id)
        if existing is None or await self.get_entity(tenant_id, existing.entity_id) is None:
            return None
        alias = GeoEntityAliasRecord(
            **command.model_dump(),
            id=alias_id,
            entity_id=existing.entity_id,
            created_at=existing.created_at,
        )
        self.aliases[alias_id] = alias
        return alias

    async def delete_alias(self, tenant_id: UUID, alias_id: UUID) -> bool:
        existing = self.aliases.get(alias_id)
        if existing is None or await self.get_entity(tenant_id, existing.entity_id) is None:
            return False
        return self.aliases.pop(alias_id, None) is not None

    async def list_topics(
        self,
        tenant_id: UUID,
        project_id: UUID,
    ) -> list[GeoTopicRecord]:
        if not self._project_matches(tenant_id, project_id):
            return []
        return [item for item in self.topics.values() if item.project_id == project_id]

    async def create_topic(
        self,
        tenant_id: UUID,
        project_id: UUID,
        command: GeoTopicCommand,
    ) -> GeoTopicRecord | None:
        if not self._project_matches(tenant_id, project_id):
            return None
        now = _now()
        topic = GeoTopicRecord(
            **command.model_dump(),
            id=uuid4(),
            project_id=project_id,
            created_at=now,
            updated_at=now,
        )
        self.topics[topic.id] = topic
        return topic

    async def update_topic(
        self,
        tenant_id: UUID,
        topic_id: UUID,
        command: GeoTopicCommand,
    ) -> GeoTopicRecord | None:
        topic = self.topics.get(topic_id)
        if topic is None or not self._project_matches(tenant_id, topic.project_id):
            return None
        return self._replace_record(topic_id, command, self.topics, GeoTopicRecord)

    async def delete_topic(self, tenant_id: UUID, topic_id: UUID) -> bool:
        topic = self.topics.get(topic_id)
        if topic is None or not self._project_matches(tenant_id, topic.project_id):
            return False
        return self.topics.pop(topic_id, None) is not None

    async def list_queries(
        self,
        tenant_id: UUID,
        project_id: UUID,
    ) -> list[GeoQueryRecord]:
        if not self._project_matches(tenant_id, project_id):
            return []
        return [item for item in self.queries.values() if item.project_id == project_id]

    async def get_query(
        self,
        tenant_id: UUID,
        query_id: UUID,
    ) -> GeoQueryRecord | None:
        query = self.queries.get(query_id)
        if query is None or not self._project_matches(tenant_id, query.project_id):
            return None
        return query

    async def create_query(
        self,
        tenant_id: UUID,
        project_id: UUID,
        command: GeoQueryCommand,
    ) -> GeoQueryRecord | None:
        if not self._project_matches(tenant_id, project_id):
            return None
        now = _now()
        query = GeoQueryRecord(
            **command.model_dump(),
            id=uuid4(),
            project_id=project_id,
            created_at=now,
            updated_at=now,
        )
        self.queries[query.id] = query
        return query

    async def update_query(
        self,
        tenant_id: UUID,
        query_id: UUID,
        command: GeoQueryCommand,
    ) -> GeoQueryRecord | None:
        if await self.get_query(tenant_id, query_id) is None:
            return None
        return self._replace_record(query_id, command, self.queries, GeoQueryRecord)

    async def delete_query(self, tenant_id: UUID, query_id: UUID) -> bool:
        if await self.get_query(tenant_id, query_id) is None:
            return False
        return self.queries.pop(query_id, None) is not None

    async def list_query_platforms(
        self,
        tenant_id: UUID,
        query_id: UUID,
    ) -> list[GeoQueryPlatformRecord]:
        if await self.get_query(tenant_id, query_id) is None:
            return []
        return [
            item for item in self.query_platforms.values() if item.query_id == query_id
        ]

    async def replace_query_platforms(
        self,
        tenant_id: UUID,
        query_id: UUID,
        commands: list[GeoQueryPlatformCommand],
    ) -> list[GeoQueryPlatformRecord] | None:
        if await self.get_query(tenant_id, query_id) is None:
            return None
        for item_id, item in list(self.query_platforms.items()):
            if item.query_id == query_id:
                del self.query_platforms[item_id]
        now = _now()
        saved = [
            GeoQueryPlatformRecord(
                **command.model_dump(),
                id=uuid4(),
                query_id=query_id,
                created_at=now,
                updated_at=now,
            )
            for command in commands
        ]
        self.query_platforms.update({item.id: item for item in saved})
        return saved

    async def list_schedules(
        self,
        tenant_id: UUID,
        query_id: UUID,
    ) -> list[GeoQueryScheduleRecord]:
        if await self.get_query(tenant_id, query_id) is None:
            return []
        return [item for item in self.schedules.values() if item.query_id == query_id]

    async def create_schedule(
        self,
        tenant_id: UUID,
        query_id: UUID,
        command: GeoQueryScheduleCommand,
    ) -> GeoQueryScheduleRecord | None:
        if await self.get_query(tenant_id, query_id) is None:
            return None
        now = _now()
        schedule = GeoQueryScheduleRecord(
            **command.model_dump(),
            id=uuid4(),
            query_id=query_id,
            last_scheduled_at=None,
            created_at=now,
            updated_at=now,
        )
        self.schedules[schedule.id] = schedule
        return schedule

    async def update_schedule(
        self,
        tenant_id: UUID,
        schedule_id: UUID,
        command: GeoQueryScheduleCommand,
    ) -> GeoQueryScheduleRecord | None:
        schedule = self.schedules.get(schedule_id)
        if schedule is None or await self.get_query(tenant_id, schedule.query_id) is None:
            return None
        return self._replace_record(
            schedule_id,
            command,
            self.schedules,
            GeoQueryScheduleRecord,
        )

    async def delete_schedule(self, tenant_id: UUID, schedule_id: UUID) -> bool:
        schedule = self.schedules.get(schedule_id)
        if schedule is None or await self.get_query(tenant_id, schedule.query_id) is None:
            return False
        return self.schedules.pop(schedule_id, None) is not None

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
        self.jobs[job.id] = job
        return job

    async def list_jobs(
        self,
        tenant_id: UUID,
        project_id: UUID,
    ) -> list[GeoQueryRunJob]:
        if not self._project_matches(tenant_id, project_id):
            return []
        return [job for job in self.jobs.values() if job.project_id == project_id]

    async def get(self, job_id: UUID) -> GeoQueryRunJob:
        job = self.jobs.get(job_id)
        if job is None:
            raise KeyError(job_id)
        return job

    async def get_job(self, tenant_id: UUID, job_id: UUID) -> GeoQueryRunJob | None:
        job = self.jobs.get(job_id)
        if job is None or not self._project_matches(tenant_id, job.project_id):
            return None
        return job

    async def get_job_tenant_id(self, job_id: UUID) -> UUID | None:
        job = self.jobs.get(job_id)
        if job is None:
            return None
        project = self.projects.get(job.project_id)
        return project.tenant_id if project is not None else None

    async def get_job_dispatch_context(
        self,
        job_id: UUID,
    ) -> GeoQueryRunJobDispatchContext | None:
        job = self.jobs.get(job_id)
        if job is None:
            return None
        query = self.queries.get(job.query_id)
        if query is None:
            return None
        project = self.projects.get(job.project_id)
        if project is None:
            return None
        topic_name = ""
        if query.topic_id is not None:
            topic = self.topics.get(query.topic_id)
            topic_name = topic.name if topic is not None else ""
        query_platform = next(
            (
                item
                for item in self.query_platforms.values()
                if item.query_id == job.query_id and item.platform_id == job.platform_id
            ),
            None,
        )
        return GeoQueryRunJobDispatchContext(
            job_id=job.id,
            tenant_id=project.tenant_id,
            project_id=job.project_id,
            seo_task_id=project.seo_task_id,
            query_id=job.query_id,
            query_text=query.query_text,
            topic_name=topic_name,
            platform=self.platform_codes.get(job.platform_id, str(job.platform_id)),
            model=(
                query_platform.model
                if query_platform is not None and query_platform.model
                else self.platform_models.get(job.platform_id)
            ),
            region=query.region,
            language=query.language,
            market_type=query.market_type,
            is_branded=query.is_branded,
            scheduled_for=job.scheduled_for,
        )

    async def save(self, job: GeoQueryRunJob) -> None:
        self.jobs[job.id] = job

    async def record_dispatch(
        self,
        *,
        job_id: UUID,
        result: PublishResult,
        payload: QueryRunJobMessage,
        occurred_at: datetime,
    ) -> None:
        self.dispatches.append((job_id, result, payload, occurred_at))

    async def record_external_callback(
        self,
        *,
        callback: ExternalRunCallback,
        occurred_at: datetime,
    ) -> None:
        self.callbacks.append((callback, occurred_at))

    async def apply_external_callback(
        self,
        *,
        callback: ExternalRunCallback,
        occurred_at: datetime,
    ) -> GeoQueryRunJob:
        job = self.jobs.get(callback.job_id)
        if job is None:
            raise KeyError(callback.job_id)
        job.mark_external_status(
            external_run_id=callback.external_run_id,
            external_status=callback.status,
            error_code=callback.error_code,
            error_message=callback.error_message,
            now=occurred_at,
        )
        await self.record_external_callback(callback=callback, occurred_at=occurred_at)
        return job

    async def save_tracking_run_result(
        self,
        *,
        command: SaveTrackingRunResultCommand,
        occurred_at: datetime,
    ) -> GeoQueryRunJob:
        external_run_id = command.response.id if command.response is not None else "unknown"
        callback = ExternalRunCallback(
            job_id=command.message.job_id,
            external_run_id=external_run_id,
            status=command.status,
            error_code=command.error_code,
            error_message=command.error_message,
        )
        job = await self.apply_external_callback(
            callback=callback,
            occurred_at=occurred_at,
        )
        if command.response is not None:
            run_request_id = uuid4()
            for result in command.response.results:
                result_id = uuid4()
                references = [
                    GeoRunResultReferenceRecord(
                        id=uuid4(),
                        run_result_id=result_id,
                        url=url,
                        title=title,
                        domain=_url_domain(url),
                        position=position,
                    )
                    for position, (url, title) in enumerate(
                        _result_references(result),
                        start=1,
                    )
                ]
                self.run_results[result_id] = GeoRunResultRecord(
                    id=result_id,
                    run_request_id=run_request_id,
                    job_id=command.message.job_id,
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
                    references=references,
                    created_at=occurred_at,
                )
        return job

    async def list_job_run_results(
        self,
        tenant_id: UUID,
        job_id: UUID,
    ) -> list[GeoRunResultRecord]:
        job = self.jobs.get(job_id)
        if job is None or not self._project_matches(tenant_id, job.project_id):
            return []
        return sorted(
            [item for item in self.run_results.values() if item.job_id == job_id],
            key=lambda item: item.run_at,
            reverse=True,
        )

    async def list_project_run_results(
        self,
        tenant_id: UUID,
        project_id: UUID,
    ) -> list[GeoRunResultRecord]:
        if not self._project_matches(tenant_id, project_id):
            return []
        job_ids = {
            job.id for job in self.jobs.values() if job.project_id == project_id
        }
        return sorted(
            [item for item in self.run_results.values() if item.job_id in job_ids],
            key=lambda item: item.run_at,
            reverse=True,
        )

    async def get_run_result(
        self,
        tenant_id: UUID,
        result_id: UUID,
    ) -> GeoRunResultRecord | None:
        result = self.run_results.get(result_id)
        if result is None:
            return None
        job = self.jobs.get(result.job_id)
        if job is None or not self._project_matches(tenant_id, job.project_id):
            return None
        return result

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
        if not self._project_matches(tenant_id, project_id):
            return None
        record = QueryResearchRunRecord(
            id=uuid4(),
            project_id=project_id,
            provider=command.provider,
            status=status,
            request_payload=request_payload,
            result=(
                QueryResearchResultRecord(
                    research_context=result.get("researchContext", ""),
                    searched_keywords=result.get("searchedKeywords", []),
                    source_urls=result.get("sourceUrls", []),
                )
                if result is not None
                else None
            ),
            error_code="query_research_failed" if error_message else None,
            error_message=error_message,
            created_at=occurred_at,
            completed_at=occurred_at,
        )
        self.query_research_runs[record.id] = record
        return record

    async def list_query_research_runs(
        self,
        tenant_id: UUID,
        project_id: UUID,
    ) -> list[QueryResearchRunRecord]:
        if not self._project_matches(tenant_id, project_id):
            return []
        return [
            item
            for item in self.query_research_runs.values()
            if item.project_id == project_id
        ]

    async def get_query_research_run(
        self,
        tenant_id: UUID,
        run_id: UUID,
    ) -> QueryResearchRunRecord | None:
        run = self.query_research_runs.get(run_id)
        if run is None or not self._project_matches(tenant_id, run.project_id):
            return None
        return run

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
        if not self._project_matches(tenant_id, project_id):
            return None
        run_id = uuid4()
        drafts = [
            self._draft_record(project_id, run_id, query, occurred_at)
            for query in (result or {}).get("queries", [])
        ]
        record = QueryGenerationRunRecord(
            id=run_id,
            project_id=project_id,
            provider=command.provider,
            status=status,
            request_payload=request_payload,
            error_code="query_generation_failed" if error_message else None,
            error_message=error_message,
            created_at=occurred_at,
            completed_at=occurred_at,
            drafts=drafts,
        )
        self.query_generation_runs[record.id] = record
        self.query_drafts.update({draft.id: draft for draft in drafts})
        return record

    async def list_query_generation_runs(
        self,
        tenant_id: UUID,
        project_id: UUID,
    ) -> list[QueryGenerationRunRecord]:
        if not self._project_matches(tenant_id, project_id):
            return []
        return [
            item
            for item in self.query_generation_runs.values()
            if item.project_id == project_id
        ]

    async def get_query_generation_run(
        self,
        tenant_id: UUID,
        run_id: UUID,
    ) -> QueryGenerationRunRecord | None:
        record = self.query_generation_runs.get(run_id)
        if record is None or not self._project_matches(tenant_id, record.project_id):
            return None
        drafts = [
            item for item in self.query_drafts.values() if item.generation_run_id == run_id
        ]
        return record.model_copy(update={"drafts": drafts})

    async def update_query_draft_selection(
        self,
        tenant_id: UUID,
        draft_id: UUID,
        command: QueryDraftSelectionCommand,
    ) -> QueryDraftRecord | None:
        draft = self.query_drafts.get(draft_id)
        if draft is None or not self._project_matches(tenant_id, draft.project_id):
            return None
        if draft.accepted_query_id is not None:
            raise ValueError("query draft already accepted")
        updated = draft.model_copy(
            update={
                "selection_status": command.selection_status,
                "updated_at": _now(),
            }
        )
        self.query_drafts[draft_id] = updated
        return updated

    async def accept_query_draft(
        self,
        tenant_id: UUID,
        draft_id: UUID,
        command: AcceptQueryDraftCommand,
    ) -> GeoQueryRecord | None:
        draft = self.query_drafts.get(draft_id)
        if draft is None or not self._project_matches(tenant_id, draft.project_id):
            return None
        if draft.accepted_query_id is not None:
            raise ValueError("query draft already accepted")
        topic_id = draft.topic_id
        if topic_id is None and draft.topic_name:
            topic = next(
                (
                    item
                    for item in self.topics.values()
                    if item.project_id == draft.project_id and item.name == draft.topic_name
                ),
                None,
            )
            if topic is None and command.create_topic_if_missing:
                topic = await self.create_topic(
                    tenant_id,
                    draft.project_id,
                    GeoTopicCommand(name=draft.topic_name),
                )
            topic_id = topic.id if topic is not None else None
        query = await self.create_query(
            tenant_id,
            draft.project_id,
            GeoQueryCommand(
                topic_id=topic_id,
                query_text=draft.query_text,
                region=draft.region,
                language=draft.language,
                market_type=draft.market_type,
                intent=draft.intent,
                is_branded=draft.is_branded,
                status=command.status,
                metadata=draft.metadata,
            ),
        )
        if query is None:
            return None
        self.query_drafts[draft_id] = draft.model_copy(
            update={
                "selection_status": "accepted",
                "accepted_query_id": query.id,
                "updated_at": _now(),
            }
        )
        return query

    def job_dict(self, job: GeoQueryRunJob) -> dict:
        data = asdict(job)
        data["status"] = job.status.value
        return data

    def _replace_record(self, item_id, command, collection, record_type):
        existing = collection.get(item_id)
        if existing is None:
            return None
        item = record_type(
            **command.model_dump(),
            id=item_id,
            **_scope_fields(existing),
            created_at=existing.created_at,
            updated_at=_now(),
        )
        collection[item_id] = item
        return item

    def _draft_record(
        self,
        project_id: UUID,
        run_id: UUID,
        query: dict,
        occurred_at: datetime,
    ) -> QueryDraftRecord:
        attributes = query.get("attributes") or {}
        intent = attributes.get("intent") or {}
        return QueryDraftRecord(
            id=uuid4(),
            generation_run_id=run_id,
            project_id=project_id,
            topic_id=query.get("topicId"),
            topic_name=query.get("topicName") or attributes.get("topicName") or "",
            query_text=query.get("queryText") or query.get("text") or query.get("query") or "",
            keywords=query.get("keywords", []),
            region=query.get("region", "TW"),
            language=query.get("language", "zh-TW"),
            market_type=query.get("marketType", "b2b_procurement"),
            intent=intent.get("category"),
            is_branded=query.get("isBranded", False),
            metadata=query.get("metadata", {}),
            created_at=occurred_at,
            updated_at=occurred_at,
        )

    def _project_matches(self, tenant_id: UUID, project_id: UUID) -> bool:
        project = self.projects.get(project_id)
        return project is not None and project.tenant_id == tenant_id


def _scope_fields(record) -> dict:
    if hasattr(record, "project_id"):
        return {"project_id": record.project_id}
    if hasattr(record, "query_id"):
        fields = {"query_id": record.query_id}
        if hasattr(record, "last_scheduled_at"):
            fields["last_scheduled_at"] = record.last_scheduled_at
        return fields
    return {}


def _now() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


def _normalize_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).replace(microsecond=0)


def _result_references(result) -> list[tuple[str, str | None]]:
    if result.references:
        return [(reference.url, reference.title) for reference in result.references]
    return [(url, None) for url in result.reference_urls]


def _url_domain(url: str) -> str | None:
    parsed = urlparse(url)
    return parsed.netloc.lower() or None
