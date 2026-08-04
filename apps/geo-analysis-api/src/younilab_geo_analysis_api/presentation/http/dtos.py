from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def _camel_case(value: str) -> str:
    head, *tail = value.split("_")
    return head + "".join(part.capitalize() for part in tail)


class ApiModel(BaseModel):
    """使用 camelCase JSON 欄位的 GEO API DTO 基底模型。"""

    model_config = ConfigDict(alias_generator=_camel_case, populate_by_name=True)


class InvalidParamResponse(ApiModel):
    name: str
    reason: str
    type: str


class ProblemDetailsResponse(ApiModel):
    type: str
    title: str
    status: int
    detail: str
    instance: str
    invalid_params: list[InvalidParamResponse] | None = None


class ProjectRequest(ApiModel):
    """客戶擁有、可編輯的 GEO project 設定。"""

    model_config = ConfigDict(
        alias_generator=_camel_case,
        populate_by_name=True,
        extra="forbid",
    )

    customer_id: UUID | None = None
    seo_task_id: UUID | None = Field(
        default=None,
        deprecated=True,
        exclude=True,
    )
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
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime


class ProjectOwnBrandSummaryResponse(ApiModel):
    entity_id: UUID
    website_url: str | None = None
    aliases: list[str]


class ProjectSummaryResponse(ApiModel):
    id: UUID
    tenant_id: UUID
    customer_id: UUID | None = None
    customer_name: str | None = None
    name: str
    default_region: str
    default_language: str
    status: str
    daily_run_budget: int
    own_brand: ProjectOwnBrandSummaryResponse | None = None
    created_at: datetime
    updated_at: datetime


class ProjectSummaryPageResponse(ApiModel):
    items: list[ProjectSummaryResponse]
    total: int


class ProjectStatusRequest(ApiModel):
    model_config = ConfigDict(
        alias_generator=_camel_case,
        populate_by_name=True,
        extra="forbid",
    )

    status: Literal["active", "paused"]


class ProjectStatusResponse(ApiModel):
    project_id: UUID
    status: Literal["active", "paused"]
    updated_at: datetime


class QuerySettingsAudience(ApiModel):
    model_config = ConfigDict(
        alias_generator=_camel_case,
        populate_by_name=True,
        extra="forbid",
    )

    name: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=2000)

    @field_validator("name", "description")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("value must not be empty")
        return normalized


class QuerySettingsIntent(ApiModel):
    model_config = ConfigDict(
        alias_generator=_camel_case,
        populate_by_name=True,
        extra="forbid",
    )

    category: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=1, max_length=2000)

    @field_validator("category")
    @classmethod
    def normalize_category(cls, value: str) -> str:
        from younilab_seo.geo_analysis.application.query_intents import (
            normalize_standard_query_intent,
        )

        normalized = value.strip()
        if not normalized:
            raise ValueError("value must not be empty")
        category = normalize_standard_query_intent(normalized)
        if category is None:
            raise ValueError("unsupported query intent category")
        return category

    @field_validator("description")
    @classmethod
    def normalize_description(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("value must not be empty")
        return normalized


class ProjectQuerySettingsRequest(ApiModel):
    model_config = ConfigDict(
        alias_generator=_camel_case,
        populate_by_name=True,
        extra="forbid",
    )

    research_provider: Literal["gemini", "openai"]
    run_provider: Literal["gemini"]
    keywords: list[str] = Field(max_length=10)
    market_type: Literal["b2c", "b2b_procurement"]
    max_queries: int = Field(ge=1, le=40)
    audience: QuerySettingsAudience
    intents: list[QuerySettingsIntent] = Field(min_length=1, max_length=4)
    should_mention_own_brand: bool
    should_mention_competitor: bool

    @field_validator("keywords", mode="before")
    @classmethod
    def normalize_keywords(cls, values: object) -> object:
        if not isinstance(values, list):
            return values
        normalized: list[object] = []
        seen: set[str] = set()
        for value in values:
            if not isinstance(value, str):
                normalized.append(value)
                continue
            keyword = value.strip()
            if not keyword or keyword.casefold() in seen:
                continue
            if len(keyword) > 200:
                raise ValueError("keyword must contain at most 200 characters")
            seen.add(keyword.casefold())
            normalized.append(keyword)
        return normalized

    @model_validator(mode="before")
    @classmethod
    def accept_legacy_single_intent(cls, value: object) -> object:
        if not isinstance(value, dict) or "intents" in value or "intent" not in value:
            return value
        normalized = dict(value)
        normalized["intents"] = [normalized.pop("intent")]
        return normalized

    @model_validator(mode="after")
    def validate_intent_selection(self):
        categories = [intent.category for intent in self.intents]
        if len(categories) != len(set(categories)):
            raise ValueError("intent categories must be unique")
        if self.max_queries < len(categories):
            raise ValueError("maxQueries must cover every selected intent")
        return self


class ProjectQuerySettingsResponse(ProjectQuerySettingsRequest):
    model_config = ConfigDict(
        alias_generator=_camel_case,
        populate_by_name=True,
        extra="ignore",
    )

    project_id: UUID
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

    model_config = ConfigDict(
        alias_generator=_camel_case,
        populate_by_name=True,
        extra="forbid",
    )

    alias: str = Field(min_length=1, max_length=200)
    match_type: str = Field(default="exact", max_length=32)

    @field_validator("alias")
    @classmethod
    def normalize_alias(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("value must not be empty")
        return normalized


class AliasResponse(ApiModel):
    """由 GEO setup UI 管理的 entity alias resource。"""

    alias: str
    match_type: str
    id: UUID
    entity_id: UUID
    created_at: datetime


class AliasCollectionRequest(ApiModel):
    model_config = ConfigDict(
        alias_generator=_camel_case,
        populate_by_name=True,
        extra="forbid",
    )

    items: list[AliasRequest]

    @field_validator("items")
    @classmethod
    def require_unique_aliases(cls, items: list[AliasRequest]) -> list[AliasRequest]:
        values = [item.alias for item in items]
        if len(set(values)) != len(values):
            raise ValueError("alias values must be unique")
        return items


class AliasCollectionResponse(ApiModel):
    items: list[AliasResponse]
    total: int


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


class QueryStatusRequest(ApiModel):
    model_config = ConfigDict(
        alias_generator=_camel_case,
        populate_by_name=True,
        extra="forbid",
    )

    status: Literal["active", "paused"]


class QueryStatusResponse(QueryStatusRequest):
    query_id: UUID
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


class BrandAliasRequest(ApiModel):
    alias: str
    match_type: Literal["exact", "case_insensitive", "contains", "domain"]


class QueryResearchRunRequest(ApiModel):
    model_config = ConfigDict(extra="forbid")

    provider: str = Field(default="dummy", min_length=1)
    brand_name: str = Field(min_length=1, max_length=200)
    competitor_brands: list[str] = Field(default_factory=list, max_length=8)
    keywords: list[str] = Field(min_length=1, max_length=10)
    region: str = Field(min_length=1, max_length=16)
    language: str | None = None
    market_type: str = Field(default="b2b_procurement", max_length=32)
    audience: QueryAudienceRequest | None = None
    brand_mention_rules: BrandMentionRulesRequest = Field(
        default_factory=BrandMentionRulesRequest
    )


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
    provider: str = Field(default="dummy", min_length=1)
    brand_name: str = Field(min_length=1, max_length=200)
    own_brand_aliases: list[BrandAliasRequest] = Field(default_factory=list)
    competitor_brands: list[str] = Field(default_factory=list)
    competitor_aliases: list[BrandAliasRequest] = Field(default_factory=list)
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

    model_config = ConfigDict(
        alias_generator=_camel_case,
        populate_by_name=True,
        extra="forbid",
    )

    platform_id: UUID
    model: str | None = Field(default=None, exclude=True, deprecated=True)
    status: str = Field(default="active", max_length=32)


class AiPlatformResponse(ApiModel):
    """每日排程候選所使用的 GEO AI Platform 狀態。"""

    id: UUID
    code: str
    display_name: str
    provider_type: str
    default_model: str | None
    status: str


class QueryPlatformResponse(QueryPlatformRequest):
    """回傳給 setup UI 的 platform assignment。"""

    id: UUID
    query_id: UUID
    created_at: datetime
    updated_at: datetime


class ScheduleRequest(ApiModel):
    """舊版 Portal 使用的 query/platform schedule 相容 request。"""

    platform_id: UUID
    frequency: str = Field(min_length=1, max_length=32)
    priority: str = Field(default="normal", max_length=32)
    timezone: str = Field(default="Asia/Taipei", max_length=64)
    next_run_at: datetime | None = None
    status: str = Field(default="active", max_length=32)


class ScheduleResponse(ScheduleRequest):
    """舊版 Portal 使用的 schedule 相容 resource。"""

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
    batch_id: UUID | None
    schedule_id: UUID | None
    source: str
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


class CreateJobResponse(JobResponse):
    """建立每日 query run job 後回報是否取得新的執行額度。"""

    was_created: bool


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
    analysis_status: str | None = None
    analysis_error_code: str | None = None
    analysis_error_message: str | None = None


class RunResultEntityMentionResponse(ApiModel):
    entity_id: UUID
    entity_role: str
    entity_name: str
    mentioned: bool
    first_mention_order: int | None = None
    evidence_text: str | None = None
    confidence: float | None = None


class RunResultSentimentResponse(ApiModel):
    entity_id: UUID
    entity_role: str
    entity_name: str
    sentiment: str
    theme: str
    statement: str
    evidence_text: str | None = None
    confidence: float | None = None


class RunResultSemanticFactResponse(ApiModel):
    fact_type: str
    value: str
    evidence_text: str | None = None
    confidence: float | None = None


class RunResultSemanticAnalysisResponse(ApiModel):
    run_result_id: UUID
    analyzer: str
    analyzer_version: str | None = None
    status: str
    entity_mentions: list[RunResultEntityMentionResponse]
    sentiments: list[RunResultSentimentResponse]
    semantic_facts: list[RunResultSemanticFactResponse]
    error_code: str | None = None
    error_message: str | None = None


class MetricValueResponse(ApiModel):
    metric_name: str
    scope_type: str
    scope_value: str | None = None
    scope_label: str | None = None
    value: float
    unit: str
    numerator: float | None = None
    denominator: float | None = None
    comparison_value: float | None = None
    delta: float | None = None
    delta_unit: str | None = None


class MetricFormulaResultResponse(ApiModel):
    period_start: datetime
    period_end: datetime
    comparison_start: datetime
    comparison_end: datetime
    metrics: list[MetricValueResponse]


class DashboardMetricValueResponse(ApiModel):
    value: float
    unit: str
    numerator: float | None = None
    denominator: float | None = None
    comparison_value: float | None = None
    delta: float | None = None
    delta_unit: str | None = None


class DashboardOverviewCardResponse(ApiModel):
    metric_name: str
    label: str
    metric: DashboardMetricValueResponse


class DashboardEntityRowResponse(ApiModel):
    entity_id: UUID
    entity_role: str
    entity_name: str
    visibility: DashboardMetricValueResponse
    mentions: DashboardMetricValueResponse
    average_position: DashboardMetricValueResponse


class DashboardCitationRowResponse(ApiModel):
    scope_type: str
    value: str
    label: str
    ownership: str | None = None
    source_type: str | None = None
    citation_count: DashboardMetricValueResponse
    used_percent: DashboardMetricValueResponse
    share_percent: DashboardMetricValueResponse


class DashboardSentimentRowResponse(ApiModel):
    sentiment: str
    statement_count: DashboardMetricValueResponse


class DashboardReportResponse(ApiModel):
    period_start: datetime
    period_end: datetime
    comparison_start: datetime
    comparison_end: datetime
    overview: list[DashboardOverviewCardResponse]
    entities: list[DashboardEntityRowResponse]
    citation_urls: list[DashboardCitationRowResponse]
    citation_domains: list[DashboardCitationRowResponse]
    sentiments: list[DashboardSentimentRowResponse]


class OverviewFilterOptionResponse(ApiModel):
    value: str
    label: str


class OverviewFilterOptionsResponse(ApiModel):
    topics: list[OverviewFilterOptionResponse]
    platforms: list[OverviewFilterOptionResponse]
    regions: list[str]
    metadata_industries: list[str]
    metadata_types: list[str]


class OverviewKpiResponse(ApiModel):
    metric_name: str
    value: float
    unit: str
    numerator: float | None = None
    denominator: float | None = None
    secondary_label: str
    secondary_value: float | None = None
    secondary_unit: str | None = None
    delta: float | None = None
    delta_unit: str | None = None


class OverviewCitationSummaryResponse(ApiModel):
    owned_share_percent: float
    citation_count: int
    cited_page_count: int
    cited_response_percent: float


class OverviewTrendPointResponse(ApiModel):
    date: str
    value: float


class OverviewVisibilitySeriesResponse(ApiModel):
    entity_id: UUID
    entity_name: str
    entity_role: str
    points: list[OverviewTrendPointResponse]


class OverviewSentimentPointResponse(ApiModel):
    date: str
    positive_count: int
    negative_count: int
    positive_negative_ratio: float | None = None


class OverviewEntityRowResponse(ApiModel):
    entity_id: UUID
    entity_name: str
    entity_role: str
    visibility_percent: float
    visibility_delta_pp: float | None = None
    sov_percent: float
    average_position: float


class OverviewQueryRowResponse(ApiModel):
    query_id: UUID
    query_text: str
    visibility_percent: float
    sov_percent: float
    citation_count: int


class OverviewIntentGroupRowResponse(ApiModel):
    intent_category: Literal[
        "navigational",
        "informational",
        "commercial_investigation",
        "transactional",
        "unclassified",
    ]
    visibility_percent: float
    sov_percent: float
    citation_count: int
    queries: list[OverviewQueryRowResponse]


class OverviewTopicRowResponse(ApiModel):
    topic_id: UUID | None = None
    topic_name: str
    visibility_percent: float
    sov_percent: float
    citation_count: int
    queries: list[OverviewQueryRowResponse]


class OverviewCitationRowResponse(ApiModel):
    scope_type: str
    value: str
    title: str | None = None
    citation_count: int
    query_count: int
    citation_rate_percent: float
    citation_share_percent: float
    ownership: str | None = None
    source_type: str | None = None
    content_tag: str | None = None
    mentions_brand: bool | None = None
    mentioned_competitors: list[str] | None = None


class OverviewReportResponse(ApiModel):
    period_start: datetime
    period_end: datetime
    comparison_start: datetime
    comparison_end: datetime
    is_preparing: bool
    filter_options: OverviewFilterOptionsResponse
    overview: list[OverviewKpiResponse]
    citation_summary: OverviewCitationSummaryResponse
    visibility_trend: list[OverviewVisibilitySeriesResponse]
    sentiment_trend: list[OverviewSentimentPointResponse]
    entities: list[OverviewEntityRowResponse]
    topics: list[OverviewTopicRowResponse]
    intent_groups: list[OverviewIntentGroupRowResponse]
    citation_urls: list[OverviewCitationRowResponse]
    citation_domains: list[OverviewCitationRowResponse]


class OverviewResponseRowResponse(ApiModel):
    run_result_id: UUID
    query_id: UUID
    query_text: str
    response_excerpt: str
    mentioned: bool | None = None
    provider: str
    region: str
    completed_at: datetime
    reference_count: int
    positive_count: int
    negative_count: int


class OverviewResponsePageResponse(ApiModel):
    items: list[OverviewResponseRowResponse]
    total: int
    page: int
    page_size: int


class KMindHubWorkspaceMappingRequest(ApiModel):
    model_config = ConfigDict(
        alias_generator=_camel_case,
        populate_by_name=True,
        extra="forbid",
    )

    workspace_id: UUID
    display_name: str = Field(min_length=1, max_length=200)
    status: str = Field(default="active", max_length=32)


class KMindHubWorkspaceProvisionRequest(ApiModel):
    model_config = ConfigDict(
        alias_generator=_camel_case,
        populate_by_name=True,
        extra="forbid",
    )

    display_name: str = Field(min_length=1, max_length=200)


class KMindHubWorkspaceMappingResponse(ApiModel):
    id: UUID
    tenant_id: UUID
    workspace_id: UUID
    display_name: str
    provisioning_mode: str
    status: str
    created_at: datetime
    updated_at: datetime


class PageResponse(ApiModel):
    """第一版 GEO 後台畫面使用的小型 collection response。"""

    items: list
    total: int
