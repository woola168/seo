from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CamelModel(BaseModel):
    """將 snake_case 欄位以 camelCase JSON 呈現的 schema 基底。"""

    model_config = ConfigDict(alias_generator=lambda value: _camel_case(value), populate_by_name=True)


def _camel_case(value: str) -> str:
    head, *tail = value.split("_")
    return head + "".join(part.capitalize() for part in tail)


class AuthorizationResourceType(StrEnum):
    CUSTOMER = "customer"
    TASK = "task"


class AuthorizationResource(CamelModel):
    """authorization service 檢查的受保護 resource。"""

    type: AuthorizationResourceType
    id: UUID
    customer_id: UUID | None = None


class AuthorizationRequest(CamelModel):
    """判斷單一使用者是否可執行某 permission 的 request。"""

    user_id: UUID
    permission: str = Field(min_length=1)
    resource: AuthorizationResource | None = None


class AuthorizationDecision(CamelModel):
    """authorization check 的 allow/deny 結果與穩定 reason code。"""

    allowed: bool
    reason_code: str


class BatchAuthorizationRequest(CamelModel):
    """一組有數量上限且會獨立評估的 authorization requests。"""

    requests: list[AuthorizationRequest] = Field(min_length=1, max_length=100)


class BatchAuthorizationDecision(CamelModel):
    """依 batch request 相同順序回傳的 authorization decisions。"""

    decisions: list[AuthorizationDecision]
