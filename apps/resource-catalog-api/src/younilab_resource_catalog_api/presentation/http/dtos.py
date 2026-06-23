from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from younilab_seo.resource_catalog.domain import Customer, ResourceStatus, SeoTask


def _camel_case(value: str) -> str:
    head, *tail = value.split("_")
    return head + "".join(part.capitalize() for part in tail)


class ApiModel(BaseModel):
    """將 snake_case 欄位以 camelCase JSON 呈現的 schema 基底。"""

    model_config = ConfigDict(
        alias_generator=_camel_case,
        populate_by_name=True,
    )


class SaveCustomerRequest(ApiModel):
    """建立或更新 customer 時接受的名稱。"""

    name: str = Field(min_length=1, max_length=200)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("name must not be empty")
        return normalized


class SaveTaskRequest(ApiModel):
    """建立或更新 task 時接受的 customer 與名稱。"""

    customer_id: UUID
    name: str = Field(min_length=1, max_length=200)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("name must not be empty")
        return normalized


class CustomerResponse(ApiModel):
    """catalog API 回傳的 customer master-data resource。"""

    id: UUID
    name: str
    status: ResourceStatus
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, customer: Customer):
        return cls(**customer.__dict__)


class TaskResponse(ApiModel):
    """包含 customer 顯示名稱的 SEO task resource。"""

    id: UUID
    customer_id: UUID
    customer_name: str
    name: str
    status: ResourceStatus
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, task: SeoTask, customer_name: str):
        return cls(**task.__dict__, customer_name=customer_name)


class PageResponse(ApiModel):
    """包含切頁前總數的分頁清單回應。"""

    items: list
    page: int
    page_size: int
    total: int
    total_pages: int


def page_response(items: list, page: int, page_size: int) -> PageResponse:
    total = len(items)
    start = (page - 1) * page_size
    return PageResponse(
        items=items[start : start + page_size],
        page=page,
        page_size=page_size,
        total=total,
        total_pages=(total + page_size - 1) // page_size,
    )
