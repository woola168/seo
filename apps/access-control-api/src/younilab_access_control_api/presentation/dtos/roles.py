from typing import Self
from uuid import UUID

from pydantic import Field

from younilab_access_control_api.presentation.dtos.base import ApiModel, ApiRequest
from younilab_seo.access_control.domain import Role


class RoleResponse(ApiModel):
    """管理 API 回傳的 role 定義與 resource scope 旗標。"""

    id: UUID
    name: str
    permissions: list[str]
    is_system: bool
    has_global_resource_access: bool

    @classmethod
    def from_domain(cls, role: Role) -> Self:
        return cls(
            id=role.id,
            name=role.name,
            permissions=sorted(role.permissions),
            is_system=role.is_system,
            has_global_resource_access=role.has_global_resource_access,
        )


class CreateRoleRequest(ApiRequest):
    """管理員建立 role 時選定的名稱與 permissions。"""

    name: str = Field(min_length=1, max_length=100)
    permissions: set[str] = Field(default_factory=set)


class ReplacePermissionsRequest(ApiRequest):
    """既有 role 的完整替換 permission 集合。"""

    permissions: set[str]
