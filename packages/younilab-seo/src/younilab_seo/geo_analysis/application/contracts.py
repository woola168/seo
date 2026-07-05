from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


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
    analysis_status: str | None = None
    analysis_error_code: str | None = None
    analysis_error_message: str | None = None


class GeoAnalysisEntityInput(ContractModel):
    """Semantic analysis 使用的品牌或競品快照。"""

    entity_id: UUID
    entity_role: Literal["own_brand", "competitor"]
    name: str
    website_url: str | None = None


class GeoAnalysisEntityContext(ContractModel):
    """單筆 run result analysis 可比較的自有品牌與競品集合。"""

    own_brand: GeoAnalysisEntityInput
    competitors: list[GeoAnalysisEntityInput] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_entity_roles(self):
        if self.own_brand.entity_role != "own_brand":
            raise ValueError("ownBrand entityRole must be own_brand")
        if any(competitor.entity_role != "competitor" for competitor in self.competitors):
            raise ValueError("competitor entityRole must be competitor")
        return self


class AnalyzeGeoRunResultCommand(ContractModel):
    """送入 semantic analyzer 的完整 run result 與專案上下文。"""

    run_result_id: UUID
    project_id: UUID
    query_id: UUID
    query_text: str
    topic_id: UUID | None = None
    topic_name: str | None = None
    topic_description: str | None = None
    provider: str
    surface: str
    model: str
    region: str
    language: str
    raw_response: str
    entities: GeoAnalysisEntityContext


class GeoEntityMentionFact(ContractModel):
    """單一 tracked entity 在回答中的 mention 與相對排序事實。"""

    entity_id: UUID
    entity_role: Literal["own_brand", "competitor"]
    entity_name: str
    mentioned: bool
    first_mention_order: int | None = Field(default=None, ge=1)
    evidence_text: str | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)

    @model_validator(mode="after")
    def validate_position(self):
        if not self.mentioned:
            if self.first_mention_order is not None:
                raise ValueError("firstMentionOrder must be empty when mentioned is false")
            if self.evidence_text is not None:
                raise ValueError("evidenceText must be empty when mentioned is false")
        return self


class GeoSentimentFact(ContractModel):
    """品牌或競品相關的 statement-level positive / negative sentiment。"""

    entity_id: UUID
    entity_role: Literal["own_brand", "competitor"]
    entity_name: str
    sentiment: Literal["positive", "negative"]
    theme: str
    statement: str
    evidence_text: str | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)


class GeoResponseSemanticFact(ContractModel):
    """回答細節與後續建議模組可使用的 semantic label 或常見陳述。"""

    fact_type: Literal["product", "service", "topic", "common_statement"]
    value: str
    evidence_text: str | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)


class GeoRunResultAnalysis(ContractModel):
    """Semantic analyzer 對單筆 run result 回傳的 normalized facts。"""

    run_result_id: UUID
    analyzer: str
    analyzer_version: str | None = None
    status: Literal["completed", "failed"]
    entity_mentions: list[GeoEntityMentionFact] = Field(default_factory=list)
    sentiments: list[GeoSentimentFact] = Field(default_factory=list)
    semantic_facts: list[GeoResponseSemanticFact] = Field(default_factory=list)
    error_code: str | None = None
    error_message: str | None = None


class SaveSemanticRunResultAnalysisCommand(ContractModel):
    """保存 semantic analyzer facts 時使用的 persistence input。"""

    analysis: GeoRunResultAnalysis
    task_key: str = "geo_semantic_analysis"
    schema_version: int = 1


class KMindHubExtractionTaskField(ContractModel):
    """定義 KMindHub extraction task 欄位，以及 GEO 端會再次驗證的正規化規則。"""

    name: str
    field_type: str = "string"
    lookup_role: str = "ignored"
    display_name: str
    description: str
    normalization: dict = Field(default_factory=dict)
    examples: str = ""
    sort_order: int = 0
    is_visible: bool = True
    is_extracted: bool = True


class KMindHubExtractionTaskDefinition(ContractModel):
    """GEO 系統版本化管理的 KMindHub extraction task schema。"""

    task_key: str
    schema_version: int
    name: str
    task: str
    description: str
    fields: list[KMindHubExtractionTaskField]
    status: str = "active"


class KMindHubExtractionTaskMappingCommand(ContractModel):
    """保存 tenant 在特定 schema version 對應的 KMindHub extraction task。"""

    workspace_id: UUID
    task_key: str
    schema_version: int
    kmindhub_task_id: UUID
    status: str = "active"


class KMindHubExtractionTaskMappingRecord(KMindHubExtractionTaskMappingCommand):
    """已建立且可被 worker 重用的 KMindHub extraction task mapping。"""

    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime


class KMindHubExtractionFieldValue(ContractModel):
    """KMindHub preview / commit item 中單一欄位的值與 evidence。"""

    value: object | None = None
    evidence: list = Field(default_factory=list)


class KMindHubExtractionPreviewItem(ContractModel):
    """KMindHub preview 產出的暫存 item；通過驗證後才可 commit。"""

    fields: dict[str, KMindHubExtractionFieldValue] = Field(default_factory=dict)
    verification: dict = Field(default_factory=dict)
    display_fields: list = Field(default_factory=list)
    candidates: list = Field(default_factory=list)


class KMindHubExtractionPreviewResult(ContractModel):
    """KMindHub extraction preview response 的 application read model。"""

    task_id: UUID
    items: list[KMindHubExtractionPreviewItem] = Field(default_factory=list)


class KMindHubExtractionCommitResult(ContractModel):
    """KMindHub commit 後回傳的批次與 item ids。"""

    commit_batch_id: str | None = None
    item_ids: list[str] = Field(default_factory=list)


class GeoRunResultEntityMentionCommand(ContractModel):
    """從 AI answer 擷取出的單一品牌、競品或其他 entity mention。"""

    entity_id: UUID | None = None
    entity_name: str
    entity_type: str
    mention_count: int = 0
    sentiment: str
    evidence_text: str = ""
    kmindhub_item_id: str | None = None


class GeoRunResultStatementCommand(ContractModel):
    """從 AI answer 擷取出的可供報表或人工檢視的重要陳述。"""

    statement_text: str
    theme: str = ""
    sentiment: str
    subject_entity_name: str | None = None
    evidence_text: str = ""
    kmindhub_item_id: str | None = None


class GeoRunResultCitationClassificationCommand(ContractModel):
    """根據既有 reference URL 判斷 citation 類型，不讓 KMindHub 重新產生 URL。"""

    run_result_reference_id: UUID
    classification: str
    matched_entity_id: UUID | None = None
    matched_domain: str | None = None
    confidence: float | None = None
    source: str = "rule_based"


class SaveRunResultAnalysisCommand(ContractModel):
    """保存單筆 run result 的 KMindHub analysis 狀態與正規化結果。"""

    run_result_id: UUID
    task_key: str = "geo_answer_analysis"
    schema_version: int = 1
    status: str
    summary: str | None = None
    overall_sentiment: str | None = None
    theme: str | None = None
    kmindhub_commit_batch_id: str | None = None
    kmindhub_item_id: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    entity_mentions: list[GeoRunResultEntityMentionCommand] = Field(default_factory=list)
    statements: list[GeoRunResultStatementCommand] = Field(default_factory=list)
    citation_classifications: list[GeoRunResultCitationClassificationCommand] = Field(
        default_factory=list
    )


class GeoRunResultAnalysisRecord(ContractModel):
    """GEO run result 已完成或失敗的 KMindHub analysis 狀態。"""

    id: UUID
    run_result_id: UUID
    task_key: str
    schema_version: int
    status: str
    summary: str | None = None
    overall_sentiment: str | None = None
    theme: str | None = None
    kmindhub_commit_batch_id: str | None = None
    kmindhub_item_id: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None


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


class KMindHubWorkspaceMappingCommand(ContractModel):
    """租戶綁定 KMindHub workspace 時使用的 application input。"""

    workspace_id: UUID
    display_name: str
    provisioning_mode: str = "manual"
    status: str = "active"


class KMindHubWorkspaceMappingRecord(KMindHubWorkspaceMappingCommand):
    """GEO Analysis 保存的 tenant 到 KMindHub workspace 對應快照。"""

    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime


class KMindHubWorkspaceProvisionCommand(ContractModel):
    """由使用者明確觸發建立 KMindHub workspace 的 input。"""

    display_name: str


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
