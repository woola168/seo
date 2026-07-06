from dataclasses import dataclass, field
from uuid import UUID

from younilab_seo.access_control.domain.tenants import DEFAULT_TENANT_ID


@dataclass(frozen=True)
class Role:
    """可同時授予 global resource access 的 permission set。"""

    id: UUID
    name: str
    tenant_id: UUID = DEFAULT_TENANT_ID
    permissions: frozenset[str] = field(default_factory=frozenset)
    is_system: bool = False
    has_global_resource_access: bool = False

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("role name must not be empty")
        if any(not permission.strip() for permission in self.permissions):
            raise ValueError("permission must not be empty")
