from uuid import UUID

from younilab_seo.access_control.application.errors import (
    Conflict,
    OperationNotAllowed,
    ResourceNotFound,
)
from younilab_seo.access_control.application.interfaces import AccessManagementRepository
from younilab_seo.access_control.domain import (
    PERMISSIONS,
    AccountStatus,
    Department,
    Role,
    UserAccount,
)


class AccessManagementService:
    """協調 account、role、grant 與 department 的管理規則。"""

    def __init__(self, repository: AccessManagementRepository, *, clock=None) -> None:
        self._repository = repository
        self._clock = clock

    async def list_users(self) -> list[UserAccount]:
        return await self._repository.list_users()

    async def get_user(self, user_id: UUID) -> UserAccount:
        user = await self._repository.get_user(user_id)
        if user is None:
            raise ResourceNotFound
        return user

    async def update_user(
        self,
        *,
        user_id: UUID,
        display_name: str,
        department_id: UUID | None,
    ) -> UserAccount:
        user = await self.get_user(user_id)
        if department_id is not None:
            department = await self._repository.get_department(department_id)
            if department is None or not department.is_active:
                raise ResourceNotFound
        user.update_profile(
            display_name=display_name,
            department_id=department_id,
            updated_at=self._now(),
        )
        await self._repository.save_user(user)
        return user

    async def change_user_status(
        self,
        *,
        actor_user_id: UUID,
        user_id: UUID,
        status: AccountStatus,
    ) -> UserAccount:
        """變更帳號狀態，同時保留至少一位 active admin。"""
        if actor_user_id == user_id and status is not AccountStatus.ACTIVE:
            raise OperationNotAllowed("cannot disable current user")
        user = await self.get_user(user_id)
        if status is not AccountStatus.ACTIVE:
            await self._ensure_admin_remains(user_id)
        now = self._now()
        user.change_status(status, now)
        await self._repository.save_user(user)
        if status is not AccountStatus.ACTIVE:
            await self._repository.revoke_user_sessions(user.id, now)
        return user

    async def delete_user(
        self,
        *,
        actor_user_id: UUID,
        user_id: UUID,
    ) -> None:
        """軟刪除使用者、撤銷 sessions，並保留 active admin access。"""
        if actor_user_id == user_id:
            raise OperationNotAllowed("cannot delete current user")
        user = await self.get_user(user_id)
        await self._ensure_admin_remains(user_id)
        now = self._now()
        user.delete(now)
        await self._repository.save_user(user)
        await self._repository.revoke_user_sessions(user.id, now)

    async def revoke_user_sessions(self, user_id: UUID) -> None:
        await self.get_user(user_id)
        await self._repository.revoke_user_sessions(user_id, self._now())

    async def list_roles(self) -> list[Role]:
        return await self._repository.list_roles()

    async def create_role(
        self,
        *,
        role_id: UUID,
        name: str,
        permissions: set[str],
    ) -> Role:
        """只使用已知 access-control permissions 建立 role。"""
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
        """替換 role 的 permissions，但不改變 identity 或 flags。"""
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

    async def delete_role(self, role_id: UUID) -> None:
        roles = await self._repository.get_roles({role_id})
        if not roles:
            raise ResourceNotFound
        role = roles[0]
        if role.is_system:
            raise Conflict("system role cannot be deleted")
        if await self._repository.role_member_count(role_id):
            raise Conflict("role is still in use")
        await self._repository.delete_role(role_id)

    async def replace_user_roles(
        self,
        *,
        user_id: UUID,
        role_ids: set[UUID],
    ) -> UserAccount:
        """驗證 role 存在與 admin continuity 後，替換使用者 roles。"""
        await self.get_user(user_id)
        if len(await self._repository.get_roles(role_ids)) != len(role_ids):
            raise ResourceNotFound
        await self._ensure_admin_remains(user_id, replacement_role_ids=role_ids)
        await self._repository.replace_user_roles(user_id, role_ids)
        return await self.get_user(user_id)

    async def list_departments(self) -> list[Department]:
        return await self._repository.list_departments()

    async def create_department(
        self,
        *,
        department_id: UUID,
        name: str,
        description: str,
    ) -> Department:
        if any(
            item.name.lower() == name.strip().lower()
            for item in await self._repository.list_departments()
            if item.is_active
        ):
            raise Conflict("department name already exists")
        now = self._now()
        department = Department(
            id=department_id,
            name=name,
            description=description,
            created_at=now,
            updated_at=now,
        )
        await self._repository.save_department(department)
        return department

    async def update_department(
        self,
        *,
        department_id: UUID,
        name: str,
        description: str,
    ) -> Department:
        department = await self._repository.get_department(department_id)
        if department is None or not department.is_active:
            raise ResourceNotFound
        department.update(
            name=name,
            description=description,
            updated_at=self._now(),
        )
        await self._repository.save_department(department)
        return department

    async def archive_department(self, department_id: UUID) -> None:
        department = await self._repository.get_department(department_id)
        if department is None or not department.is_active:
            raise ResourceNotFound
        if await self._repository.department_member_count(department_id):
            raise Conflict("department is still in use")
        department.archive(self._now())
        await self._repository.save_department(department)

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

    async def _ensure_admin_remains(
        self,
        user_id: UUID,
        *,
        replacement_role_ids: set[UUID] | None = None,
    ) -> None:
        users = [user for user in await self._repository.list_users() if user.is_active]
        roles = {role.id: role for role in await self._repository.list_roles()}

        def is_admin(user: UserAccount) -> bool:
            role_ids = (
                replacement_role_ids
                if user.id == user_id and replacement_role_ids is not None
                else user.role_ids
            )
            permissions = {
                permission
                for role_id in role_ids
                for permission in roles.get(
                    role_id,
                    Role(id=role_id, name="missing", permissions=frozenset()),
                ).permissions
            }
            return {"users.manage", "roles.manage"} <= permissions

        current = next((user for user in users if user.id == user_id), None)
        if current is not None and is_admin(current):
            remaining = [user for user in users if user.id != user_id and is_admin(user)]
            if not remaining:
                raise OperationNotAllowed("last administrator must remain active")

    def _now(self):
        if self._clock is None:
            from datetime import UTC, datetime

            return datetime.now(UTC)
        return self._clock.now()
