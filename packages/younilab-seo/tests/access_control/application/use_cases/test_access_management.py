import asyncio
import pytest
from uuid import UUID

from younilab_seo.access_control.application import (
    AccessManagementService,
    Conflict,
    ResourceNotFound,
)
from younilab_seo.access_control.domain import AccountStatus, Role, UserAccount
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
