from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


def _camel_case(value: str) -> str:
    head, *tail = value.split("_")
    return head + "".join(part.capitalize() for part in tail)


class ContractModel(BaseModel):
    """GEO application boundary 使用的 camelCase contract base。"""

    model_config = ConfigDict(alias_generator=_camel_case, populate_by_name=True)


class QueryRunJobMessage(ContractModel):
    """準備送往 message broker 的 query run job message。"""

    job_id: UUID
    project_id: UUID
    query_id: UUID
    query_text: str
    platform: str
    model: str | None = None
    region: str
    language: str
    scheduled_for: datetime
    callback_url: str


class PublishResult(ContractModel):
    """message publisher 回報的派送結果。"""

    backend: str
    destination: str
    message_id: str | None = None
    status: str
    error_message: str | None = None


class ExternalRunCallback(ContractModel):
    """外部 runner 回傳的 job 狀態 callback，不承載 AI result content。"""

    job_id: UUID
    external_run_id: str
    status: str
    result_location: str | None = None
    error_code: str | None = None
    error_message: str | None = None


class GeoProjectCommand(ContractModel):
    """建立或更新 GEO project 的 application input。"""

    customer_id: UUID
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


class GeoQueryPlatformCommand(ContractModel):
    """建立或替換 tracked query platform assignment 的 application input。"""

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
    """替 tracked query 建立 query run job 的 application input。"""

    platform_id: UUID
    scheduled_for: datetime | None = None
    priority: str = "normal"
    job_type: str = "manual_run"
