from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


def _camel_case(value: str) -> str:
    head, *tail = value.split("_")
    return head + "".join(part.capitalize() for part in tail)


class ContractModel(BaseModel):
    """GEO application 邊界使用的 camelCase contract 基底。"""

    model_config = ConfigDict(alias_generator=_camel_case, populate_by_name=True)


class QueryRunJobMessage(ContractModel):
    """發布到 provider queue 的 GEO query run job message。"""

    job_id: UUID
    tenant_id: UUID
    project_id: UUID
    seo_task_id: UUID
    query_id: UUID
    query_text: str
    topic_name: str
    platform: str
    model: str | None = None
    region: str
    language: str
    market_type: str
    is_branded: bool
    scheduled_for: datetime
    callback_url: str


class GeoQueryRunJobDispatchContext(ContractModel):
    """從已保存 job 組出 broker message 所需的 dispatch read model。"""

    job_id: UUID
    tenant_id: UUID
    project_id: UUID
    seo_task_id: UUID | None
    query_id: UUID
    query_text: str
    topic_name: str
    platform: str
    model: str | None = None
    region: str
    language: str
    market_type: str
    is_branded: bool
    scheduled_for: datetime


class TrackingRunResult(ContractModel):
    """runner service 回傳給 worker 的最終執行狀態。"""

    external_run_id: str
    status: str
    error_code: str | None = None
    error_message: str | None = None


class TrackingRunReference(ContractModel):
    """Provider 回傳的一筆來源引用。"""

    url: str
    title: str | None = None


class TrackingRunResultItem(ContractModel):
    """Provider 對單一 query 的跑題結果。"""

    id: str
    run_request_id: str
    query_id: UUID
    provider: str
    surface: str
    model: str
    region: str
    language: str
    status: str
    raw_response: str
    reference_urls: list[str] = Field(default_factory=list)
    references: list[TrackingRunReference] = Field(default_factory=list)
    error: str | None = None
    run_at: datetime


class TrackingRunResponse(ContractModel):
    """geo-tracking /run-requests 的完整 response。"""

    id: str
    seo_task_id: UUID
    timing: str
    results: list[TrackingRunResultItem] = Field(default_factory=list)


class SaveTrackingRunResultCommand(ContractModel):
    """保存 worker 呼叫 tracking 後的 raw result 與 orchestration 狀態。"""

    message: QueryRunJobMessage
    response: TrackingRunResponse | None = None
    status: str
    error_code: str | None = None
    error_message: str | None = None
    request_payload: dict = Field(default_factory=dict)


class GeoRunResultReferenceRecord(ContractModel):
    """已保存的 run result reference。"""

    id: UUID
    run_result_id: UUID
    url: str
    title: str | None = None
    domain: str | None = None
    position: int


class GeoRunResultRecord(ContractModel):
    """已保存的 GEO run result raw data。"""

    id: UUID
    run_request_id: UUID
    job_id: UUID
    tracking_result_id: str
    query_id: UUID
    provider: str
    surface: str
    model: str
    region: str
    language: str
    status: str
    raw_response: str
    error: str | None = None
    run_at: datetime
    references: list[GeoRunResultReferenceRecord] = Field(default_factory=list)
    created_at: datetime


class GeoRunRequestRecord(ContractModel):
    """已保存的 worker tracking request 與其 results。"""

    id: UUID
    job_id: UUID
    tracking_run_request_id: str
    seo_task_id: UUID
    provider: str
    timing: str
    status: str
    error_code: str | None = None
    error_message: str | None = None
    request_payload: dict = Field(default_factory=dict)
    created_at: datetime
    completed_at: datetime | None = None
    results: list[GeoRunResultRecord] = Field(default_factory=list)


class PublishResult(ContractModel):
    """message publisher 寫入 broker 後的結果與 evidence。"""

    backend: str
    destination: str
    message_id: str | None = None
    status: str
    error_message: str | None = None


class ExternalRunCallback(ContractModel):
    """外部 runner 回寫 job 狀態的 callback，不包含 AI result content。"""

    job_id: UUID
    external_run_id: str
    status: str
    result_location: str | None = None
    error_code: str | None = None
    error_message: str | None = None


class GeoProjectCommand(ContractModel):
    """建立或更新 GEO project 的 application input。"""

    tenant_id: UUID
    customer_id: UUID | None = None
    seo_task_id: UUID | None = None
    name: str
    default_region: str = "TW"
    default_language: str = "zh-TW"
    status: str = "active"
    daily_run_budget: int = 0


class GeoProjectRecord(GeoProjectCommand):
    """已保存的 GEO project 記錄。"""

    id: UUID
    created_at: datetime
    updated_at: datetime


class GeoMarketCommand(ContractModel):
    """建立或更新 GEO market locale 的 application input。"""

    region: str
    language: str
    market_name: str
    prompt_locale_hint: str = ""
    serp_gl: str | None = None
    serp_hl: str | None = None
    serp_location: str | None = None
    status: str = "active"


class GeoMarketRecord(GeoMarketCommand):
    """已保存的 GEO market locale 記錄。"""

    id: UUID
    project_id: UUID
    created_at: datetime
    updated_at: datetime


class GeoEntityCommand(ContractModel):
    """建立或更新 tracked entity 的 application input。"""

    entity_type: str
    name: str
    website_url: str | None = None
    description: str = ""
    status: str = "active"


class GeoEntityRecord(GeoEntityCommand):
    """已保存的 tracked entity 記錄。"""

    id: UUID
    project_id: UUID
    created_at: datetime
    updated_at: datetime


class GeoEntityAliasCommand(ContractModel):
    """建立或更新 tracked entity alias 的 application input。"""

    alias: str
    match_type: str = "exact"


class GeoEntityAliasRecord(GeoEntityAliasCommand):
    """已保存的 tracked entity alias 記錄。"""

    id: UUID
    entity_id: UUID
    created_at: datetime


class GeoTopicCommand(ContractModel):
    """建立或更新 GEO query topic 的 application input。"""

    name: str
    description: str = ""
    status: str = "active"


class GeoTopicRecord(GeoTopicCommand):
    """已保存的 GEO query topic 記錄。"""

    id: UUID
    project_id: UUID
    created_at: datetime
    updated_at: datetime


class GeoQueryCommand(ContractModel):
    """建立或更新 tracked query 的 application input。"""

    topic_id: UUID | None = None
    query_text: str
    region: str
    language: str
    market_type: str = "b2b_procurement"
    intent: str | None = None
    buyer_stage: str | None = None
    is_branded: bool = False
    priority: str = "normal"
    status: str = "active"
    metadata: dict = Field(default_factory=dict)


class GeoQueryRecord(GeoQueryCommand):
    """已保存的 tracked query 記錄。"""

    id: UUID
    project_id: UUID
    created_at: datetime
    updated_at: datetime


class QueryAudience(ContractModel):
    name: str
    description: str


class QueryIntent(ContractModel):
    category: str
    description: str


class BrandMentionRules(ContractModel):
    should_mention_own_brand: bool = True
    should_mention_competitor: bool = False


class QueryResearchCommand(ContractModel):
    provider: str = "dummy"
    brand_name: str
    competitor_brands: list[str] = Field(default_factory=list, max_length=8)
    keywords: list[str] = Field(min_length=1, max_length=10)
    region: str
    language: str | None = None
    market_type: str = "b2b_procurement"
    intents: list[QueryIntent] = Field(default_factory=list, max_length=8)
    audience: QueryAudience | None = None
    brand_mention_rules: BrandMentionRules = Field(default_factory=BrandMentionRules)


class QueryResearchResultRecord(ContractModel):
    research_context: str
    searched_keywords: list[str] = Field(default_factory=list)
    source_urls: list[str] = Field(default_factory=list)


class QueryResearchRunRecord(ContractModel):
    id: UUID
    project_id: UUID
    provider: str
    status: str
    request_payload: dict = Field(default_factory=dict)
    result: QueryResearchResultRecord | None = None
    error_code: str | None = None
    error_message: str | None = None
    created_at: datetime
    completed_at: datetime | None = None


class QueryGenerationCommand(ContractModel):
    seo_task_id: UUID
    provider: str = "dummy"
    brand_name: str
    competitor_brands: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    region: str
    language: str | None = None
    market_type: str = "b2b_procurement"
    topics: list[dict] = Field(default_factory=list)
    topic_names: list[str] = Field(default_factory=list)
    intents: list[QueryIntent] = Field(default_factory=list)
    audience: QueryAudience
    brand_mention_rules: BrandMentionRules = Field(default_factory=BrandMentionRules)
    research_context: str | None = None
    max_queries: int = 12


class QueryDraftRecord(ContractModel):
    id: UUID
    generation_run_id: UUID
    project_id: UUID
    topic_id: UUID | None = None
    topic_name: str
    query_text: str
    keywords: list[str] = Field(default_factory=list)
    region: str
    language: str
    market_type: str
    intent: str | None = None
    is_branded: bool
    status: str = "draft"
    selection_status: str | None = None
    accepted_query_id: UUID | None = None
    metadata: dict = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class QueryGenerationRunRecord(ContractModel):
    id: UUID
    project_id: UUID
    provider: str
    status: str
    request_payload: dict = Field(default_factory=dict)
    error_code: str | None = None
    error_message: str | None = None
    created_at: datetime
    completed_at: datetime | None = None
    drafts: list[QueryDraftRecord] = Field(default_factory=list)


class QueryDraftSelectionCommand(ContractModel):
    selection_status: str


class AcceptQueryDraftCommand(ContractModel):
    create_topic_if_missing: bool = True
    status: str = "active"


class GeoQueryPlatformCommand(ContractModel):
    """建立或更新 tracked query platform assignment 的 application input。"""

    platform_id: UUID
    model: str | None = None
    status: str = "active"


class GeoQueryPlatformRecord(GeoQueryPlatformCommand):
    """已保存的 query platform assignment 記錄。"""

    id: UUID
    query_id: UUID
    created_at: datetime
    updated_at: datetime


class GeoQueryScheduleCommand(ContractModel):
    """建立或更新 query/platform schedule 的 application input。"""

    platform_id: UUID
    frequency: str
    priority: str = "normal"
    timezone: str = "Asia/Taipei"
    next_run_at: datetime | None = None
    status: str = "active"


class GeoQueryScheduleRecord(GeoQueryScheduleCommand):
    """已保存的 query/platform schedule 記錄。"""

    id: UUID
    query_id: UUID
    last_scheduled_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class CreateQueryRunJobCommand(ContractModel):
    """從 tracked query 建立 query run job 的 application input。"""

    platform_id: UUID
    scheduled_for: datetime | None = None
    priority: str = "normal"
    job_type: str = "manual_run"
