from uuid import UUID

from younilab_access_control_api.presentation.dtos.base import ApiRequest


class ReplaceCustomerGrantsRequest(ApiRequest):
    """單一使用者的完整 customer 授權清單。"""

    customer_ids: set[UUID]


class ReplaceTaskGrantsRequest(ApiRequest):
    """單一使用者的完整 task 授權清單。"""

    task_ids: set[UUID]
