from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


def _camel_case(value: str) -> str:
    head, *tail = value.split("_")
    return head + "".join(part.capitalize() for part in tail)


class ContractModel(BaseModel):
    """跨邊界暴露的穩定 GEO orchestration contract 基底模型。"""

    model_config = ConfigDict(alias_generator=_camel_case, populate_by_name=True)


class QueryRunJobMessage(ContractModel):
    """交給選定 broker，供外部 AI runner 消費的 job message。"""

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
    """嘗試發布 job message 後回傳的 broker 中立結果。"""

    backend: str
    destination: str
    message_id: str | None = None
    status: str
    error_message: str | None = None


class ExternalRunCallback(ContractModel):
    """外部 runner 回報狀態用的 callback，不包含 AI response 內容。"""

    job_id: UUID
    external_run_id: str
    status: str
    result_location: str | None = None
    error_code: str | None = None
    error_message: str | None = None
