from datetime import date, datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Computed,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel, UniqueConstraint


class GeoProjectRow(SQLModel, table=True):
    """Project-level GEO setup row for a customer."""

    __tablename__ = "geo_project"

    id: UUID = Field(primary_key=True)
    tenant_id: UUID = Field(nullable=False, index=True)
    customer_id: UUID | None = Field(default=None)
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


class GeoProjectQuerySettingsRow(SQLModel, table=True):
    """每個 GEO Project 一份的 Query Research 與 Generation 預設值。"""

    __tablename__ = "geo_project_query_settings"
    __table_args__ = (
        CheckConstraint(
            "research_provider IN ('gemini')",
            name="ck_geo_project_query_settings_research_provider",
        ),
        CheckConstraint(
            "run_provider IN ('gemini')",
            name="ck_geo_project_query_settings_run_provider",
        ),
        CheckConstraint(
            "market_type IN ('b2c', 'b2b_procurement')",
            name="ck_geo_project_query_settings_market_type",
        ),
        CheckConstraint(
            "max_queries BETWEEN 1 AND 40",
            name="ck_geo_project_query_settings_max_queries",
        ),
        CheckConstraint(
            "jsonb_typeof(keywords) = 'array' AND jsonb_array_length(keywords) <= 10",
            name="ck_geo_project_query_settings_keywords",
        ),
        CheckConstraint(
            "btrim(audience_name) <> ''",
            name="ck_geo_project_query_settings_audience_name",
        ),
        CheckConstraint(
            "btrim(audience_description) <> '' AND length(audience_description) <= 2000",
            name="ck_geo_project_query_settings_audience_description",
        ),
        CheckConstraint(
            "btrim(intent_category) <> ''",
            name="ck_geo_project_query_settings_intent_category",
        ),
        CheckConstraint(
            "btrim(intent_description) <> '' AND length(intent_description) <= 2000",
            name="ck_geo_project_query_settings_intent_description",
        ),
    )

    project_id: UUID = Field(
        sa_column=Column(
            ForeignKey("geo_project.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )
    research_provider: str = Field(sa_column=Column(String(64), nullable=False))
    run_provider: str = Field(sa_column=Column(String(64), nullable=False))
    keywords: list = Field(default_factory=list, sa_column=Column(JSONB, nullable=False))
    market_type: str = Field(sa_column=Column(String(32), nullable=False))
    max_queries: int = Field(sa_column=Column(Integer, nullable=False))
    audience_name: str = Field(sa_column=Column(String(200), nullable=False))
    audience_description: str = Field(sa_column=Column(Text, nullable=False))
    intent_category: str = Field(sa_column=Column(String(100), nullable=False))
    intent_description: str = Field(sa_column=Column(Text, nullable=False))
    should_mention_own_brand: bool = Field(sa_column=Column(Boolean, nullable=False))
    should_mention_competitor: bool = Field(sa_column=Column(Boolean, nullable=False))
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    updated_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))


class TenantKMindHubWorkspaceMappingRow(SQLModel, table=True):
    """每個 tenant 對應一個 KMindHub Insight workspace 的 reference-only mapping。"""

    __tablename__ = "tenant_kmindhub_workspace_mapping"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            name="ux_tenant_kmindhub_workspace_mapping_tenant",
        ),
    )

    id: UUID = Field(primary_key=True)
    tenant_id: UUID = Field(nullable=False, index=True)
    workspace_id: UUID = Field(nullable=False)
    display_name: str = Field(sa_column=Column(String(200), nullable=False))
    provisioning_mode: str = Field(sa_column=Column(String(32), nullable=False))
    status: str = Field(sa_column=Column(String(32), nullable=False))
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    updated_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))


class TenantKMindHubExtractionTaskMappingRow(SQLModel, table=True):
    """每個 tenant 的 GEO extraction schema version 對應一個 KMindHub task。"""

    __tablename__ = "tenant_kmindhub_extraction_task_mapping"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "task_key",
            "schema_version",
            name="ux_tenant_kmindhub_extraction_task_mapping_version",
        ),
    )

    id: UUID = Field(primary_key=True)
    tenant_id: UUID = Field(nullable=False, index=True)
    workspace_id: UUID = Field(nullable=False)
    task_key: str = Field(sa_column=Column(String(100), nullable=False))
    schema_version: int = Field(sa_column=Column(Integer, nullable=False))
    kmindhub_task_id: UUID = Field(nullable=False)
    status: str = Field(sa_column=Column(String(32), nullable=False))
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    updated_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))


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


class GeoQueryResearchRunRow(SQLModel, table=True):
    __tablename__ = "geo_query_research_run"

    id: UUID = Field(primary_key=True)
    project_id: UUID = Field(foreign_key="geo_project.id", nullable=False)
    provider: str = Field(sa_column=Column(String(64), nullable=False))
    status: str = Field(sa_column=Column(String(32), nullable=False))
    request_payload: dict = Field(sa_column=Column(JSONB, nullable=False))
    research_context: str | None = Field(default=None, sa_column=Column(Text))
    searched_keywords: list = Field(default_factory=list, sa_column=Column(JSONB, nullable=False))
    source_urls: list = Field(default_factory=list, sa_column=Column(JSONB, nullable=False))
    error_code: str | None = Field(default=None, sa_column=Column(String(100)))
    error_message: str | None = Field(default=None, sa_column=Column(Text))
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    completed_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True)))


class GeoQueryGenerationRunRow(SQLModel, table=True):
    __tablename__ = "geo_query_generation_run"

    id: UUID = Field(primary_key=True)
    project_id: UUID = Field(foreign_key="geo_project.id", nullable=False)
    provider: str = Field(sa_column=Column(String(64), nullable=False))
    status: str = Field(sa_column=Column(String(32), nullable=False))
    request_payload: dict = Field(sa_column=Column(JSONB, nullable=False))
    error_code: str | None = Field(default=None, sa_column=Column(String(100)))
    error_message: str | None = Field(default=None, sa_column=Column(Text))
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    completed_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True)))


class GeoQueryDraftRow(SQLModel, table=True):
    __tablename__ = "geo_query_draft"

    id: UUID = Field(primary_key=True)
    generation_run_id: UUID = Field(foreign_key="geo_query_generation_run.id", nullable=False)
    project_id: UUID = Field(foreign_key="geo_project.id", nullable=False)
    topic_id: UUID | None = Field(default=None, foreign_key="geo_topic.id")
    topic_name: str = Field(default="", sa_column=Column(String(200), nullable=False))
    query_text: str = Field(sa_column=Column(Text, nullable=False))
    keywords: list = Field(default_factory=list, sa_column=Column(JSONB, nullable=False))
    region: str = Field(sa_column=Column(String(16), nullable=False))
    language: str = Field(sa_column=Column(String(16), nullable=False))
    market_type: str = Field(sa_column=Column(String(32), nullable=False))
    intent: str | None = Field(default=None, sa_column=Column(String(32)))
    is_branded: bool = Field(default=False, sa_column=Column(Boolean, nullable=False))
    status: str = Field(default="draft", sa_column=Column(String(32), nullable=False))
    selection_status: str | None = Field(default=None, sa_column=Column(String(32)))
    accepted_query_id: UUID | None = Field(default=None, foreign_key="geo_query.id")
    metadata_json: dict = Field(default_factory=dict, sa_column=Column("metadata", JSONB, nullable=False))
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    updated_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))


class GeoQueryDraftSelectionRow(SQLModel, table=True):
    __tablename__ = "geo_query_draft_selection"

    id: UUID = Field(primary_key=True)
    draft_id: UUID = Field(foreign_key="geo_query_draft.id", nullable=False)
    selection_status: str = Field(sa_column=Column(String(32), nullable=False))
    query_id: UUID | None = Field(default=None, foreign_key="geo_query.id")
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


class GeoDailyRunBatchRow(SQLModel, table=True):
    """每個 Project 在單一營業日只保存一筆冪等展開批次。"""

    __tablename__ = "geo_daily_run_batch"
    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "business_date",
            name="ux_geo_daily_run_batch_project_date",
        ),
    )

    id: UUID = Field(primary_key=True)
    project_id: UUID = Field(foreign_key="geo_project.id", nullable=False)
    business_date: date = Field(sa_column=Column(Date, nullable=False))
    scheduled_for: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    status: str = Field(sa_column=Column(String(32), nullable=False))
    candidate_count: int = Field(default=0, nullable=False)
    job_count: int = Field(default=0, nullable=False)
    budget_enforced: bool = Field(default=False, sa_column=Column(Boolean, nullable=False))
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    updated_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))


class GeoQueryRunJobRow(SQLModel, table=True):
    """Persistent query run job dispatched through the configured broker."""

    __tablename__ = "geo_query_run_job"
    __table_args__ = (
        Index(
            "ux_geo_query_run_job_scheduled_identity",
            "query_id",
            "platform_id",
            "scheduled_for",
            unique=True,
            postgresql_where=text("source = 'scheduled'"),
        ),
        Index(
            "ux_geo_query_run_job_daily_slot",
            "query_id",
            "platform_id",
            "business_date",
            unique=True,
            postgresql_where=text("is_daily_slot_owner = true"),
        ),
    )

    id: UUID = Field(primary_key=True)
    project_id: UUID = Field(foreign_key="geo_project.id", nullable=False)
    query_id: UUID = Field(foreign_key="geo_query.id", nullable=False)
    platform_id: UUID = Field(foreign_key="geo_ai_platform.id", nullable=False)
    batch_id: UUID | None = Field(default=None, foreign_key="geo_daily_run_batch.id")
    schedule_id: UUID | None = Field(default=None, foreign_key="geo_query_schedule.id")
    source: str = Field(default="manual", sa_column=Column(String(32), nullable=False))
    job_type: str = Field(default="scheduled_run", sa_column=Column(String(32), nullable=False))
    priority: str = Field(default="normal", sa_column=Column(String(32), nullable=False))
    scheduled_for: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    business_date: date | None = Field(
        default=None,
        sa_column=Column(
            Date,
            Computed("(scheduled_for AT TIME ZONE 'Asia/Taipei')::date", persisted=True),
            nullable=False,
        ),
    )
    is_daily_slot_owner: bool = Field(
        default=True,
        sa_column=Column(Boolean, nullable=False, server_default=text("true")),
    )
    status: str = Field(sa_column=Column(String(32), nullable=False))
    attempt_count: int = Field(default=0, nullable=False)
    max_attempts: int = Field(default=3, nullable=False)
    next_retry_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True)),
    )
    dedupe_key: str = Field(sa_column=Column(String(200), nullable=False, unique=True))
    execution_snapshot: dict = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False),
    )
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


class GeoRunResultAnalysisRow(SQLModel, table=True):
    """KMindHub 對單筆 raw run result 的報表前處理狀態與摘要。"""

    __tablename__ = "geo_run_result_analysis"
    __table_args__ = (
        UniqueConstraint(
            "run_result_id",
            "task_key",
            "schema_version",
            name="ux_geo_run_result_analysis_version",
        ),
    )

    id: UUID = Field(primary_key=True)
    run_result_id: UUID = Field(foreign_key="geo_run_result.id", nullable=False)
    task_key: str = Field(sa_column=Column(String(100), nullable=False))
    schema_version: int = Field(sa_column=Column(Integer, nullable=False))
    status: str = Field(sa_column=Column(String(32), nullable=False))
    analyzer: str | None = Field(default=None, sa_column=Column(String(64)))
    analyzer_version: str | None = Field(default=None, sa_column=Column(String(100)))
    summary: str | None = Field(default=None, sa_column=Column(Text))
    overall_sentiment: str | None = Field(default=None, sa_column=Column(String(32)))
    theme: str | None = Field(default=None, sa_column=Column(String(200)))
    kmindhub_commit_batch_id: str | None = Field(default=None, sa_column=Column(String(200)))
    kmindhub_item_id: str | None = Field(default=None, sa_column=Column(String(200)))
    error_code: str | None = Field(default=None, sa_column=Column(String(100)))
    error_message: str | None = Field(default=None, sa_column=Column(Text))
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    updated_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    completed_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True)))


class GeoRunResultEntityMentionRow(SQLModel, table=True):
    """AI answer 中被擷取出的品牌、競品或其他 entity mention。"""

    __tablename__ = "geo_run_result_entity_mention"

    id: UUID = Field(primary_key=True)
    run_result_id: UUID = Field(foreign_key="geo_run_result.id", nullable=False)
    analysis_id: UUID = Field(foreign_key="geo_run_result_analysis.id", nullable=False)
    entity_id: UUID | None = Field(default=None)
    entity_name: str = Field(sa_column=Column(String(200), nullable=False))
    entity_type: str = Field(sa_column=Column(String(32), nullable=False))
    entity_role: str | None = Field(default=None, sa_column=Column(String(32)))
    mentioned: bool | None = Field(default=None, sa_column=Column(Boolean))
    first_mention_order: int | None = Field(default=None, sa_column=Column(Integer))
    mention_count: int = Field(sa_column=Column(Integer, nullable=False))
    sentiment: str = Field(sa_column=Column(String(32), nullable=False))
    evidence_text: str = Field(default="", sa_column=Column(Text, nullable=False))
    confidence: float | None = Field(default=None, sa_column=Column(Numeric(5, 4)))
    kmindhub_item_id: str | None = Field(default=None, sa_column=Column(String(200)))
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))


class GeoRunResultStatementRow(SQLModel, table=True):
    """AI answer 中可供報表檢視的重要陳述。"""

    __tablename__ = "geo_run_result_statement"

    id: UUID = Field(primary_key=True)
    run_result_id: UUID = Field(foreign_key="geo_run_result.id", nullable=False)
    analysis_id: UUID = Field(foreign_key="geo_run_result_analysis.id", nullable=False)
    statement_text: str = Field(sa_column=Column(Text, nullable=False))
    entity_id: UUID | None = Field(default=None)
    entity_role: str | None = Field(default=None, sa_column=Column(String(32)))
    entity_name: str | None = Field(default=None, sa_column=Column(String(200)))
    theme: str = Field(default="", sa_column=Column(String(200), nullable=False))
    sentiment: str = Field(sa_column=Column(String(32), nullable=False))
    subject_entity_name: str | None = Field(default=None, sa_column=Column(String(200)))
    evidence_text: str = Field(default="", sa_column=Column(Text, nullable=False))
    confidence: float | None = Field(default=None, sa_column=Column(Numeric(5, 4)))
    kmindhub_item_id: str | None = Field(default=None, sa_column=Column(String(200)))
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))


class GeoResponseSemanticFactRow(SQLModel, table=True):
    """從 provider 原始回應中抽取出的語意事實。"""

    __tablename__ = "geo_response_semantic_fact"

    id: UUID = Field(primary_key=True)
    analysis_id: UUID = Field(foreign_key="geo_run_result_analysis.id", nullable=False)
    run_result_id: UUID = Field(foreign_key="geo_run_result.id", nullable=False)
    fact_type: str = Field(sa_column=Column(String(32), nullable=False))
    value: str = Field(sa_column=Column(Text, nullable=False))
    evidence_text: str | None = Field(default=None, sa_column=Column(Text))
    confidence: float | None = Field(default=None, sa_column=Column(Numeric(5, 4)))
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))


class GeoRunResultCitationClassificationRow(SQLModel, table=True):
    """既有 citation reference 的分類結果，URL 來源仍以 raw reference 為準。"""

    __tablename__ = "geo_run_result_citation_classification"

    id: UUID = Field(primary_key=True)
    run_result_reference_id: UUID = Field(
        foreign_key="geo_run_result_reference.id",
        nullable=False,
    )
    analysis_id: UUID = Field(foreign_key="geo_run_result_analysis.id", nullable=False)
    classification: str = Field(sa_column=Column(String(32), nullable=False))
    matched_entity_id: UUID | None = Field(default=None)
    matched_domain: str | None = Field(default=None, sa_column=Column(String(255)))
    confidence: float | None = Field(default=None, sa_column=Column(Numeric(5, 4)))
    source: str = Field(default="rule_based", sa_column=Column(String(64), nullable=False))
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))


class GeoRunResultCitationNormalizationRow(SQLModel, table=True):
    """單筆 run result citation normalization lifecycle。"""

    __tablename__ = "geo_run_result_citation_normalization"
    __table_args__ = (
        UniqueConstraint(
            "run_result_id",
            "normalizer_version",
            name="ux_geo_run_result_citation_normalization_version",
        ),
    )

    id: UUID = Field(primary_key=True)
    run_result_id: UUID = Field(foreign_key="geo_run_result.id", nullable=False)
    project_id: UUID = Field(foreign_key="geo_project.id", nullable=False)
    normalizer_version: str = Field(sa_column=Column(String(100), nullable=False))
    status: str = Field(sa_column=Column(String(32), nullable=False))
    error_code: str | None = Field(default=None, sa_column=Column(String(100)))
    error_message: str | None = Field(default=None, sa_column=Column(Text))
    skipped_reference_count: int = Field(
        default=0,
        sa_column=Column(Integer, nullable=False),
    )
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    updated_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    completed_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True)))


class GeoRunResultCitationRow(SQLModel, table=True):
    """Normalized citation fact used by report metrics."""

    __tablename__ = "geo_run_result_citation"

    id: UUID = Field(primary_key=True)
    normalization_id: UUID = Field(
        foreign_key="geo_run_result_citation_normalization.id",
        nullable=False,
    )
    run_result_id: UUID = Field(foreign_key="geo_run_result.id", nullable=False)
    reference_id: UUID = Field(foreign_key="geo_run_result_reference.id", nullable=False)
    url: str = Field(sa_column=Column(Text, nullable=False))
    domain: str = Field(sa_column=Column(String(255), nullable=False))
    title: str | None = Field(default=None, sa_column=Column(Text))
    position: int = Field(sa_column=Column(Integer, nullable=False))
    ownership: str = Field(sa_column=Column(String(32), nullable=False))
    source_type: str = Field(sa_column=Column(String(32), nullable=False))
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
