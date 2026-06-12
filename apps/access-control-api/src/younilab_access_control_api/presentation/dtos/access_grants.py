from uuid import UUID

from younilab_access_control_api.presentation.dtos.base import ApiRequest


class ReplaceCustomerGrantsRequest(ApiRequest):
    customer_ids: set[UUID]


class ReplaceTaskGrantsRequest(ApiRequest):
    task_ids: set[UUID]
