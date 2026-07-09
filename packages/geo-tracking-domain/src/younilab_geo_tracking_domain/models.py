from dataclasses import dataclass, field
from enum import StrEnum
from uuid import UUID


class RegionCode(StrEnum):
    TAIWAN = "TW"
    UNITED_STATES = "US"


class MarketType(StrEnum):
    B2C = "b2c"
    B2B_PROCUREMENT = "b2b_procurement"


class QuerySource(StrEnum):
    RESEARCH = "research"
    MANUAL = "manual"
    DUMMY = "dummy"


class QueryStatus(StrEnum):
    ACTIVE = "active"
    PAUSED = "paused"


class RunTiming(StrEnum):
    RUN_NOW = "run_now"
    NEXT_CYCLE = "next_cycle"


class ProviderCode(StrEnum):
    DUMMY = "dummy"
    GEMINI = "gemini"
    GOOGLE_AIO = "google_aio"


class RunResultStatus(StrEnum):
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True)
class Topic:
    id: UUID
    name: str


@dataclass(frozen=True)
class TrackedQuery:
    id: UUID
    seo_task_id: UUID | None
    text: str
    topic_id: UUID | None
    topic_name: str
    region: RegionCode
    language: str
    market_type: MarketType
    is_branded: bool
    metadata: dict[str, str] = field(default_factory=dict)
    source: QuerySource = QuerySource.RESEARCH
    status: QueryStatus = QueryStatus.ACTIVE
