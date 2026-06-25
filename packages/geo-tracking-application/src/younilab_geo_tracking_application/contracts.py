from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator
from younilab_geo_tracking_domain import (
    MarketType,
    ProviderCode,
    QuerySource,
    QueryStatus,
    RegionCode,
    RunResultStatus,
    RunTiming,
)


def _camel_case(value: str) -> str:
    head, *tail = value.split("_")
    return head + "".join(part.capitalize() for part in tail)


class ContractModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=_camel_case,
        populate_by_name=True,
    )


class TopicSummary(ContractModel):
    id: UUID
    name: str
    description: str = ""


class TopicInput(ContractModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=1000)


class QueryIntent(ContractModel):
    category: str
    description: str


class QueryAudience(ContractModel):
    name: str
    description: str


class BrandMentionRules(ContractModel):
    should_mention_own_brand: bool = True
    should_mention_competitor: bool = False


class QueryGenerationAttributes(ContractModel):
    intent: QueryIntent
    keyword: str
    topic_name: str
    topic_description: str = ""
    audience: QueryAudience
    brand_mention_rules: BrandMentionRules


class QueryDraft(ContractModel):
    attributes: QueryGenerationAttributes
    query: str = Field(min_length=1, max_length=500)
    keywords: list[str] = Field(default_factory=list, max_length=10)


class QueryDraftList(ContractModel):
    items: list[QueryDraft] = Field(min_length=1, max_length=40)


class GeneratedQuery(ContractModel):
    id: UUID
    seo_task_id: UUID
    text: str
    keywords: list[str] = Field(default_factory=list, max_length=10)
    topic_id: UUID | None
    topic_name: str
    region: RegionCode
    language: str
    market_type: MarketType
    is_branded: bool
    attributes: QueryGenerationAttributes
    metadata: dict[str, str]
    source: QuerySource
    status: QueryStatus


class QueryGenerationCommand(ContractModel):
    seo_task_id: UUID
    provider: ProviderCode = ProviderCode.DUMMY
    brand_name: str = Field(min_length=1, max_length=200)
    competitor_brands: list[str] = Field(default_factory=list, max_length=8)
    keywords: list[str] = Field(min_length=1, max_length=10)
    region: RegionCode
    language: str | None = Field(default=None, max_length=20)
    market_type: MarketType
    topics: list[TopicInput] = Field(default_factory=list, max_length=8)
    topic_names: list[str] = Field(default_factory=list, max_length=8)
    intents: list[QueryIntent] = Field(min_length=1, max_length=8)
    audience: QueryAudience
    brand_mention_rules: BrandMentionRules = Field(default_factory=BrandMentionRules)
    research_context: str | None = Field(default=None, max_length=5000)
    max_queries: int = Field(default=12, ge=1, le=40)

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, provider: ProviderCode) -> ProviderCode:
        if provider == ProviderCode.GOOGLE_AIO:
            raise ValueError("google_aio is only supported by run requests")
        return provider


class QueryGenerationResult(ContractModel):
    topics: list[TopicSummary]
    queries: list[GeneratedQuery]


class QueryResearchCommand(ContractModel):
    provider: ProviderCode = ProviderCode.DUMMY
    brand_name: str = Field(min_length=1, max_length=200)
    competitor_brands: list[str] = Field(default_factory=list, max_length=8)
    keywords: list[str] = Field(min_length=1, max_length=10)
    region: RegionCode
    language: str | None = Field(default=None, max_length=20)
    market_type: MarketType
    audience: QueryAudience | None = None

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, provider: ProviderCode) -> ProviderCode:
        if provider == ProviderCode.GOOGLE_AIO:
            raise ValueError("google_aio is only supported by run requests")
        return provider


class QueryResearchResult(ContractModel):
    research_context: str
    searched_keywords: list[str] = Field(default_factory=list)
    source_urls: list[str] = Field(default_factory=list)


class RunQueryInput(ContractModel):
    id: UUID
    text: str
    topic_name: str
    region: RegionCode
    language: str
    market_type: MarketType
    is_branded: bool
    metadata: dict[str, str] = Field(default_factory=dict)


class RunRequestCommand(ContractModel):
    seo_task_id: UUID
    queries: list[RunQueryInput] = Field(min_length=1, max_length=20)
    provider: ProviderCode = ProviderCode.DUMMY
    timing: RunTiming = RunTiming.RUN_NOW


class AnswerRequest(ContractModel):
    query_id: UUID
    query_text: str
    region: RegionCode
    language: str
    market_type: MarketType
    is_branded: bool
    system_prompt: str


class Reference(ContractModel):
    url: str
    title: str | None = None


class AnswerResponse(ContractModel):
    provider: ProviderCode
    surface: str
    model: str
    raw_response: str
    reference_urls: list[str] = Field(default_factory=list)
    references: list[Reference] = Field(default_factory=list)


class RunResult(ContractModel):
    id: UUID
    run_request_id: UUID
    query_id: UUID
    provider: ProviderCode
    surface: str
    model: str
    region: RegionCode
    language: str
    status: RunResultStatus
    raw_response: str
    reference_urls: list[str]
    references: list[Reference]
    error: str | None
    run_at: datetime


class RunRequestResult(ContractModel):
    id: UUID
    seo_task_id: UUID
    timing: RunTiming
    results: list[RunResult]
