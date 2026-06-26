from datetime import date, datetime
from uuid import UUID

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel, UniqueConstraint


class GeoProjectRow(SQLModel, table=True):
    """Project-level GEO setup row for a customer."""

    __tablename__ = "geo_project"

    id: UUID = Field(primary_key=True)
    customer_id: UUID = Field(nullable=False)
    seo_task_id: UUID | None = Field(default=None)
    name: str = Field(sa_column=Column(String(200), nullable=False))
    default_region: str = Field(default="TW", sa_column=Column(String(16), nullable=False))
    default_language: str = Field(
        default="zh-TW",
        sa_column=Column(String(16), nullable=False),
    )
    status: str = Field(sa_column=Column(String(32), nullable=False))
    daily_run_budget: int = Field(default=0, nullable=False)
    daily_cost_budget: float | None = Field(
        default=None,
        sa_column=Column(Numeric(12, 6)),
    )
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    updated_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    archived_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True)),
    )


class GeoMarketRow(SQLModel, table=True):
    """Market locale settings used when building runner messages."""

    __tablename__ = "geo_market"
    __table_args__ = (
        UniqueConstraint("project_id", "region", "language", name="ux_geo_market_scope"),
    )

    id: UUID = Field(primary_key=True)
    project_id: UUID = Field(foreign_key="geo_project.id", nullable=False)
    region: str = Field(sa_column=Column(String(16), nullable=False))
    language: str = Field(sa_column=Column(String(16), nullable=False))
    market_name: str = Field(sa_column=Column(String(100), nullable=False))
    prompt_locale_hint: str = Field(default="", sa_column=Column(Text, nullable=False))
    serp_gl: str | None = Field(default=None, sa_column=Column(String(16)))
    serp_hl: str | None = Field(default=None, sa_column=Column(String(16)))
    serp_location: str | None = Field(default=None, sa_column=Column(String(200)))
    status: str = Field(sa_column=Column(String(32), nullable=False))
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    updated_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))


class GeoEntityRow(SQLModel, table=True):
    """Tracked brand, competitor, or entity metadata within a GEO project."""

    __tablename__ = "geo_entity"
    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "entity_type",
            "name",
            name="ux_geo_entity_scope_type_name",
        ),
    )

    id: UUID = Field(primary_key=True)
    project_id: UUID = Field(foreign_key="geo_project.id", nullable=False)
    entity_type: str = Field(sa_column=Column(String(32), nullable=False))
    name: str = Field(sa_column=Column(String(200), nullable=False))
    website_url: str | None = Field(default=None, sa_column=Column(Text))
    description: str = Field(default="", sa_column=Column(Text, nullable=False))
    status: str = Field(sa_column=Column(String(32), nullable=False))
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    updated_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))


class GeoEntityAliasRow(SQLModel, table=True):
    """Alias used by runner and analysis workflows to match a tracked entity."""

    __tablename__ = "geo_entity_alias"
    __table_args__ = (
        UniqueConstraint("entity_id", "alias", name="ux_geo_entity_alias"),
    )

    id: UUID = Field(primary_key=True)
    entity_id: UUID = Field(foreign_key="geo_entity.id", nullable=False)
    alias: str = Field(sa_column=Column(String(200), nullable=False))
    match_type: str = Field(default="exact", sa_column=Column(String(32), nullable=False))
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))


class GeoTopicRow(SQLModel, table=True):
    """Topic grouping for tracked queries in a project."""

    __tablename__ = "geo_topic"
    __table_args__ = (
        UniqueConstraint("project_id", "name", name="ux_geo_topic_scope_name"),
    )

    id: UUID = Field(primary_key=True)
    project_id: UUID = Field(foreign_key="geo_project.id", nullable=False)
    name: str = Field(sa_column=Column(String(200), nullable=False))
    description: str = Field(default="", sa_column=Column(Text, nullable=False))
    status: str = Field(sa_column=Column(String(32), nullable=False))
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    updated_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))


class GeoQueryRow(SQLModel, table=True):
    """Tracked natural-language question dispatched to GEO runners."""

    __tablename__ = "geo_query"

    id: UUID = Field(primary_key=True)
    project_id: UUID = Field(foreign_key="geo_project.id", nullable=False)
    topic_id: UUID | None = Field(default=None, foreign_key="geo_topic.id")
    query_text: str = Field(sa_column=Column(Text, nullable=False))
    region: str = Field(sa_column=Column(String(16), nullable=False))
    language: str = Field(sa_column=Column(String(16), nullable=False))
    market_type: str = Field(
        default="b2b_procurement",
        sa_column=Column(String(32), nullable=False),
    )
    intent: str | None = Field(default=None, sa_column=Column(String(32)))
    buyer_stage: str | None = Field(default=None, sa_column=Column(String(32)))
    is_branded: bool = Field(default=False, sa_column=Column(Boolean, nullable=False))
    priority: str = Field(default="normal", sa_column=Column(String(32), nullable=False))
    status: str = Field(sa_column=Column(String(32), nullable=False))
    metadata_json: dict = Field(
        default_factory=dict,
        sa_column=Column("metadata", JSONB, nullable=False),
    )
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    updated_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    archived_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True)),
    )


class GeoQueryKeywordRow(SQLModel, table=True):
    """Keyword research term attached to a tracked query."""

    __tablename__ = "geo_query_keyword"

    id: UUID = Field(primary_key=True)
    query_id: UUID = Field(foreign_key="geo_query.id", nullable=False)
    keyword: str = Field(sa_column=Column(String(200), nullable=False))
    search_volume: int | None = None
    region: str = Field(sa_column=Column(String(16), nullable=False))
    language: str = Field(sa_column=Column(String(16), nullable=False))
    source: str = Field(default="manual", sa_column=Column(String(64), nullable=False))
    metadata_json: dict = Field(
        default_factory=dict,
        sa_column=Column("metadata", JSONB, nullable=False),
    )
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))


class GeoAiPlatformRow(SQLModel, table=True):
    """Selectable AI or SERP platform metadata without provider credentials."""

    __tablename__ = "geo_ai_platform"

    id: UUID = Field(primary_key=True)
    code: str = Field(sa_column=Column(String(64), nullable=False, unique=True))
    display_name: str = Field(sa_column=Column(String(100), nullable=False))
    provider_type: str = Field(sa_column=Column(String(32), nullable=False))
    default_model: str | None = Field(default=None, sa_column=Column(String(100)))
    supports_citations: bool = Field(
        default=False,
        sa_column=Column(Boolean, nullable=False),
    )
    supports_grounding: bool = Field(
        default=False,
        sa_column=Column(Boolean, nullable=False),
    )
    status: str = Field(sa_column=Column(String(32), nullable=False))
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    updated_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))


class GeoQueryPlatformRow(SQLModel, table=True):
    """Platform selection for a tracked query."""

    __tablename__ = "geo_query_platform"
    __table_args__ = (
        UniqueConstraint("query_id", "platform_id", name="ux_geo_query_platform"),
    )

    id: UUID = Field(primary_key=True)
    query_id: UUID = Field(foreign_key="geo_query.id", nullable=False)
    platform_id: UUID = Field(foreign_key="geo_ai_platform.id", nullable=False)
    model: str | None = Field(default=None, sa_column=Column(String(100)))
    status: str = Field(sa_column=Column(String(32), nullable=False))
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    updated_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))


class GeoQueryScheduleRow(SQLModel, table=True):
    """Schedule for creating query/platform dispatch jobs."""

    __tablename__ = "geo_query_schedule"
    __table_args__ = (
        UniqueConstraint("query_id", "platform_id", name="ux_geo_query_schedule"),
    )

    id: UUID = Field(primary_key=True)
    query_id: UUID = Field(foreign_key="geo_query.id", nullable=False)
    platform_id: UUID = Field(foreign_key="geo_ai_platform.id", nullable=False)
    frequency: str = Field(sa_column=Column(String(32), nullable=False))
    priority: str = Field(default="normal", sa_column=Column(String(32), nullable=False))
    timezone: str = Field(default="Asia/Taipei", sa_column=Column(String(64), nullable=False))
    next_run_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True)),
    )
    last_scheduled_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True)),
    )
    status: str = Field(sa_column=Column(String(32), nullable=False))
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    updated_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))


class GeoQueryRunJobRow(SQLModel, table=True):
    """Persistent query run job dispatched through the configured broker."""

    __tablename__ = "geo_query_run_job"

    id: UUID = Field(primary_key=True)
    project_id: UUID = Field(foreign_key="geo_project.id", nullable=False)
    query_id: UUID = Field(foreign_key="geo_query.id", nullable=False)
    platform_id: UUID = Field(foreign_key="geo_ai_platform.id", nullable=False)
    schedule_id: UUID | None = Field(default=None, foreign_key="geo_query_schedule.id")
    job_type: str = Field(default="scheduled_run", sa_column=Column(String(32), nullable=False))
    priority: str = Field(default="normal", sa_column=Column(String(32), nullable=False))
    scheduled_for: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    status: str = Field(sa_column=Column(String(32), nullable=False))
    attempt_count: int = Field(default=0, nullable=False)
    max_attempts: int = Field(default=3, nullable=False)
    next_retry_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True)),
    )
    dedupe_key: str = Field(sa_column=Column(String(200), nullable=False, unique=True))
    dispatch_backend: str | None = Field(default=None, sa_column=Column(String(32)))
    dispatch_message_id: str | None = Field(default=None, sa_column=Column(String(200)))
    external_run_id: str | None = Field(default=None, sa_column=Column(String(200)))
    last_error_code: str | None = Field(default=None, sa_column=Column(String(100)))
    last_error_message: str | None = Field(default=None, sa_column=Column(Text))
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    updated_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))


class GeoMessageDispatchLogRow(SQLModel, table=True):
    """Message dispatch log independent from a specific broker implementation."""

    __tablename__ = "geo_message_dispatch_log"

    id: UUID = Field(primary_key=True)
    job_id: UUID = Field(foreign_key="geo_query_run_job.id", nullable=False)
    message_backend: str = Field(sa_column=Column(String(32), nullable=False))
    destination: str = Field(sa_column=Column(String(200), nullable=False))
    message_id: str | None = Field(default=None, sa_column=Column(String(200)))
    payload: dict = Field(sa_column=Column(JSONB, nullable=False))
    publish_status: str = Field(sa_column=Column(String(32), nullable=False))
    published_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True)),
    )
    error_message: str | None = Field(default=None, sa_column=Column(Text))
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))


class GeoWorkerLeaseRow(SQLModel, table=True):
    """Lease record for worker or compensation processes."""

    __tablename__ = "geo_worker_lease"

    id: UUID = Field(primary_key=True)
    job_id: UUID = Field(foreign_key="geo_query_run_job.id", nullable=False)
    worker_id: str = Field(sa_column=Column(String(100), nullable=False))
    leased_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    expires_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    released_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True)),
    )
    release_reason: str | None = Field(default=None, sa_column=Column(String(64)))


class GeoJobDispatchEventRow(SQLModel, table=True):
    """Audit event for job scheduling, dispatch, retry, and callback transitions."""

    __tablename__ = "geo_job_dispatch_event"

    id: UUID = Field(primary_key=True)
    job_id: UUID = Field(foreign_key="geo_query_run_job.id", nullable=False)
    event_type: str = Field(sa_column=Column(String(64), nullable=False))
    occurred_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    actor: str = Field(sa_column=Column(String(100), nullable=False))
    metadata_json: dict = Field(
        default_factory=dict,
        sa_column=Column("metadata", JSONB, nullable=False),
    )


class GeoExternalRunReferenceRow(SQLModel, table=True):
    """Reference to an external runner execution without storing AI response content."""

    __tablename__ = "geo_external_run_reference"

    id: UUID = Field(primary_key=True)
    job_id: UUID = Field(foreign_key="geo_query_run_job.id", nullable=False)
    external_system: str = Field(sa_column=Column(String(100), nullable=False))
    external_run_id: str = Field(sa_column=Column(String(200), nullable=False))
    external_status: str = Field(sa_column=Column(String(64), nullable=False))
    callback_received_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True)),
    )
    result_location: str | None = Field(default=None, sa_column=Column(Text))
    metadata_json: dict = Field(
        default_factory=dict,
        sa_column=Column("metadata", JSONB, nullable=False),
    )
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    updated_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))


class GeoRunRequestRow(SQLModel, table=True):
    """Worker call to geo-tracking for one analysis job."""

    __tablename__ = "geo_run_request"

    id: UUID = Field(primary_key=True)
    job_id: UUID = Field(foreign_key="geo_query_run_job.id", nullable=False)
    tracking_run_request_id: str = Field(sa_column=Column(String(200), nullable=False))
    seo_task_id: UUID = Field(nullable=False)
    provider: str = Field(sa_column=Column(String(64), nullable=False))
    timing: str = Field(sa_column=Column(String(32), nullable=False))
    status: str = Field(sa_column=Column(String(32), nullable=False))
    error_code: str | None = Field(default=None, sa_column=Column(String(100)))
    error_message: str | None = Field(default=None, sa_column=Column(Text))
    request_payload: dict = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False),
    )
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    completed_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True)),
    )


class GeoRunResultRow(SQLModel, table=True):
    """Raw provider result returned by geo-tracking for one query."""

    __tablename__ = "geo_run_result"

    id: UUID = Field(primary_key=True)
    run_request_id: UUID = Field(foreign_key="geo_run_request.id", nullable=False)
    job_id: UUID = Field(foreign_key="geo_query_run_job.id", nullable=False)
    tracking_result_id: str = Field(sa_column=Column(String(200), nullable=False))
    query_id: UUID = Field(foreign_key="geo_query.id", nullable=False)
    provider: str = Field(sa_column=Column(String(64), nullable=False))
    surface: str = Field(sa_column=Column(String(100), nullable=False))
    model: str = Field(sa_column=Column(String(100), nullable=False))
    region: str = Field(sa_column=Column(String(16), nullable=False))
    language: str = Field(sa_column=Column(String(16), nullable=False))
    status: str = Field(sa_column=Column(String(32), nullable=False))
    raw_response: str = Field(default="", sa_column=Column(Text, nullable=False))
    error: str | None = Field(default=None, sa_column=Column(Text))
    run_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))


class GeoRunResultReferenceRow(SQLModel, table=True):
    """Reference URL returned with a raw provider result."""

    __tablename__ = "geo_run_result_reference"

    id: UUID = Field(primary_key=True)
    run_result_id: UUID = Field(foreign_key="geo_run_result.id", nullable=False)
    url: str = Field(sa_column=Column(Text, nullable=False))
    title: str | None = Field(default=None, sa_column=Column(Text))
    domain: str | None = Field(default=None, sa_column=Column(String(255)))
    position: int = Field(sa_column=Column(Integer, nullable=False))
