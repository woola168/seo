from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from younilab_resource_catalog_domain import Customer, ResourceStatus, SeoTask


def _camel_case(value: str) -> str:
    head, *tail = value.split("_")
    return head + "".join(part.capitalize() for part in tail)


class ApiModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=_camel_case,
        populate_by_name=True,
    )


class SaveCustomerRequest(ApiModel):
    name: str = Field(min_length=1, max_length=200)


class SaveTaskRequest(ApiModel):
    customer_id: UUID
    name: str = Field(min_length=1, max_length=200)


class CustomerResponse(ApiModel):
    id: UUID
    name: str
    status: ResourceStatus
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, customer: Customer):
        return cls(**customer.__dict__)


class TaskResponse(ApiModel):
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
