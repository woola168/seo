import asyncio
import pytest
from uuid import UUID

from younilab_seo.access_control.application import (
    AccessManagementService,
    Conflict,
    ResourceNotFound,
)
from younilab_seo.access_control.domain import (
    DEFAULT_TENANT_ID,
    AccountStatus,
    Role,
    UserAccount,
)
from younilab_seo.access_control.infrastructure import MemoryAccessControlRepository


def test_delete_role_removes_unused_non_system_role() -> None:
    async def scenario() -> None:
        role_id = UUID("11111111-1111-4111-8111-111111111111")
        repository = MemoryAccessControlRepository(
            roles=[Role(id=role_id, name="SEO Viewer", permissions=frozenset())],
        )
        service = AccessManagementService(repository)

        await service.delete_role(role_id)

        assert await repository.list_roles() == []

    asyncio.run(scenario())


def test_internal_permission_cannot_be_assigned_to_a_new_role() -> None:
    async def scenario() -> None:
        service = AccessManagementService(MemoryAccessControlRepository())

        with pytest.raises(Conflict, match="unknown permissions: geo.admin.access"):
            await service.create_role(
                role_id=UUID("11111111-1111-4111-8111-111111111111"),
                name="RD Admin",
                permissions={"geo.admin.access"},
            )

    asyncio.run(scenario())


def test_replacing_role_permissions_preserves_internal_permissions() -> None:
    async def scenario() -> None:
        role_id = UUID("11111111-1111-4111-8111-111111111111")
        repository = MemoryAccessControlRepository(
            roles=[
                Role(
                    id=role_id,
                    name="admin",
                    permissions=frozenset(
                        {"geo.admin.access", "geo.projects.read"}
                    ),
                    is_system=True,
                )
            ],
        )
        service = AccessManagementService(repository)

        updated = await service.replace_role_permissions(
            role_id=role_id,
            permissions={"customers.read"},
        )

        assert updated.permissions == frozenset(
            {"geo.admin.access", "customers.read"}
        )

    asyncio.run(scenario())


def test_replacing_role_permissions_accepts_existing_internal_permissions() -> None:
    async def scenario() -> None:
        role_id = UUID("11111111-1111-4111-8111-111111111111")
        repository = MemoryAccessControlRepository(
            roles=[
                Role(
                    id=role_id,
                    name="admin",
                    permissions=frozenset(
                        {"geo.admin.access", "geo.projects.read"}
                    ),
                    is_system=True,
                )
            ],
        )
        service = AccessManagementService(repository)

        updated = await service.replace_role_permissions(
            role_id=role_id,
            permissions={"geo.admin.access", "customers.read"},
        )

        assert updated.permissions == frozenset(
            {"geo.admin.access", "customers.read"}
        )

    asyncio.run(scenario())


def test_replacing_role_permissions_rejects_new_internal_permissions() -> None:
    async def scenario() -> None:
        role_id = UUID("11111111-1111-4111-8111-111111111111")
        repository = MemoryAccessControlRepository(
            roles=[
                Role(
                    id=role_id,
                    name="viewer",
                    permissions=frozenset({"geo.projects.read"}),
                )
            ],
        )
        service = AccessManagementService(repository)

        with pytest.raises(Conflict, match="unknown permissions: geo.admin.access"):
            await service.replace_role_permissions(
                role_id=role_id,
                permissions={"geo.admin.access", "geo.projects.read"},
            )

    asyncio.run(scenario())


def test_delete_role_rejects_missing_system_and_used_roles() -> None:
    async def scenario() -> None:
        system_role_id = UUID("11111111-1111-4111-8111-111111111111")
        used_role_id = UUID("22222222-2222-4222-8222-222222222222")
        missing_role_id = UUID("33333333-3333-4333-8333-333333333333")
        repository = MemoryAccessControlRepository(
            users=[
                UserAccount(
                    id=UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"),
                    email="user@example.com",
                    display_name="User",
                    status=AccountStatus.ACTIVE,
                    role_ids={used_role_id},
                )
            ],
            roles=[
                Role(
                    id=system_role_id,
                    name="admin",
                    permissions=frozenset(),
                    is_system=True,
                ),
                Role(id=used_role_id, name="Used", permissions=frozenset()),
            ],
        )
        service = AccessManagementService(repository)

        with pytest.raises(ResourceNotFound):
            await service.delete_role(missing_role_id)
        with pytest.raises(Conflict, match="system role cannot be deleted"):
            await service.delete_role(system_role_id)
        with pytest.raises(Conflict, match="role is still in use"):
            await service.delete_role(used_role_id)

    asyncio.run(scenario())


def test_replace_user_roles_rejects_cross_tenant_role() -> None:
    async def scenario() -> None:
        tenant_id = UUID("99999999-9999-4999-8999-999999999999")
        user_id = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
        own_role_id = UUID("11111111-1111-4111-8111-111111111111")
        other_role_id = UUID("22222222-2222-4222-8222-222222222222")
        repository = MemoryAccessControlRepository(
            users=[
                UserAccount(
                    id=user_id,
                    email="user@example.com",
                    display_name="User",
                    status=AccountStatus.ACTIVE,
                    role_ids={own_role_id},
                )
            ],
            roles=[
                Role(id=own_role_id, name="Own", permissions=frozenset()),
                Role(
                    id=other_role_id,
                    tenant_id=tenant_id,
                    name="Other",
                    permissions=frozenset(),
                ),
            ],
        )
        service = AccessManagementService(repository)

        with pytest.raises(ResourceNotFound):
            await service.replace_user_roles(
                user_id=user_id,
                role_ids={other_role_id},
            )

    asyncio.run(scenario())


def test_replace_customer_grants_validates_resource_tenant() -> None:
    async def scenario() -> None:
        user_id = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
        customer_id = UUID("11111111-1111-4111-8111-111111111111")
        verifier = FakeResourceGrantVerifier(allowed=False)
        repository = MemoryAccessControlRepository(
            users=[
                UserAccount(
                    id=user_id,
                    email="user@example.com",
                    display_name="User",
                    status=AccountStatus.ACTIVE,
                )
            ],
        )
        service = AccessManagementService(
            repository,
            resource_grant_verifier=verifier,
        )

        with pytest.raises(ResourceNotFound):
            await service.replace_customer_grants(
                user_id=user_id,
                customer_ids={customer_id},
                tenant_id=DEFAULT_TENANT_ID,
                access_token="token",
            )

        assert repository.users[user_id].customer_ids == set()
        assert verifier.customer_checks == [
            (DEFAULT_TENANT_ID, {customer_id}, "token")
        ]

    asyncio.run(scenario())


class FakeResourceGrantVerifier:
    def __init__(self, *, allowed: bool = True) -> None:
        self.allowed = allowed
        self.customer_checks = []
        self.task_checks = []

    async def require_customers_in_tenant(
        self,
        tenant_id,
        customer_ids,
        access_token=None,
    ) -> None:
        self.customer_checks.append((tenant_id, customer_ids, access_token))
        if not self.allowed:
            raise ResourceNotFound

    async def require_tasks_in_tenant(
        self,
        tenant_id,
        task_ids,
        access_token=None,
    ) -> None:
        self.task_checks.append((tenant_id, task_ids, access_token))
        if not self.allowed:
            raise ResourceNotFound
