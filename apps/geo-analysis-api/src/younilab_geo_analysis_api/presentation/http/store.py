from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

from younilab_seo.geo_analysis.application import (
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
    GeoQueryScheduleCommand,
    GeoQueryScheduleRecord,
    GeoTopicCommand,
    GeoTopicRecord,
    PublishResult,
    QueryRunJobMessage,
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
    dispatches: list[tuple[UUID, PublishResult, QueryRunJobMessage, datetime]] = field(
        default_factory=list
    )
    callbacks: list[tuple[ExternalRunCallback, datetime]] = field(default_factory=list)

    async def list_projects(
        self,
        customer_id: UUID | None = None,
    ) -> list[GeoProjectRecord]:
        items = list(self.projects.values())
        if customer_id is not None:
            items = [item for item in items if item.customer_id == customer_id]
        return items

    async def get_project(self, project_id: UUID) -> GeoProjectRecord | None:
        return self.projects.get(project_id)

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
        project_id: UUID,
        command: GeoProjectCommand,
    ) -> GeoProjectRecord | None:
        if project_id not in self.projects:
            return None
        project = GeoProjectRecord(
            **command.model_dump(),
            id=project_id,
            created_at=self.projects[project_id].created_at,
            updated_at=_now(),
        )
        self.projects[project_id] = project
        return project

    async def delete_project(self, project_id: UUID) -> bool:
        return self.projects.pop(project_id, None) is not None

    async def list_markets(self, project_id: UUID) -> list[GeoMarketRecord]:
        return [item for item in self.markets.values() if item.project_id == project_id]

    async def create_market(
        self,
        project_id: UUID,
        command: GeoMarketCommand,
    ) -> GeoMarketRecord | None:
        if project_id not in self.projects:
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
        market_id: UUID,
        command: GeoMarketCommand,
    ) -> GeoMarketRecord | None:
        return self._replace_record(
            market_id,
            command,
            self.markets,
            GeoMarketRecord,
        )

    async def delete_market(self, market_id: UUID) -> bool:
        return self.markets.pop(market_id, None) is not None

    async def list_entities(self, project_id: UUID) -> list[GeoEntityRecord]:
        return [item for item in self.entities.values() if item.project_id == project_id]

    async def get_entity(self, entity_id: UUID) -> GeoEntityRecord | None:
        return self.entities.get(entity_id)

    async def create_entity(
        self,
        project_id: UUID,
        command: GeoEntityCommand,
    ) -> GeoEntityRecord | None:
        if project_id not in self.projects:
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
        entity_id: UUID,
        command: GeoEntityCommand,
    ) -> GeoEntityRecord | None:
        return self._replace_record(
            entity_id,
            command,
            self.entities,
            GeoEntityRecord,
        )

    async def delete_entity(self, entity_id: UUID) -> bool:
        return self.entities.pop(entity_id, None) is not None

    async def list_aliases(self, entity_id: UUID) -> list[GeoEntityAliasRecord]:
        return [item for item in self.aliases.values() if item.entity_id == entity_id]

    async def create_alias(
        self,
        entity_id: UUID,
        command: GeoEntityAliasCommand,
    ) -> GeoEntityAliasRecord | None:
        if entity_id not in self.entities:
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
        alias_id: UUID,
        command: GeoEntityAliasCommand,
    ) -> GeoEntityAliasRecord | None:
        existing = self.aliases.get(alias_id)
        if existing is None:
            return None
        alias = GeoEntityAliasRecord(
            **command.model_dump(),
            id=alias_id,
            entity_id=existing.entity_id,
            created_at=existing.created_at,
        )
        self.aliases[alias_id] = alias
        return alias

    async def delete_alias(self, alias_id: UUID) -> bool:
        return self.aliases.pop(alias_id, None) is not None

    async def list_topics(self, project_id: UUID) -> list[GeoTopicRecord]:
        return [item for item in self.topics.values() if item.project_id == project_id]

    async def create_topic(
        self,
        project_id: UUID,
        command: GeoTopicCommand,
    ) -> GeoTopicRecord | None:
        if project_id not in self.projects:
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
        topic_id: UUID,
        command: GeoTopicCommand,
    ) -> GeoTopicRecord | None:
        return self._replace_record(topic_id, command, self.topics, GeoTopicRecord)

    async def delete_topic(self, topic_id: UUID) -> bool:
        return self.topics.pop(topic_id, None) is not None

    async def list_queries(self, project_id: UUID) -> list[GeoQueryRecord]:
        return [item for item in self.queries.values() if item.project_id == project_id]

    async def get_query(self, query_id: UUID) -> GeoQueryRecord | None:
        return self.queries.get(query_id)

    async def create_query(
        self,
        project_id: UUID,
        command: GeoQueryCommand,
    ) -> GeoQueryRecord | None:
        if project_id not in self.projects:
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
        query_id: UUID,
        command: GeoQueryCommand,
    ) -> GeoQueryRecord | None:
        return self._replace_record(query_id, command, self.queries, GeoQueryRecord)

    async def delete_query(self, query_id: UUID) -> bool:
        return self.queries.pop(query_id, None) is not None

    async def list_query_platforms(
        self,
        query_id: UUID,
    ) -> list[GeoQueryPlatformRecord]:
        return [
            item for item in self.query_platforms.values() if item.query_id == query_id
        ]

    async def replace_query_platforms(
        self,
        query_id: UUID,
        commands: list[GeoQueryPlatformCommand],
    ) -> list[GeoQueryPlatformRecord] | None:
        if query_id not in self.queries:
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

    async def list_schedules(self, query_id: UUID) -> list[GeoQueryScheduleRecord]:
        return [item for item in self.schedules.values() if item.query_id == query_id]

    async def create_schedule(
        self,
        query_id: UUID,
        command: GeoQueryScheduleCommand,
    ) -> GeoQueryScheduleRecord | None:
        if query_id not in self.queries:
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
        schedule_id: UUID,
        command: GeoQueryScheduleCommand,
    ) -> GeoQueryScheduleRecord | None:
        return self._replace_record(
            schedule_id,
            command,
            self.schedules,
            GeoQueryScheduleRecord,
        )

    async def delete_schedule(self, schedule_id: UUID) -> bool:
        return self.schedules.pop(schedule_id, None) is not None

    async def create_job(
        self,
        query_id: UUID,
        command: CreateQueryRunJobCommand,
    ) -> GeoQueryRunJob | None:
        query = self.queries.get(query_id)
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

    async def list_jobs(self, project_id: UUID) -> list[GeoQueryRunJob]:
        return [job for job in self.jobs.values() if job.project_id == project_id]

    async def get(self, job_id: UUID) -> GeoQueryRunJob:
        job = await self.get_job(job_id)
        if job is None:
            raise KeyError(job_id)
        return job

    async def get_job(self, job_id: UUID) -> GeoQueryRunJob | None:
        return self.jobs.get(job_id)

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
