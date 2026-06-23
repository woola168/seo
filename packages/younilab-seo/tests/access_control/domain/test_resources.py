from uuid import UUID

import pytest

from younilab_seo.access_control.domain import ProtectedResource, ResourceType


def test_task_resource_requires_customer_id() -> None:
    with pytest.raises(ValueError, match="task resource customer id is required"):
        ProtectedResource(
            type=ResourceType.TASK,
            id=UUID("33333333-3333-4333-8333-333333333333"),
        )
