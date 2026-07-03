from typing import Self
from uuid import UUID

from younilab_access_control_api.presentation.dtos.base import ApiModel
from younilab_seo.access_control.application import Capabilities


class CapabilitiesResponse(ApiModel):
    """目前使用者生效中的 permissions 與 resource grants。"""

    tenant_id: UUID
    permissions: list[str]
    has_global_resource_access: bool
    customer_ids: list[UUID]
    task_ids: list[UUID]

    @classmethod
    def from_domain(cls, capabilities: Capabilities) -> Self:
        return cls(
            tenant_id=capabilities.tenant_id,
            permissions=sorted(capabilities.permissions),
            has_global_resource_access=capabilities.has_global_resource_access,
            customer_ids=sorted(capabilities.customer_ids, key=str),
            task_ids=sorted(capabilities.task_ids, key=str),
        )
