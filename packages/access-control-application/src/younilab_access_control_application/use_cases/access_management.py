from uuid import UUID

from younilab_access_control_application.errors import Conflict, ResourceNotFound
from younilab_access_control_application.interfaces import AccessManagementRepository
from younilab_access_control_domain import PERMISSIONS, Role, UserAccount


class AccessManagementService:
    def __init__(self, repository: AccessManagementRepository) -> None:
        self._repository = repository

    async def list_users(self) -> list[UserAccount]:
        return await self._repository.list_users()

    async def get_user(self, user_id: UUID) -> UserAccount:
        user = await self._repository.get_user(user_id)
        if user is None:
            raise ResourceNotFound
        return user

    async def list_roles(self) -> list[Role]:
        return await self._repository.list_roles()

    async def create_role(
        self,
        *,
        role_id: UUID,
        name: str,
        permissions: set[str],
    ) -> Role:
        self._validate_permissions(permissions)
        if any(
            role.name.lower() == name.strip().lower()
            for role in await self.list_roles()
        ):
            raise Conflict("role name already exists")
        role = Role(
            id=role_id,
            name=name,
            permissions=frozenset(permissions),
        )
        await self._repository.save_role(role)
        return role

    async def replace_role_permissions(
        self,
        *,
        role_id: UUID,
        permissions: set[str],
    ) -> Role:
        self._validate_permissions(permissions)
        roles = await self._repository.get_roles({role_id})
        if not roles:
            raise ResourceNotFound
        current = roles[0]
        role = Role(
            id=current.id,
            name=current.name,
            permissions=frozenset(permissions),
            is_system=current.is_system,
            has_global_resource_access=current.has_global_resource_access,
        )
        await self._repository.save_role(role)
        return role

    async def replace_user_roles(
        self,
        *,
        user_id: UUID,
        role_ids: set[UUID],
    ) -> UserAccount:
        await self.get_user(user_id)
        if len(await self._repository.get_roles(role_ids)) != len(role_ids):
            raise ResourceNotFound
        await self._repository.replace_user_roles(user_id, role_ids)
        return await self.get_user(user_id)

    async def replace_customer_grants(
        self,
        *,
        user_id: UUID,
        customer_ids: set[UUID],
    ) -> UserAccount:
        await self.get_user(user_id)
        await self._repository.replace_customer_grants(user_id, customer_ids)
        return await self.get_user(user_id)

    async def replace_task_grants(
        self,
        *,
        user_id: UUID,
        task_ids: set[UUID],
    ) -> UserAccount:
        await self.get_user(user_id)
        await self._repository.replace_task_grants(user_id, task_ids)
        return await self.get_user(user_id)

    @staticmethod
    def _validate_permissions(permissions: set[str]) -> None:
        unknown = permissions - PERMISSIONS
        if unknown:
            raise Conflict(f"unknown permissions: {', '.join(sorted(unknown))}")
