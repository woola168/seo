from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

from younilab_geo_analysis_api.presentation.http.dtos import (
    AliasRequest,
    CreateJobRequest,
    EntityRequest,
    MarketRequest,
    ProjectRequest,
    QueryPlatformRequest,
    QueryRequest,
    ScheduleRequest,
    TopicRequest,
)
from younilab_geo_analysis_domain import GeoQueryRunJob, JobStatus


@dataclass
class GeoApiStore:
    """PostgreSQL repository 串接前暫用的記憶體 orchestration store。"""

    projects: dict[UUID, dict] = field(default_factory=dict)
    markets: dict[UUID, dict] = field(default_factory=dict)
    entities: dict[UUID, dict] = field(default_factory=dict)
    aliases: dict[UUID, dict] = field(default_factory=dict)
    topics: dict[UUID, dict] = field(default_factory=dict)
    queries: dict[UUID, dict] = field(default_factory=dict)
    query_platforms: dict[UUID, dict] = field(default_factory=dict)
    schedules: dict[UUID, dict] = field(default_factory=dict)
    jobs: dict[UUID, GeoQueryRunJob] = field(default_factory=dict)

    def create_project(self, request: ProjectRequest) -> dict:
        now = _now()
        project = {
            **request.model_dump(),
            "id": uuid4(),
            "created_at": now,
            "updated_at": now,
        }
        self.projects[project["id"]] = project
        return project

    def update_project(self, project_id: UUID, request: ProjectRequest) -> dict | None:
        if project_id not in self.projects:
            return None
        project = {
            **self.projects[project_id],
            **request.model_dump(),
            "updated_at": _now(),
        }
        self.projects[project_id] = project
        return project

    def create_market(self, project_id: UUID, request: MarketRequest) -> dict | None:
        return self._create_scoped(project_id, request, self.markets, "project_id")

    def update_market(self, market_id: UUID, request: MarketRequest) -> dict | None:
        return self._update(market_id, request, self.markets)

    def create_entity(self, project_id: UUID, request: EntityRequest) -> dict | None:
        return self._create_scoped(project_id, request, self.entities, "project_id")

    def update_entity(self, entity_id: UUID, request: EntityRequest) -> dict | None:
        return self._update(entity_id, request, self.entities)

    def create_alias(self, entity_id: UUID, request: AliasRequest) -> dict | None:
        if entity_id not in self.entities:
            return None
        now = _now()
        alias = {
            **request.model_dump(),
            "id": uuid4(),
            "entity_id": entity_id,
            "created_at": now,
        }
        self.aliases[alias["id"]] = alias
        return alias

    def update_alias(self, alias_id: UUID, request: AliasRequest) -> dict | None:
        if alias_id not in self.aliases:
            return None
        alias = {**self.aliases[alias_id], **request.model_dump()}
        self.aliases[alias_id] = alias
        return alias

    def create_topic(self, project_id: UUID, request: TopicRequest) -> dict | None:
        if project_id not in self.projects:
            return None
        now = _now()
        topic = {
            **request.model_dump(),
            "id": uuid4(),
            "project_id": project_id,
            "created_at": now,
            "updated_at": now,
        }
        self.topics[topic["id"]] = topic
        return topic

    def update_topic(self, topic_id: UUID, request: TopicRequest) -> dict | None:
        if topic_id not in self.topics:
            return None
        topic = {
            **self.topics[topic_id],
            **request.model_dump(),
            "updated_at": _now(),
        }
        self.topics[topic_id] = topic
        return topic

    def create_query(self, project_id: UUID, request: QueryRequest) -> dict | None:
        if project_id not in self.projects:
            return None
        now = _now()
        query = {
            **request.model_dump(),
            "id": uuid4(),
            "project_id": project_id,
            "created_at": now,
            "updated_at": now,
        }
        self.queries[query["id"]] = query
        return query

    def update_query(self, query_id: UUID, request: QueryRequest) -> dict | None:
        if query_id not in self.queries:
            return None
        query = {
            **self.queries[query_id],
            **request.model_dump(),
            "updated_at": _now(),
        }
        self.queries[query_id] = query
        return query

    def replace_query_platforms(
        self,
        query_id: UUID,
        requests: list[QueryPlatformRequest],
    ) -> list[dict] | None:
        if query_id not in self.queries:
            return None
        for platform_id, item in list(self.query_platforms.items()):
            if item["query_id"] == query_id:
                del self.query_platforms[platform_id]
        now = _now()
        saved = []
        for request in requests:
            item = {
                **request.model_dump(),
                "id": uuid4(),
                "query_id": query_id,
                "created_at": now,
                "updated_at": now,
            }
            self.query_platforms[item["id"]] = item
            saved.append(item)
        return saved

    def create_schedule(self, query_id: UUID, request: ScheduleRequest) -> dict | None:
        if query_id not in self.queries:
            return None
        now = _now()
        schedule = {
            **request.model_dump(),
            "id": uuid4(),
            "query_id": query_id,
            "last_scheduled_at": None,
            "created_at": now,
            "updated_at": now,
        }
        self.schedules[schedule["id"]] = schedule
        return schedule

    def update_schedule(self, schedule_id: UUID, request: ScheduleRequest) -> dict | None:
        return self._update(schedule_id, request, self.schedules)

    def create_job(self, query_id: UUID, request: CreateJobRequest) -> GeoQueryRunJob | None:
        query = self.queries.get(query_id)
        if query is None:
            return None
        now = _now()
        scheduled_for = _normalize_datetime(request.scheduled_for or now)
        job = GeoQueryRunJob(
            id=uuid4(),
            project_id=query["project_id"],
            query_id=query_id,
            platform_id=request.platform_id,
            schedule_id=None,
            job_type=request.job_type,
            priority=request.priority,
            scheduled_for=scheduled_for,
            status=JobStatus.PENDING,
            attempt_count=0,
            max_attempts=3,
            dedupe_key=(
                f"{query['project_id']}:{query_id}:{request.platform_id}:"
                f"{scheduled_for.isoformat()}"
            ),
            created_at=now,
            updated_at=now,
        )
        self.jobs[job.id] = job
        return job

    def job_dict(self, job: GeoQueryRunJob) -> dict:
        data = asdict(job)
        data["status"] = job.status.value
        return data

    def _create_scoped(
        self,
        project_id: UUID,
        request,
        collection: dict[UUID, dict],
        scope_key: str,
    ) -> dict | None:
        if project_id not in self.projects:
            return None
        now = _now()
        item = {
            **request.model_dump(),
            "id": uuid4(),
            scope_key: project_id,
            "created_at": now,
            "updated_at": now,
        }
        collection[item["id"]] = item
        return item

    def _update(self, item_id: UUID, request, collection: dict[UUID, dict]) -> dict | None:
        if item_id not in collection:
            return None
        item = {
            **collection[item_id],
            **request.model_dump(),
            "updated_at": _now(),
        }
        collection[item_id] = item
        return item


def _now() -> datetime:
    return datetime.now(UTC)


def _normalize_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).replace(microsecond=0)
