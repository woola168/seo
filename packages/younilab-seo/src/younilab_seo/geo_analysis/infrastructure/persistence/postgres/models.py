from datetime import date, datetime
from uuid import UUID

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel, UniqueConstraint


class GeoProjectRow(SQLModel, table=True):
    """綁定既有 customer 的 project-level GEO setup row。"""

    __tablename__ = "geo_project"

    id: UUID = Field(primary_key=True)
    customer_id: UUID = Field(foreign_key="customer.id", nullable=False)
    seo_task_id: UUID | None = Field(default=None, foreign_key="seo_task.id")
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
    """準備外部 runner message 時使用的 market locale 設定。"""

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
    """GEO project 中要追蹤的品牌或競品 metadata。"""

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
    """傳給外部 runner 或分析模組的 tracked entity alias。"""

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
    """project 內用來群組 tracked query 的 topic。"""

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
    """排程給外部 GEO runner 執行的自然語言問題。"""

    __tablename__ = "geo_query"

    id: UUID = Field(primary_key=True)
    project_id: UUID = Field(foreign_key="geo_project.id", nullable=False)
    topic_id: UUID | None = Field(default=None, foreign_key="geo_topic.id")
    query_text: str = Field(sa_column=Column(Text, nullable=False))
    region: str = Field(sa_column=Column(String(16), nullable=False))
    language: str = Field(sa_column=Column(String(16), nullable=False))
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
    """附加在產生或人工整理 query 上的 keyword research 來源。"""

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
    """可選擇的 AI 或 SERP platform metadata，不包含 provider credential。"""

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
    """job 排程前針對 query 設定的 platform selection。"""

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
    """用來建立 dispatch job 的週期性 query/platform schedule。"""

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
    """application 擁有、且不依賴特定 message broker 的 dispatch job 狀態。"""

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
    """不綁定特定 broker 產品的 message dispatch 證據。"""

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
    """DB-scanning 或補償 worker 使用的 lease record。"""

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
    """記錄 job scheduling、dispatch、retry 與 callback transition 的 audit event。"""

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
    """外部 runner 狀態 reference，不儲存 AI response content。"""

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
