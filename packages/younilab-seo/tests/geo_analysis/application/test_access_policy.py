from datetime import UTC, datetime
from uuid import UUID, uuid4

from younilab_seo.geo_analysis.application import AuthorizedPrincipal, GeoProjectRecord
from younilab_seo.geo_analysis.application.use_cases.access_policy import (
    can_access_project,
    filter_accessible_projects,
)


TENANT_ID = UUID("00000000-0000-4000-8000-000000000001")
OTHER_TENANT_ID = UUID("00000000-0000-4000-8000-000000000002")


def test_global_principal_can_access_same_tenant_projects() -> None:
    project = _project()
    principal = _principal(has_global_resource_access=True)

    assert can_access_project(principal, project) is True


def test_customer_and_task_grants_limit_project_access() -> None:
    customer_id = uuid4()
    task_id = uuid4()
    allowed_by_customer = _project(customer_id=customer_id)
    allowed_by_task = _project(seo_task_id=task_id)
    denied = _project(customer_id=uuid4(), seo_task_id=uuid4())
    unscoped = _project()
    principal = _principal(
        customer_ids=frozenset({customer_id}),
        task_ids=frozenset({task_id}),
    )

    assert filter_accessible_projects(
        principal,
        [allowed_by_customer, allowed_by_task, denied, unscoped],
    ) == [allowed_by_customer, allowed_by_task]


def test_project_access_rejects_other_tenant() -> None:
    principal = _principal(has_global_resource_access=True)

    assert can_access_project(principal, _project(tenant_id=OTHER_TENANT_ID)) is False


def _principal(
    *,
    has_global_resource_access: bool = False,
    customer_ids: frozenset[UUID] = frozenset(),
    task_ids: frozenset[UUID] = frozenset(),
) -> AuthorizedPrincipal:
    return AuthorizedPrincipal(
        tenant_id=TENANT_ID,
        permissions=frozenset(),
        has_global_resource_access=has_global_resource_access,
        customer_ids=customer_ids,
        task_ids=task_ids,
    )


def _project(
    *,
    tenant_id: UUID = TENANT_ID,
    customer_id: UUID | None = None,
    seo_task_id: UUID | None = None,
) -> GeoProjectRecord:
    now = datetime(2026, 7, 2, tzinfo=UTC)
    return GeoProjectRecord(
        id=uuid4(),
        tenant_id=tenant_id,
        customer_id=customer_id,
        seo_task_id=seo_task_id,
        name="GEO",
        default_region="TW",
        default_language="zh-TW",
        status="active",
        daily_run_budget=0,
        created_at=now,
        updated_at=now,
    )
