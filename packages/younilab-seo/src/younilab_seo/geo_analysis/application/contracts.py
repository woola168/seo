from datetime import date, datetime
from typing import Literal
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def _camel_case(value: str) -> str:
    head, *tail = value.split("_")
    return head + "".join(part.capitalize() for part in tail)


def _is_timezone_aware(value: datetime) -> bool:
    return value.tzinfo is not None and value.tzinfo.utcoffset(value) is not None


class ContractModel(BaseModel):
    """GEO application 邊界使用的 camelCase contract 基底。"""

    model_config = ConfigDict(alias_generator=_camel_case, populate_by_name=True)


class QueryRunJobMessage(ContractModel):
    """發布到 provider queue 的 GEO query run job message。"""

    job_id: UUID
    tenant_id: UUID
    project_id: UUID
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
        if any(
            competitor.entity_role != "competitor" for competitor in self.competitors
        ):
            raise ValueError("competitor entityRole must be competitor")
        return self


class AnalyzeGeoRunResultCommand(ContractModel):
    """送入 semantic analyzer 的完整 run result 與專案上下文。"""

    tenant_id: UUID
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


class EvidenceTextRepairFailure(ContractModel):
    """單一 preview item 中無法逐字回溯的 evidence。"""

    item_index: int = Field(ge=0)
    wrong_evidence_text: str = Field(min_length=1)


class EvidenceTextRepairCommand(ContractModel):
    """要求 repair adapter 將失敗 evidence 對回 raw response 原文。"""

    raw_response: str = Field(min_length=1)
    failures: list[EvidenceTextRepairFailure] = Field(min_length=1)


class EvidenceTextRepair(ContractModel):
    """單一失敗 evidence 的 focused repair 結果。"""

    item_index: int = Field(ge=0)
    evidence_text: str | None = None


class EvidenceTextRepairResult(ContractModel):
    """與 repair command failures 順序一致的修復結果。"""

    repairs: list[EvidenceTextRepair] = Field(default_factory=list)


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
                raise ValueError(
                    "firstMentionOrder must be empty when mentioned is false"
                )
            if self.evidence_text is not None:
                raise ValueError("evidenceText must be empty when mentioned is false")
        return self


class GeoEntityMentionDetectionItem(ContractModel):
    """Deterministic mention with the canonical or alias match that produced it."""

    entity_id: UUID
    entity_role: Literal["own_brand", "competitor"]
    entity_name: str
    mentioned: bool
    first_mention_order: int | None = Field(default=None, ge=1)
    evidence_text: str | None = None
    matched_by: Literal["canonical", "alias"] | None = None
    matched_value: str | None = None
    match_type: (
        Literal["canonical", "exact", "case_insensitive", "contains"] | None
    ) = None

    @model_validator(mode="after")
    def validate_match(self):
        if self.mentioned and (
            self.first_mention_order is None or self.evidence_text is None
        ):
            raise ValueError(
                "mentioned detection items must include order and evidence"
            )
        if not self.mentioned:
            if self.first_mention_order is not None:
                raise ValueError(
                    "firstMentionOrder must be empty when mentioned is false"
                )
            if self.evidence_text is not None:
                raise ValueError("evidenceText must be empty when mentioned is false")
        match_values = (self.matched_by, self.matched_value, self.match_type)
        if self.mentioned and any(value is None for value in match_values):
            raise ValueError("mentioned detection items must include match metadata")
        if not self.mentioned and any(value is not None for value in match_values):
            raise ValueError("unmentioned detection items must not include match metadata")
        return self


class GeoRunResultEntityDetection(ContractModel):
    """Versioned entity-mention result independent of semantic extraction."""

    run_result_id: UUID
    detector_version: str = "explicit_alias:v1"
    status: Literal["completed", "failed"]
    items: list[GeoEntityMentionDetectionItem] = Field(default_factory=list)
    error_code: str | None = None
    error_message: str | None = None

    @model_validator(mode="after")
    def validate_status(self):
        if self.status == "failed" and self.items:
            raise ValueError("failed detection must not contain items")
        return self


class SaveRunResultEntityDetectionCommand(ContractModel):
    """Persistence input for one version of deterministic entity mention detection."""

    detection: GeoRunResultEntityDetection


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
    analyzer_request_payload: dict | None = None
    analyzer_response_payload: dict | None = None
    validation_failures: list[dict] = Field(default_factory=list)


class SaveSemanticRunResultAnalysisCommand(ContractModel):
    """保存 semantic analyzer facts 時使用的 persistence input。"""

    analysis: GeoRunResultAnalysis
    task_key: str = "geo_semantic_analysis"
    schema_version: int = 1


class NormalizeRunResultCitationsCommand(ContractModel):
    """將已保存 runner references 轉成報表 citation facts 的 application input。"""

    tenant_id: UUID
    run_result_id: UUID
    normalizer_version: str = "url_domain:v2"


class GeoRunResultCitationFact(ContractModel):
    """單一 runner reference 的 deterministic citation fact。"""

    run_result_id: UUID
    reference_id: UUID
    url: str
    domain: str
    title: str | None = None
    position: int
    ownership: Literal["owned", "other"]
    source_type: Literal["owned_site", "unknown"]


class GeoRunResultCitationNormalization(ContractModel):
    """單筆 run result citation normalization 的 application result。"""

    run_result_id: UUID
    project_id: UUID | None = None
    normalizer_version: str = "url_domain:v2"
    status: Literal["completed", "failed"]
    citations: list[GeoRunResultCitationFact] = Field(default_factory=list)
    skipped_reference_count: int = Field(default=0, ge=0)
    error_code: str | None = None
    error_message: str | None = None


class SaveRunResultCitationNormalizationCommand(ContractModel):
    """保存 citation normalization lifecycle 與 facts 時使用的 persistence input。"""

    normalization: GeoRunResultCitationNormalization


class GeoMetricRunResultInput(ContractModel):
    """報表公式計算使用的 completed run result metadata。"""

    run_result_id: UUID
    query_id: UUID | None = None
    topic_id: UUID | None = None
    provider: str | None = None
    region: str | None = None
    language: str | None = None
    completed_at: datetime

    @model_validator(mode="after")
    def validate_completed_at_timezone(self):
        if not _is_timezone_aware(self.completed_at):
            raise ValueError("completedAt must be timezone-aware")
        return self


class GeoMetricFormulaQuery(ContractModel):
    """限制報表公式計算期間與可選維度的 in-memory query。"""

    period_start: datetime
    period_end: datetime
    comparison_start: datetime | None = None
    comparison_end: datetime | None = None
    query_id: UUID | None = None
    topic_id: UUID | None = None
    provider: str | None = None
    region: str | None = None
    language: str | None = None

    @model_validator(mode="after")
    def validate_periods(self):
        period_values = [self.period_start, self.period_end]
        if self.comparison_start is not None:
            period_values.append(self.comparison_start)
        if self.comparison_end is not None:
            period_values.append(self.comparison_end)
        if any(not _is_timezone_aware(value) for value in period_values):
            raise ValueError("metric formula periods must be timezone-aware")
        if self.period_end <= self.period_start:
            raise ValueError("periodEnd must be later than periodStart")
        if (self.comparison_start is None) != (self.comparison_end is None):
            raise ValueError(
                "comparisonStart and comparisonEnd must be provided together"
            )
        if (
            self.comparison_start is not None
            and self.comparison_end is not None
            and self.comparison_end <= self.comparison_start
        ):
            raise ValueError("comparisonEnd must be later than comparisonStart")
        if self.comparison_end is not None and self.comparison_end > self.period_start:
            raise ValueError("comparisonEnd must not be later than periodStart")
        return self


class GeoMetricEntityMentionInput(GeoEntityMentionFact):
    """報表公式計算使用、已帶入 run result identity 的 entity mention fact。"""

    run_result_id: UUID


class GeoMetricSentimentInput(GeoSentimentFact):
    """報表公式計算使用、已帶入 run result identity 的 sentiment fact。"""

    run_result_id: UUID


class GeoMetricFormulaSource(ContractModel):
    """已正規化 facts 與 run result metadata 的純公式輸入。"""

    run_results: list[GeoMetricRunResultInput] = Field(default_factory=list)
    entity_mentions: list[GeoMetricEntityMentionInput] = Field(default_factory=list)
    sentiments: list[GeoMetricSentimentInput] = Field(default_factory=list)
    citations: list[GeoRunResultCitationFact] = Field(default_factory=list)


class GeoMetricValue(ContractModel):
    """單一報表 metric 的可呈現計算結果。"""

    metric_name: Literal[
        "visibility",
        "mentions",
        "sov",
        "average_position",
        "citation_count",
        "used_percent",
        "share_percent",
        "sentiment_count",
    ]
    scope_type: Literal[
        "project",
        "entity",
        "citation_url",
        "citation_domain",
        "sentiment",
    ]
    scope_value: str | None = None
    scope_label: str | None = None
    value: float
    unit: Literal["percent", "count", "position"]
    numerator: float | None = None
    denominator: float | None = None
    comparison_value: float | None = None
    delta: float | None = None
    delta_unit: Literal["pp", "count", "position"] | None = None


class GeoMetricFormulaResult(ContractModel):
    """報表公式核心針對目前期間與前期比較產生的 metrics。"""

    period_start: datetime
    period_end: datetime
    comparison_start: datetime
    comparison_end: datetime
    metrics: list[GeoMetricValue] = Field(default_factory=list)


class GeoDashboardMetricValue(ContractModel):
    """Dashboard read model 中可直接呈現的單一 metric value。"""

    value: float
    unit: Literal["percent", "count", "position"]
    numerator: float | None = None
    denominator: float | None = None
    comparison_value: float | None = None
    delta: float | None = None
    delta_unit: Literal["pp", "count", "position"] | None = None


class GeoDashboardOverviewCard(ContractModel):
    """Dashboard overview 區塊的一張 KPI card。"""

    metric_name: Literal["visibility", "mentions", "sov", "average_position"]
    label: str
    metric: GeoDashboardMetricValue


class GeoDashboardEntityRow(ContractModel):
    """Dashboard entity comparison table 的一列。"""

    entity_id: UUID
    entity_role: Literal["own_brand", "competitor"]
    entity_name: str
    visibility: GeoDashboardMetricValue
    mentions: GeoDashboardMetricValue
    average_position: GeoDashboardMetricValue


class GeoDashboardCitationRow(ContractModel):
    """Dashboard citation table 的 URL 或 domain grouping row。"""

    scope_type: Literal["url", "domain"]
    value: str
    label: str
    ownership: str | None = None
    source_type: str | None = None
    citation_count: GeoDashboardMetricValue
    used_percent: GeoDashboardMetricValue
    share_percent: GeoDashboardMetricValue


class GeoDashboardSentimentRow(ContractModel):
    """Dashboard sentiment breakdown 的 positive / negative row。"""

    sentiment: Literal["positive", "negative"]
    statement_count: GeoDashboardMetricValue


class GeoDashboardReport(ContractModel):
    """Dashboard 頁面可直接使用的 request-time report view model。"""

    period_start: datetime
    period_end: datetime
    comparison_start: datetime
    comparison_end: datetime
    overview: list[GeoDashboardOverviewCard] = Field(default_factory=list)
    entities: list[GeoDashboardEntityRow] = Field(default_factory=list)
    citation_urls: list[GeoDashboardCitationRow] = Field(default_factory=list)
    citation_domains: list[GeoDashboardCitationRow] = Field(default_factory=list)
    sentiments: list[GeoDashboardSentimentRow] = Field(default_factory=list)


class GeoOverviewQuery(ContractModel):
    """限制 Overview 報表期間、時區與使用者選取的查詢維度。"""

    period_start: datetime
    period_end: datetime
    topic_ids: list[UUID] = Field(default_factory=list)
    providers: list[str] = Field(default_factory=list)
    region: str | None = None
    metadata_industry: list[str] = Field(default_factory=list)
    metadata_type: list[str] = Field(default_factory=list)
    time_zone: str = "Asia/Taipei"

    @model_validator(mode="after")
    def validate_overview_query(self):
        if not _is_timezone_aware(self.period_start) or not _is_timezone_aware(
            self.period_end
        ):
            raise ValueError("overview periods must be timezone-aware")
        if self.period_end <= self.period_start:
            raise ValueError("periodEnd must be later than periodStart")
        try:
            ZoneInfo(self.time_zone)
        except ZoneInfoNotFoundError as exc:
            if self.time_zone == "Asia/Taipei":
                return self
            raise ValueError("timeZone must be a valid IANA time zone") from exc
        return self


class GeoOverviewFilterOption(ContractModel):
    value: str
    label: str


class GeoOverviewFilterOptions(ContractModel):
    topics: list[GeoOverviewFilterOption] = Field(default_factory=list)
    platforms: list[GeoOverviewFilterOption] = Field(default_factory=list)
    regions: list[str] = Field(default_factory=list)
    metadata_industries: list[str] = Field(default_factory=list)
    metadata_types: list[str] = Field(default_factory=list)


class GeoOverviewKpi(ContractModel):
    metric_name: Literal["mentions", "average_position", "visibility", "sov"]
    value: float
    unit: Literal["count", "position", "percent"]
    numerator: float | None = None
    denominator: float | None = None
    secondary_label: str
    secondary_value: float | None = None
    secondary_unit: Literal["count", "position", "percent"] | None = None
    delta: float | None = None
    delta_unit: Literal["pp", "count", "position"] | None = None


class GeoOverviewCitationSummary(ContractModel):
    owned_share_percent: float
    citation_count: int
    cited_page_count: int
    cited_response_percent: float


class GeoOverviewTrendPoint(ContractModel):
    date: str
    value: float


class GeoOverviewVisibilitySeries(ContractModel):
    entity_id: UUID
    entity_name: str
    entity_role: Literal["own_brand", "competitor"]
    points: list[GeoOverviewTrendPoint] = Field(default_factory=list)


class GeoOverviewSentimentPoint(ContractModel):
    date: str
    positive_count: int
    negative_count: int
    positive_negative_ratio: float | None = None


class GeoOverviewEntityRow(ContractModel):
    entity_id: UUID
    entity_name: str
    entity_role: Literal["own_brand", "competitor"]
    visibility_percent: float
    visibility_delta_pp: float | None = None
    sov_percent: float
    average_position: float


class GeoOverviewQueryRow(ContractModel):
    query_id: UUID
    query_text: str
    visibility_percent: float
    sov_percent: float
    citation_count: int


class GeoOverviewTopicRow(ContractModel):
    topic_id: UUID | None = None
    topic_name: str
    visibility_percent: float
    sov_percent: float
    citation_count: int
    queries: list[GeoOverviewQueryRow] = Field(default_factory=list)


class GeoOverviewCitationRow(ContractModel):
    scope_type: Literal["url", "domain"]
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


class GeoOverviewReport(ContractModel):
    period_start: datetime
    period_end: datetime
    comparison_start: datetime
    comparison_end: datetime
    is_preparing: bool
    filter_options: GeoOverviewFilterOptions
    overview: list[GeoOverviewKpi] = Field(default_factory=list)
    citation_summary: GeoOverviewCitationSummary
    visibility_trend: list[GeoOverviewVisibilitySeries] = Field(default_factory=list)
    sentiment_trend: list[GeoOverviewSentimentPoint] = Field(default_factory=list)
    entities: list[GeoOverviewEntityRow] = Field(default_factory=list)
    topics: list[GeoOverviewTopicRow] = Field(default_factory=list)
    citation_urls: list[GeoOverviewCitationRow] = Field(default_factory=list)
    citation_domains: list[GeoOverviewCitationRow] = Field(default_factory=list)


class GeoOverviewResponseRow(ContractModel):
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


class GeoOverviewResponsePage(ContractModel):
    items: list[GeoOverviewResponseRow] = Field(default_factory=list)
    total: int
    page: int
    page_size: int


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
    request_payload: dict | None = None
    response_payload: dict | None = None


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
    entity_mentions: list[GeoRunResultEntityMentionCommand] = Field(
        default_factory=list
    )
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


class GeoProjectStatusCommand(ContractModel):
    """切換 Project 是否參與後續排程。"""

    status: Literal["active", "paused"]


class GeoProjectOwnBrandSummary(ContractModel):
    """Project 列表顯示所需的自有品牌摘要。"""

    entity_id: UUID
    website_url: str | None = None
    aliases: list[str] = Field(default_factory=list)


class GeoProjectSummaryRecord(GeoProjectRecord):
    """Project 列表使用的跨資源 read model。"""

    customer_name: str | None = None
    own_brand: GeoProjectOwnBrandSummary | None = None


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
    """描述 tracked entity alias 集合中的單一項目。"""

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


class GeoProjectQuerySettingsAudience(ContractModel):
    """Project Query 預設設定中的目標受眾。"""

    name: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=2000)

    @field_validator("name", "description")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("value must not be empty")
        return normalized


class GeoProjectQuerySettingsIntent(ContractModel):
    """Project Query 預設設定中的主要搜尋意圖。"""

    category: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=1, max_length=2000)

    @field_validator("category", "description")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("value must not be empty")
        return normalized


class GeoProjectQuerySettingsCommand(ContractModel):
    """完整替換一個 Project 的 Query Research 與 Generation 預設值。"""

    research_provider: Literal["gemini"]
    run_provider: Literal["gemini"]
    keywords: list[str] = Field(default_factory=list, max_length=10)
    market_type: Literal["b2c", "b2b_procurement"]
    max_queries: int = Field(ge=1, le=40)
    audience: GeoProjectQuerySettingsAudience
    intent: GeoProjectQuerySettingsIntent
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
            if not keyword:
                continue
            if len(keyword) > 200:
                raise ValueError("keyword must contain at most 200 characters")
            key = keyword.casefold()
            if key not in seen:
                seen.add(key)
                normalized.append(keyword)
        return normalized


class GeoProjectQuerySettingsRecord(GeoProjectQuerySettingsCommand):
    """已保存的 Project Query 預設設定。"""

    project_id: UUID
    created_at: datetime
    updated_at: datetime


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
    status: str = "active"


class GeoQueryPlatformRecord(GeoQueryPlatformCommand):
    """已保存的 query platform assignment 記錄。"""

    id: UUID
    query_id: UUID
    created_at: datetime
    updated_at: datetime


class GeoAiPlatformRecord(ContractModel):
    """可供排程與管理介面判斷是否啟用的 GEO AI Platform。"""

    id: UUID
    code: str
    display_name: str
    provider_type: str
    default_model: str | None = None
    status: str


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


class DailyRunMaterializationResult(ContractModel):
    """單一營業日排程工作經冪等展開後的結果。"""

    business_date: date
    scheduled_for: datetime
    batch_count: int
    job_count: int
    budget_enforced: bool = False


class DailySchedulerTickResult(ContractModel):
    """Scheduler 完成一次輪詢後的可觀測結果。"""

    due: bool
    business_date: date
    materialized_batches: int = 0
    materialized_jobs: int = 0
    dispatched_jobs: int = 0
    reconciled_jobs: int = 0
    budget_enforced: bool = False
