from typing import Self
from uuid import UUID

from younilab_access_control_api.presentation.dtos.base import ApiModel, ApiRequest
from younilab_access_control_domain import UserAccount


class UserResponse(ApiModel):
    id: UUID
    email: str
    display_name: str
    status: str
    role_ids: list[UUID]

    @classmethod
    def from_domain(cls, user: UserAccount) -> Self:
        return cls(
            id=user.id,
            email=user.email,
            display_name=user.display_name,
            status=user.status.value,
            role_ids=sorted(user.role_ids, key=str),
        )


class UserAccessResponse(UserResponse):
    customer_ids: list[UUID]
    task_ids: list[UUID]

    @classmethod
    def from_domain(cls, user: UserAccount) -> Self:
        return cls(
            id=user.id,
            email=user.email,
            display_name=user.display_name,
            status=user.status.value,
            role_ids=sorted(user.role_ids, key=str),
            customer_ids=sorted(user.customer_ids, key=str),
            task_ids=sorted(user.task_ids, key=str),
        )


class ReplaceRolesRequest(ApiRequest):
    role_ids: set[UUID]
