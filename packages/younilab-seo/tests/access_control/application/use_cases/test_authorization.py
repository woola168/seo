import asyncio
from uuid import UUID

from younilab_seo.access_control.application import (
    AuthorizationRepository,
    AuthorizationService,
)
from younilab_seo.access_control.domain import AccountStatus, Role, UserAccount
from younilab_seo.access_control.contracts import (
    AuthorizationRequest,
    AuthorizationResource,
    AuthorizationResourceType,
)


USER_ID = UUID("11111111-1111-4111-8111-111111111111")
ROLE_ID = UUID("22222222-2222-4222-8222-222222222222")
OTHER_ROLE_ID = UUID("99999999-9999-4999-8999-999999999999")
OTHER_TENANT_ID = UUID("88888888-8888-4888-8888-888888888888")
CUSTOMER_ID = UUID("33333333-3333-4333-8333-333333333333")
TASK_ID = UUID("44444444-4444-4444-8444-444444444444")


class FakeRepository:
    async def get_user(self, user_id: UUID):
        return UserAccount(
            id=USER_ID,
            email="seo@example.com",
            display_name="SEO User",
            status=AccountStatus.ACTIVE,
            role_ids={ROLE_ID},
            customer_ids={CUSTOMER_ID},
        )

    async def get_roles(self, role_ids: set[UUID], tenant_id: UUID | None = None):
        return [
            Role(
                id=ROLE_ID,
                name="Specialist",
                permissions=frozenset({"tasks.read"}),
            )
        ]


def test_authorization_service_combines_permission_and_customer_scope() -> None:
    async def scenario() -> None:
        repository = FakeRepository()
        assert isinstance(repository, AuthorizationRepository)
        service = AuthorizationService(repository)

        decision = await service.evaluate(
            AuthorizationRequest(
                user_id=USER_ID,
                permission="tasks.read",
                resource=AuthorizationResource(
                    type=AuthorizationResourceType.TASK,
                    id=TASK_ID,
                    customer_id=CUSTOMER_ID,
                ),
            )
        )

        assert decision.allowed is True

    asyncio.run(scenario())


def test_authorization_service_filters_roles_by_user_tenant() -> None:
    class TenantAwareFakeRepository:
        async def get_user(self, user_id: UUID):
            return UserAccount(
                id=USER_ID,
                email="seo@example.com",
                display_name="SEO User",
                status=AccountStatus.ACTIVE,
                role_ids={OTHER_ROLE_ID},
                customer_ids={CUSTOMER_ID},
            )

        async def get_roles(
            self,
            role_ids: set[UUID],
            tenant_id: UUID | None = None,
        ):
            role = Role(
                id=OTHER_ROLE_ID,
                tenant_id=OTHER_TENANT_ID,
                name="Other Tenant Role",
                permissions=frozenset({"tasks.read"}),
            )
            return [role] if role.id in role_ids and role.tenant_id == tenant_id else []

    async def scenario() -> None:
        service = AuthorizationService(TenantAwareFakeRepository())

        decision = await service.evaluate(
            AuthorizationRequest(
                user_id=USER_ID,
                permission="tasks.read",
                resource=AuthorizationResource(
                    type=AuthorizationResourceType.TASK,
                    id=TASK_ID,
                    customer_id=CUSTOMER_ID,
                ),
            )
        )

        assert decision.allowed is False

    asyncio.run(scenario())
