from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _camel_case(value: str) -> str:
    head, *tail = value.split("_")
    return head + "".join(part.capitalize() for part in tail)


class ApiModel(BaseModel):
    """使用 camelCase JSON 欄位的 GEO API DTO 基底模型。"""

    model_config = ConfigDict(alias_generator=_camel_case, populate_by_name=True)


class ProjectRequest(ApiModel):
    """客戶擁有、可編輯的 GEO project 設定。"""

    customer_id: UUID | None = None
    seo_task_id: UUID | None = None
    name: str = Field(min_length=1, max_length=200)
    default_region: str = Field(default="TW", min_length=1, max_length=16)
    default_language: str = Field(default="zh-TW", min_length=1, max_length=16)
    status: str = Field(default="active", max_length=32)
    daily_run_budget: int = Field(default=0, ge=0)

    @field_validator("name", "default_region", "default_language", "status")
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("value must not be empty")
        return normalized


class ProjectResponse(ProjectRequest):
    """回傳給後台的 GEO project resource。"""

    id: UUID
    created_at: datetime
    updated_at: datetime


class MarketRequest(ApiModel):
    """外部 runner message 使用的 market locale 與 SERP 參數提示。"""

    region: str = Field(min_length=1, max_length=16)
    language: str = Field(min_length=1, max_length=16)
    market_name: str = Field(min_length=1, max_length=100)
    prompt_locale_hint: str = ""
    serp_gl: str | None = None
    serp_hl: str | None = None
    serp_location: str | None = None
    status: str = Field(default="active", max_length=32)


class MarketResponse(MarketRequest):
    """用來控制 query locale 與 runner 提示的 market resource。"""

    id: UUID
    project_id: UUID
    created_at: datetime
    updated_at: datetime


class EntityRequest(ApiModel):
    """要追蹤的主要品牌、競品或相關 entity。"""

    entity_type: str = Field(min_length=1, max_length=32)
    name: str = Field(min_length=1, max_length=200)
    website_url: str | None = None
    description: str = ""
    status: str = Field(default="active", max_length=32)


class EntityResponse(EntityRequest):
    """不包含 mention extraction data 的 tracked entity resource。"""

    id: UUID
    project_id: UUID
    created_at: datetime
    updated_at: datetime


class AliasRequest(ApiModel):
    """傳給 runner 或分析模組的 entity 替代名稱。"""

    alias: str = Field(min_length=1, max_length=200)
    match_type: str = Field(default="exact", max_length=32)


class AliasResponse(AliasRequest):
    """由 GEO setup UI 管理的 entity alias resource。"""

    id: UUID
    entity_id: UUID
    created_at: datetime


class TopicRequest(ApiModel):
    """GEO project 內用來群組 query 的 metadata。"""

    name: str = Field(min_length=1, max_length=200)
    description: str = ""
    status: str = Field(default="active", max_length=32)

    @field_validator("name", "status")
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("value must not be empty")
        return normalized


class TopicResponse(TopicRequest):
    """用來組織 tracked query 的 topic resource。"""

    id: UUID
    project_id: UUID
    created_at: datetime
    updated_at: datetime


class QueryRequest(ApiModel):
    """準備派送給外部 GEO runner 的自然語言問題。"""

    topic_id: UUID | None = None
    query_text: str = Field(min_length=1)
    region: str = Field(min_length=1, max_length=16)
    language: str = Field(min_length=1, max_length=16)
    market_type: str = Field(default="b2b_procurement", max_length=32)
    intent: str | None = None
    buyer_stage: str | None = None
    is_branded: bool = False
    priority: str = Field(default="normal", max_length=32)
    status: str = Field(default="active", max_length=32)
    metadata: dict = Field(default_factory=dict)

    @field_validator("query_text", "region", "language", "priority", "status")
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("value must not be empty")
        return normalized

    @field_validator("market_type")
    @classmethod
    def validate_market_type(cls, value: str) -> str:
        normalized = value.strip()
        if normalized not in {"b2c", "b2b_procurement"}:
            raise ValueError("marketType must be b2c or b2b_procurement")
        return normalized


class QueryResponse(QueryRequest):
    """不包含 AI response 或 metric data 的 tracked query resource。"""

    id: UUID
    project_id: UUID
    created_at: datetime
    updated_at: datetime


class QueryAudienceRequest(ApiModel):
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)


class QueryIntentRequest(ApiModel):
    category: str = Field(min_length=1)
    description: str = Field(min_length=1)


class BrandMentionRulesRequest(ApiModel):
    should_mention_own_brand: bool = True
    should_mention_competitor: bool = False


class QueryResearchRunRequest(ApiModel):
    provider: str = Field(default="dummy", min_length=1)
    brand_name: str = Field(min_length=1, max_length=200)
    competitor_brands: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    region: str = Field(min_length=1, max_length=16)
    language: str | None = None
    market_type: str = Field(default="b2b_procurement", max_length=32)
    audience: QueryAudienceRequest | None = None


class QueryResearchResultResponse(ApiModel):
    research_context: str
    searched_keywords: list[str]
    source_urls: list[str]


class QueryResearchRunResponse(ApiModel):
    id: UUID
    project_id: UUID
    provider: str
    status: str
    request_payload: dict
    result: QueryResearchResultResponse | None
    error_code: str | None
    error_message: str | None
    created_at: datetime
    completed_at: datetime | None


class QueryGenerationRunRequest(ApiModel):
    seo_task_id: UUID
    provider: str = Field(default="dummy", min_length=1)
    brand_name: str = Field(min_length=1, max_length=200)
    competitor_brands: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    region: str = Field(min_length=1, max_length=16)
    language: str | None = None
    market_type: str = Field(default="b2b_procurement", max_length=32)
    topics: list[dict] = Field(default_factory=list)
    topic_names: list[str] = Field(default_factory=list)
    intents: list[QueryIntentRequest] = Field(default_factory=list)
    audience: QueryAudienceRequest
    brand_mention_rules: BrandMentionRulesRequest = Field(
        default_factory=BrandMentionRulesRequest
    )
    research_context: str | None = None
    max_queries: int = Field(default=12, ge=1, le=40)


class QueryDraftResponse(ApiModel):
    id: UUID
    generation_run_id: UUID
    project_id: UUID
    topic_id: UUID | None
    topic_name: str
    query_text: str
    keywords: list[str]
    region: str
    language: str
    market_type: str
    intent: str | None
    is_branded: bool
    status: str
    selection_status: str | None
    accepted_query_id: UUID | None
    metadata: dict
    created_at: datetime
    updated_at: datetime


class QueryGenerationRunResponse(ApiModel):
    id: UUID
    project_id: UUID
    provider: str
    status: str
    request_payload: dict
    error_code: str | None
    error_message: str | None
    created_at: datetime
    completed_at: datetime | None
    drafts: list[QueryDraftResponse]


class QueryDraftSelectionRequest(ApiModel):
    selection_status: str = Field(min_length=1, max_length=32)


class AcceptQueryDraftRequest(ApiModel):
    create_topic_if_missing: bool = True
    status: str = Field(default="active", max_length=32)


class QueryPlatformRequest(ApiModel):
    """tracked query 的 platform 選擇。"""

    platform_id: UUID
    model: str | None = None
    status: str = Field(default="active", max_length=32)


class QueryPlatformResponse(QueryPlatformRequest):
    """回傳給 setup UI 的 platform assignment。"""

    id: UUID
    query_id: UUID
    created_at: datetime
    updated_at: datetime


class ScheduleRequest(ApiModel):
    """單一 query/platform pair 的週期性派送排程。"""

    platform_id: UUID
    frequency: str = Field(min_length=1, max_length=32)
    priority: str = Field(default="normal", max_length=32)
    timezone: str = Field(default="Asia/Taipei", max_length=64)
    next_run_at: datetime | None = None
    status: str = Field(default="active", max_length=32)


class ScheduleResponse(ScheduleRequest):
    """用來建立未來 query run job 的 schedule resource。"""

    id: UUID
    query_id: UUID
    last_scheduled_at: datetime | None
    created_at: datetime
    updated_at: datetime


class CreateJobRequest(ApiModel):
    """針對 query 與目標 platform 建立手動派送 job 的 request。"""

    platform_id: UUID
    scheduled_for: datetime | None = None
    priority: str = Field(default="normal", max_length=32)
    job_type: str = Field(default="manual_run", max_length=32)


class JobResponse(ApiModel):
    """此模組擁有的 query run job orchestration 狀態。"""

    id: UUID
    project_id: UUID
    query_id: UUID
    platform_id: UUID
    schedule_id: UUID | None
    job_type: str
    priority: str
    scheduled_for: datetime
    status: str
    attempt_count: int
    max_attempts: int
    dedupe_key: str
    dispatch_backend: str | None
    dispatch_message_id: str | None
    external_run_id: str | None
    last_error_code: str | None
    last_error_message: str | None
    created_at: datetime
    updated_at: datetime


class ExternalCallbackRequest(ApiModel):
    """外部 runner 回報狀態用的 callback，不包含 result content。"""

    external_run_id: str = Field(min_length=1)
    status: str = Field(min_length=1)
    result_location: str | None = None
    error_code: str | None = None
    error_message: str | None = None


class RunResultReferenceResponse(ApiModel):
    """Run result 中的一筆 provider reference。"""

    id: UUID
    run_result_id: UUID
    url: str
    title: str | None
    domain: str | None
    position: int


class RunResultResponse(ApiModel):
    """已保存的 GEO run raw result。"""

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
    error: str | None
    run_at: datetime
    references: list[RunResultReferenceResponse]
    created_at: datetime


class PageResponse(ApiModel):
    """第一版 GEO 後台畫面使用的小型 collection response。"""

    items: list
    total: int
