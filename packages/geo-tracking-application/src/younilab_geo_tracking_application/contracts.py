import ipaddress
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, field_validator
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
    intents: list[QueryIntent] = Field(default_factory=list, max_length=8)
    audience: QueryAudience | None = None
    brand_mention_rules: BrandMentionRules = Field(default_factory=BrandMentionRules)

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


ProjectType = Literal[
    "company",
    "brand",
    "product",
    "service",
    "repository",
    "other",
]


class ProjectInspectionCommand(ContractModel):
    project_url: AnyHttpUrl
    language: str = Field(min_length=1, max_length=20)

    @field_validator("project_url")
    @classmethod
    def validate_public_project_url(cls, value: AnyHttpUrl) -> AnyHttpUrl:
        return _validate_public_project_url(value)


class ConfirmedProjectIdentity(ContractModel):
    model_config = ConfigDict(extra="forbid")

    source_url: AnyHttpUrl
    retrieved_url: AnyHttpUrl
    project_name: str = Field(min_length=1, max_length=200)
    project_description: str = Field(min_length=1, max_length=1000)
    project_type: ProjectType
    core_offerings: list[str] = Field(min_length=1, max_length=8)

    @field_validator("source_url", "retrieved_url")
    @classmethod
    def validate_public_project_urls(cls, value: AnyHttpUrl) -> AnyHttpUrl:
        return _validate_public_project_url(value)


class ProjectSuggestionCommand(ContractModel):
    model_config = ConfigDict(extra="forbid")

    confirmed_project: ConfirmedProjectIdentity
    region: RegionCode
    language: str = Field(min_length=1, max_length=20)
    market_type: MarketType
    competitor_count: int = Field(default=5, ge=1, le=8)
    topic_count: int = Field(default=5, ge=1, le=8)
    keyword_count: int = Field(default=5, ge=1, le=10)


def _validate_public_project_url(value: AnyHttpUrl) -> AnyHttpUrl:
    host = (value.host or "").lower().rstrip(".")
    if (
        value.username
        or value.password
        or host == "localhost"
        or host.endswith(".localhost")
        or host.endswith(".local")
    ):
        raise ValueError("project_url must be a public URL")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return value
    if not address.is_global:
        raise ValueError("project_url must be a public URL")
    return value


class ProjectDiscoveryIdentity(ContractModel):
    project_name: str = Field(max_length=200)
    project_description: str = Field(max_length=1000)
    project_type: ProjectType
    core_offerings: list[str] = Field(default_factory=list, max_length=8)
    sufficient_context: bool
    limitation: str = Field(default="", max_length=1000)


class VerifiedProjectIdentity(ContractModel):
    model_config = ConfigDict(frozen=True)

    source_url: AnyHttpUrl
    retrieved_url: AnyHttpUrl
    project_name: str
    project_description: str
    project_type: ProjectType
    core_offerings: tuple[str, ...]


class ProjectDiscoveryInspection(ContractModel):
    retrieval_succeeded: bool
    retrieved_url: AnyHttpUrl | None
    identity: ProjectDiscoveryIdentity | None


class ProjectInspectionResult(ContractModel):
    source_url: AnyHttpUrl
    retrieved_url: AnyHttpUrl
    project_name: str
    project_description: str
    project_type: ProjectType
    core_offerings: list[str]


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


class ProjectSuggestionResult(ContractModel):
    search_succeeded: bool
    competitors: list[str] = Field(default_factory=list, max_length=8)
    topics: list[TopicInput] = Field(default_factory=list, max_length=8)
    keywords: list[str] = Field(default_factory=list, max_length=10)
    references: list[Reference] = Field(default_factory=list)


class ProjectSuggestionsResult(ContractModel):
    competitors: list[str]
    topics: list[TopicInput]
    keywords: list[str]
    references: list[Reference]


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
    timing: RunTiming
    results: list[RunResult]
