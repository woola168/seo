from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=lambda value: _camel_case(value), populate_by_name=True)


def _camel_case(value: str) -> str:
    head, *tail = value.split("_")
    return head + "".join(part.capitalize() for part in tail)


class AuthorizationResourceType(StrEnum):
    CUSTOMER = "customer"
    TASK = "task"


class AuthorizationResource(CamelModel):
    type: AuthorizationResourceType
    id: UUID
    customer_id: UUID | None = None


class AuthorizationRequest(CamelModel):
    user_id: UUID
    permission: str = Field(min_length=1)
    resource: AuthorizationResource | None = None


class AuthorizationDecision(CamelModel):
    allowed: bool
    reason_code: str


class BatchAuthorizationRequest(CamelModel):
    requests: list[AuthorizationRequest] = Field(min_length=1, max_length=100)


class BatchAuthorizationDecision(CamelModel):
    decisions: list[AuthorizationDecision]
