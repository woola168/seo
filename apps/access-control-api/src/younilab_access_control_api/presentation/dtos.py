from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


def _camel_case(value: str) -> str:
    head, *tail = value.split("_")
    return head + "".join(part.capitalize() for part in tail)


class ApiModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=_camel_case,
        populate_by_name=True,
    )


class LoginRequest(ApiModel):
    email: EmailStr
    password: str = Field(min_length=1)


class TokenResponse(ApiModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime


class UserResponse(ApiModel):
    id: UUID
    email: str
    display_name: str
    status: str
    role_ids: list[UUID]


class CapabilitiesResponse(ApiModel):
    permissions: list[str]
    has_global_resource_access: bool
    customer_ids: list[UUID]
    task_ids: list[UUID]


class RoleResponse(ApiModel):
    id: UUID
    name: str
    permissions: list[str]
    is_system: bool
    has_global_resource_access: bool


class CreateRoleRequest(ApiModel):
    name: str = Field(min_length=1, max_length=100)
    permissions: set[str] = Field(default_factory=set)


class ReplacePermissionsRequest(ApiModel):
    permissions: set[str]


class ReplaceRolesRequest(ApiModel):
    role_ids: set[UUID]


class ReplaceCustomerGrantsRequest(ApiModel):
    customer_ids: set[UUID]


class ReplaceTaskGrantsRequest(ApiModel):
    task_ids: set[UUID]


class UserAccessResponse(UserResponse):
    customer_ids: list[UUID]
    task_ids: list[UUID]
