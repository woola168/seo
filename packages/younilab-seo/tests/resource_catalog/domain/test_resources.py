from datetime import UTC, datetime
from uuid import uuid4

from younilab_seo.resource_catalog.domain import Customer, ResourceStatus, SeoTask


def test_resources_normalize_names_and_archive() -> None:
    now = datetime.now(UTC)
    customer = Customer(uuid4(), " Acme ", ResourceStatus.ACTIVE, now, now)
    task = SeoTask(uuid4(), customer.id, " Audit ", ResourceStatus.ACTIVE, now, now)

    customer.archive(now)
    task.archive(now)

    assert customer.name == "Acme"
    assert task.name == "Audit"
    assert customer.status is ResourceStatus.ARCHIVED
    assert task.status is ResourceStatus.ARCHIVED
