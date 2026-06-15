from datetime import datetime
from typing import Self
from uuid import UUID

from younilab_access_control_api.presentation.dtos.base import ApiModel, ApiRequest
from younilab_access_control_domain import Department


class DepartmentResponse(ApiModel):
    id: UUID
    name: str
    description: str
    member_count: int
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, department: Department, member_count: int) -> Self:
        return cls(
            id=department.id,
            name=department.name,
            description=department.description,
            member_count=member_count,
            created_at=department.created_at,
            updated_at=department.updated_at,
        )


class SaveDepartmentRequest(ApiRequest):
    name: str
    description: str = ""
