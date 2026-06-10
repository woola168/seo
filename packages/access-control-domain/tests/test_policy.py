from uuid import UUID

from younilab_access_control_domain import (
    AccessPolicy,
    AccountStatus,
    AuthorizationReason,
    ProtectedResource,
    ResourceType,
    Role,
    UserAccount,
)


USER_ID = UUID("11111111-1111-4111-8111-111111111111")
ROLE_ID = UUID("22222222-2222-4222-8222-222222222222")
CUSTOMER_ID = UUID("33333333-3333-4333-8333-333333333333")
TASK_ID = UUID("44444444-4444-4444-8444-444444444444")


def user(
    *,
    status: AccountStatus = AccountStatus.ACTIVE,
    customer_ids: set[UUID] | None = None,
    task_ids: set[UUID] | None = None,
) -> UserAccount:
    return UserAccount(
        id=USER_ID,
        email="user@example.com",
        display_name="SEO User",
        status=status,
        role_ids={ROLE_ID},
        customer_ids=customer_ids or set(),
        task_ids=task_ids or set(),
    )


def role(*, global_access: bool = False) -> Role:
    return Role(
        id=ROLE_ID,
        name="SEO Specialist",
        permissions=frozenset({"tasks.read"}),
        has_global_resource_access=global_access,
    )


def task_resource() -> ProtectedResource:
    return ProtectedResource(
        type=ResourceType.TASK,
        id=TASK_ID,
        customer_id=CUSTOMER_ID,
    )


def test_customer_grant_includes_customer_tasks() -> None:
    decision = AccessPolicy().evaluate(
        user=user(customer_ids={CUSTOMER_ID}),
        roles=[role()],
        permission="tasks.read",
        resource=task_resource(),
    )

    assert decision.allowed is True
    assert decision.reason_code == AuthorizationReason.CUSTOMER_ACCESS_GRANTED


def test_task_grant_does_not_require_customer_grant() -> None:
    decision = AccessPolicy().evaluate(
        user=user(task_ids={TASK_ID}),
        roles=[role()],
        permission="tasks.read",
        resource=task_resource(),
    )

    assert decision.allowed is True
    assert decision.reason_code == AuthorizationReason.TASK_ACCESS_GRANTED


def test_permission_is_required_even_when_resource_is_granted() -> None:
    decision = AccessPolicy().evaluate(
        user=user(customer_ids={CUSTOMER_ID}),
        roles=[role()],
        permission="tasks.update",
        resource=task_resource(),
    )

    assert decision.allowed is False
    assert decision.reason_code == AuthorizationReason.PERMISSION_DENIED


def test_global_role_bypasses_resource_grants() -> None:
    decision = AccessPolicy().evaluate(
        user=user(),
        roles=[role(global_access=True)],
        permission="tasks.read",
        resource=task_resource(),
    )

    assert decision.allowed is True
    assert decision.reason_code == AuthorizationReason.GLOBAL_ACCESS_GRANTED


def test_disabled_account_is_always_denied() -> None:
    decision = AccessPolicy().evaluate(
        user=user(
            status=AccountStatus.DISABLED,
            customer_ids={CUSTOMER_ID},
        ),
        roles=[role(global_access=True)],
        permission="tasks.read",
        resource=task_resource(),
    )

    assert decision.allowed is False
    assert decision.reason_code == AuthorizationReason.ACCOUNT_INACTIVE
