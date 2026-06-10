import asyncio
from uuid import UUID

from younilab_access_control_application import AuthorizationService
from younilab_access_control_domain import AccountStatus, Role, UserAccount
from younilab_authorization_contracts import (
    AuthorizationRequest,
    AuthorizationResource,
    AuthorizationResourceType,
)


USER_ID = UUID("11111111-1111-4111-8111-111111111111")
ROLE_ID = UUID("22222222-2222-4222-8222-222222222222")
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

    async def get_roles(self, role_ids: set[UUID]):
        return [
            Role(
                id=ROLE_ID,
                name="Specialist",
                permissions=frozenset({"tasks.read"}),
            )
        ]


def test_authorization_service_combines_permission_and_customer_scope() -> None:
    async def scenario() -> None:
        service = AuthorizationService(FakeRepository())  # type: ignore[arg-type]

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
