from typing import Self
from uuid import UUID

from younilab_access_control_api.presentation.dtos.base import ApiModel
from younilab_access_control_application import Capabilities


class CapabilitiesResponse(ApiModel):
    permissions: list[str]
    has_global_resource_access: bool
    customer_ids: list[UUID]
    task_ids: list[UUID]

    @classmethod
    def from_domain(cls, capabilities: Capabilities) -> Self:
        return cls(
            permissions=sorted(capabilities.permissions),
            has_global_resource_access=capabilities.has_global_resource_access,
            customer_ids=sorted(capabilities.customer_ids, key=str),
            task_ids=sorted(capabilities.task_ids, key=str),
        )
