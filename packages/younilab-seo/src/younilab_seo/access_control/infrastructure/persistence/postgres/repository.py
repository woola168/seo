from collections import defaultdict
from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from younilab_seo.access_control.application import (
    PasswordReset,
    RefreshSession,
    UserInvitation,
)
from younilab_seo.access_control.domain import (
    AccountStatus,
    Department,
    Role,
    Tenant,
    TenantStatus,
    UserAccount,
)
from younilab_seo.access_control.infrastructure.persistence.postgres.models import (
    CustomerAccessGrantRow,
    DepartmentRow,
    InvitationRow,
    PasswordResetRow,
    RefreshSessionRow,
    RoleRow,
    TaskAccessGrantRow,
    TenantRow,
    UserRoleRow,
    UserRow,
)


class PostgresAccessControlRepository:
    """production persistence 使用的 PostgreSQL AccessControlRepository adapter。"""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def get_tenant(self, tenant_id: UUID) -> Tenant | None:
        async with self._session_factory() as session:
            row = await session.get(TenantRow, tenant_id)
            return _tenant_from_row(row) if row is not None else None

    async def get_tenant_by_code(self, code: str) -> Tenant | None:
        async with self._session_factory() as session:
            row = await session.scalar(
                select(TenantRow).where(TenantRow.code == code.strip().lower())
            )
            return _tenant_from_row(row) if row is not None else None

    async def list_users(self, tenant_id: UUID | None = None) -> list[UserAccount]:
        async with self._session_factory() as session:
            statement = select(UserRow).where(UserRow.deleted_at.is_(None))
            if tenant_id is not None:
                statement = statement.where(UserRow.tenant_id == tenant_id)
            rows = (
                await session.scalars(
                    statement.order_by(UserRow.email)
                )
            ).all()
            tenant_names = await self._list_tenant_names(
                session,
                {row.tenant_id for row in rows},
            )
            user_ids = {row.id for row in rows}
            role_ids_by_user = await self._list_user_role_ids(session, user_ids)
            customer_ids_by_user = await self._list_user_customer_ids(
                session,
                user_ids,
            )
            task_ids_by_user = await self._list_user_task_ids(session, user_ids)
            return [
                self._user_from_row(
                    row,
                    role_ids=role_ids_by_user[row.id],
                    customer_ids=customer_ids_by_user[row.id],
                    task_ids=task_ids_by_user[row.id],
                    tenant_name=tenant_names.get(row.tenant_id),
                )
                for row in rows
            ]

    async def save_user(self, user: UserAccount) -> None:
        async with self._session_factory() as session:
            row = await session.get(UserRow, user.id)
            if row is None:
                now = user.created_at or user.updated_at
                if now is None:
                    raise ValueError("new user requires created_at")
                row = UserRow(
                    id=user.id,
                    tenant_id=user.tenant_id,
                    email=user.email,
                    display_name=user.display_name,
                    status=user.status.value,
                    created_at=now,
                    updated_at=user.updated_at or now,
                )
                session.add(row)
            row.email = user.email
            row.tenant_id = user.tenant_id
            row.display_name = user.display_name
            row.status = user.status.value
            row.department_id = user.department_id
            row.auth_provider = user.auth_provider
            row.last_login_at = user.last_login_at
            row.invited_at = user.invited_at
            row.updated_at = user.updated_at or row.updated_at
            row.deleted_at = user.deleted_at
            await session.commit()

    async def update_password_hash(self, user_id: UUID, password_hash: str) -> None:
        async with self._session_factory() as session:
            await session.execute(
                update(UserRow)
                .where(UserRow.id == user_id)
                .values(password_hash=password_hash)
            )
            await session.commit()

    async def get_user(self, user_id: UUID) -> UserAccount | None:
        async with self._session_factory() as session:
            row = await session.get(UserRow, user_id)
            return await self._map_user(session, row) if row is not None else None

    async def get_user_by_email(self, email: str) -> UserAccount | None:
        async with self._session_factory() as session:
            row = await session.scalar(
                select(UserRow).where(UserRow.email == email.strip().lower())
            )
            return await self._map_user(session, row) if row is not None else None

    async def get_password_hash(self, user_id: UUID) -> str | None:
        async with self._session_factory() as session:
            return await session.scalar(
                select(UserRow.password_hash).where(UserRow.id == user_id)
            )

    async def get_roles(
        self,
        role_ids: set[UUID],
        tenant_id: UUID | None = None,
    ) -> list[Role]:
        if not role_ids:
            return []
        async with self._session_factory() as session:
            statement = select(RoleRow).where(RoleRow.id.in_(role_ids))
            if tenant_id is not None:
                statement = statement.where(RoleRow.tenant_id == tenant_id)
            rows = (
                await session.scalars(statement)
            ).all()
            return [
                Role(
                    id=row.id,
                    name=row.name,
                    tenant_id=row.tenant_id,
                    permissions=frozenset(row.permissions),
                    is_system=row.is_system,
                    has_global_resource_access=row.has_global_resource_access,
                )
                for row in rows
            ]

    async def list_roles(self, tenant_id: UUID | None = None) -> list[Role]:
        async with self._session_factory() as session:
            statement = select(RoleRow)
            if tenant_id is not None:
                statement = statement.where(RoleRow.tenant_id == tenant_id)
            rows = (await session.scalars(statement.order_by(RoleRow.name))).all()
            return [
                Role(
                    id=row.id,
                    name=row.name,
                    tenant_id=row.tenant_id,
                    permissions=frozenset(row.permissions),
                    is_system=row.is_system,
                    has_global_resource_access=row.has_global_resource_access,
                )
                for row in rows
            ]

    async def save_role(self, role: Role) -> None:
        async with self._session_factory() as session:
            row = await session.get(RoleRow, role.id)
            if row is None:
                row = RoleRow(id=role.id, tenant_id=role.tenant_id, name=role.name)
                session.add(row)
            row.tenant_id = role.tenant_id
            row.name = role.name
            row.permissions = sorted(role.permissions)
            row.is_system = role.is_system
            row.has_global_resource_access = role.has_global_resource_access
            await session.commit()

    async def delete_role(self, role_id: UUID) -> None:
        async with self._session_factory() as session:
            await session.execute(
                delete(UserRoleRow).where(UserRoleRow.role_id == role_id)
            )
            await session.execute(delete(RoleRow).where(RoleRow.id == role_id))
            await session.commit()

    async def role_member_count(
        self,
        role_id: UUID,
        tenant_id: UUID | None = None,
    ) -> int:
        async with self._session_factory() as session:
            statement = (
                select(func.count())
                .select_from(UserRoleRow)
                .join(UserRow, UserRow.id == UserRoleRow.user_id)
                .where(
                    UserRoleRow.role_id == role_id,
                    UserRow.deleted_at.is_(None),
                )
            )
            if tenant_id is not None:
                statement = statement.where(UserRow.tenant_id == tenant_id)
            return int(
                await session.scalar(statement)
                or 0
            )

    async def replace_user_roles(
        self,
        user_id: UUID,
        role_ids: set[UUID],
    ) -> None:
        async with self._session_factory() as session:
            existing = (
                await session.scalars(
                    select(UserRoleRow).where(UserRoleRow.user_id == user_id)
                )
            ).all()
            existing_by_role_id = {row.role_id: row for row in existing}
            for role_id, row in existing_by_role_id.items():
                if role_id in role_ids:
                    continue
                await session.delete(row)
            session.add_all(
                [
                    UserRoleRow(user_id=user_id, role_id=role_id)
                    for role_id in role_ids - existing_by_role_id.keys()
                ]
            )
            await session.commit()

    async def replace_customer_grants(
        self,
        user_id: UUID,
        customer_ids: set[UUID],
    ) -> None:
        async with self._session_factory() as session:
            existing = (
                await session.scalars(
                    select(CustomerAccessGrantRow).where(
                        CustomerAccessGrantRow.user_id == user_id
                    )
                )
            ).all()
            existing_by_customer_id = {row.customer_id: row for row in existing}
            for customer_id, row in existing_by_customer_id.items():
                if customer_id in customer_ids:
                    continue
                await session.delete(row)
            session.add_all(
                [
                    CustomerAccessGrantRow(user_id=user_id, customer_id=customer_id)
                    for customer_id in customer_ids - existing_by_customer_id.keys()
                ]
            )
            await session.commit()

    async def replace_task_grants(
        self,
        user_id: UUID,
        task_ids: set[UUID],
    ) -> None:
        async with self._session_factory() as session:
            existing = (
                await session.scalars(
                    select(TaskAccessGrantRow).where(
                        TaskAccessGrantRow.user_id == user_id
                    )
                )
            ).all()
            existing_by_task_id = {row.task_id: row for row in existing}
            for task_id, row in existing_by_task_id.items():
                if task_id in task_ids:
                    continue
                await session.delete(row)
            session.add_all(
                [
                    TaskAccessGrantRow(user_id=user_id, task_id=task_id)
                    for task_id in task_ids - existing_by_task_id.keys()
                ]
            )
            await session.commit()

    async def save_refresh_session(self, refresh_session: RefreshSession) -> None:
        async with self._session_factory() as session:
            session.add(_session_to_row(refresh_session))
            await session.commit()

    async def get_refresh_session(self, token_digest: str) -> RefreshSession | None:
        async with self._session_factory() as session:
            row = await session.scalar(
                select(RefreshSessionRow).where(
                    RefreshSessionRow.token_digest == token_digest
                )
            )
            return _session_from_row(row) if row is not None else None

    async def get_refresh_session_by_id(
        self,
        session_id: UUID,
    ) -> RefreshSession | None:
        async with self._session_factory() as session:
            row = await session.get(RefreshSessionRow, session_id)
            return _session_from_row(row) if row is not None else None

    async def replace_refresh_session(
        self,
        *,
        current_session_id: UUID,
        replacement: RefreshSession,
        revoked_at: datetime,
    ) -> None:
        async with self._session_factory() as session:
            current = await session.get(RefreshSessionRow, current_session_id)
            if current is None:
                raise LookupError("refresh session does not exist")
            current.revoked_at = revoked_at
            current.replaced_by_id = replacement.id
            session.add(_session_to_row(replacement))
            await session.commit()

    async def revoke_refresh_session(
        self,
        session_id: UUID,
        revoked_at: datetime,
    ) -> None:
        async with self._session_factory() as session:
            await session.execute(
                update(RefreshSessionRow)
                .where(
                    RefreshSessionRow.id == session_id,
                    RefreshSessionRow.revoked_at.is_(None),
                )
                .values(revoked_at=revoked_at)
            )
            await session.commit()

    async def revoke_session_family(
        self,
        family_id: UUID,
        revoked_at: datetime,
    ) -> None:
        async with self._session_factory() as session:
            await session.execute(
                update(RefreshSessionRow)
                .where(
                    RefreshSessionRow.family_id == family_id,
                    RefreshSessionRow.revoked_at.is_(None),
                )
                .values(revoked_at=revoked_at)
            )
            await session.commit()

    async def revoke_user_sessions(
        self,
        user_id: UUID,
        revoked_at: datetime,
    ) -> None:
        async with self._session_factory() as session:
            await session.execute(
                update(RefreshSessionRow)
                .where(
                    RefreshSessionRow.user_id == user_id,
                    RefreshSessionRow.revoked_at.is_(None),
                )
                .values(revoked_at=revoked_at)
            )
            await session.commit()

    async def save_password_reset(self, reset: PasswordReset) -> None:
        async with self._session_factory() as session:
            session.add(
                PasswordResetRow(
                    id=reset.id,
                    user_id=reset.user_id,
                    token_digest=reset.token_digest,
                    expires_at=reset.expires_at,
                    created_at=reset.created_at,
                    used_at=reset.used_at,
                    revoked_at=reset.revoked_at,
                )
            )
            await session.commit()

    async def get_password_reset(self, token_digest: str) -> PasswordReset | None:
        async with self._session_factory() as session:
            row = await session.scalar(
                select(PasswordResetRow).where(
                    PasswordResetRow.token_digest == token_digest
                )
            )
            return _password_reset_from_row(row) if row is not None else None

    async def consume_password_reset(
        self,
        reset_id: UUID,
        used_at: datetime,
    ) -> None:
        async with self._session_factory() as session:
            await session.execute(
                update(PasswordResetRow)
                .where(PasswordResetRow.id == reset_id)
                .values(used_at=used_at)
            )
            await session.commit()

    async def revoke_password_resets(
        self,
        user_id: UUID,
        revoked_at: datetime,
    ) -> None:
        async with self._session_factory() as session:
            await session.execute(
                update(PasswordResetRow)
                .where(
                    PasswordResetRow.user_id == user_id,
                    PasswordResetRow.used_at.is_(None),
                    PasswordResetRow.revoked_at.is_(None),
                )
                .values(revoked_at=revoked_at)
            )
            await session.commit()

    async def save_invitation(self, invitation: UserInvitation) -> None:
        async with self._session_factory() as session:
            session.add(
                InvitationRow(
                    id=invitation.id,
                    user_id=invitation.user_id,
                    email=invitation.email,
                    token_digest=invitation.token_digest,
                    expires_at=invitation.expires_at,
                    accepted_at=invitation.accepted_at,
                    revoked_at=invitation.revoked_at,
                    created_at=invitation.created_at,
                    created_by=invitation.created_by,
                )
            )
            await session.commit()

    async def create_invited_user(
        self,
        *,
        user: UserAccount,
        invitation: UserInvitation,
        role_ids: set[UUID],
        customer_ids: set[UUID],
        task_ids: set[UUID],
    ) -> None:
        async with self._session_factory() as session:
            async with session.begin():
                session.add(
                    UserRow(
                        id=user.id,
                        tenant_id=user.tenant_id,
                        email=user.email,
                        display_name=user.display_name,
                        status=user.status.value,
                        password_hash=None,
                        created_at=user.created_at,
                        updated_at=user.updated_at,
                        department_id=user.department_id,
                        auth_provider=user.auth_provider,
                        invited_at=user.invited_at,
                    )
                )
                await session.flush()
                session.add_all(
                    [
                        UserRoleRow(user_id=user.id, role_id=role_id)
                        for role_id in role_ids
                    ]
                )
                session.add_all(
                    [
                        CustomerAccessGrantRow(
                            user_id=user.id,
                            customer_id=customer_id,
                        )
                        for customer_id in customer_ids
                    ]
                )
                session.add_all(
                    [
                        TaskAccessGrantRow(user_id=user.id, task_id=task_id)
                        for task_id in task_ids
                    ]
                )
                session.add(
                    InvitationRow(
                        id=invitation.id,
                        user_id=invitation.user_id,
                        email=invitation.email,
                        token_digest=invitation.token_digest,
                        expires_at=invitation.expires_at,
                        created_at=invitation.created_at,
                        created_by=invitation.created_by,
                    )
                )

    async def get_invitation(
        self,
        invitation_id: UUID,
    ) -> UserInvitation | None:
        async with self._session_factory() as session:
            row = await session.get(InvitationRow, invitation_id)
            return _invitation_from_row(row) if row is not None else None

    async def get_invitation_by_token(
        self,
        token_digest: str,
    ) -> UserInvitation | None:
        async with self._session_factory() as session:
            row = await session.scalar(
                select(InvitationRow).where(
                    InvitationRow.token_digest == token_digest
                )
            )
            return _invitation_from_row(row) if row is not None else None

    async def accept_invitation(
        self,
        invitation_id: UUID,
        accepted_at: datetime,
    ) -> None:
        async with self._session_factory() as session:
            await session.execute(
                update(InvitationRow)
                .where(InvitationRow.id == invitation_id)
                .values(accepted_at=accepted_at)
            )
            await session.commit()

    async def revoke_invitation(
        self,
        invitation_id: UUID,
        revoked_at: datetime,
    ) -> None:
        async with self._session_factory() as session:
            await session.execute(
                update(InvitationRow)
                .where(InvitationRow.id == invitation_id)
                .values(revoked_at=revoked_at)
            )
            await session.commit()

    async def list_departments(
        self,
        tenant_id: UUID | None = None,
    ) -> list[Department]:
        async with self._session_factory() as session:
            statement = select(DepartmentRow).where(DepartmentRow.archived_at.is_(None))
            if tenant_id is not None:
                statement = statement.where(DepartmentRow.tenant_id == tenant_id)
            rows = (
                await session.scalars(
                    statement.order_by(DepartmentRow.name)
                )
            ).all()
            return [_department_from_row(row) for row in rows]

    async def get_department(self, department_id: UUID) -> Department | None:
        async with self._session_factory() as session:
            row = await session.get(DepartmentRow, department_id)
            return _department_from_row(row) if row is not None else None

    async def save_department(self, department: Department) -> None:
        async with self._session_factory() as session:
            row = await session.get(DepartmentRow, department.id)
            if row is None:
                row = DepartmentRow(
                    id=department.id,
                    tenant_id=department.tenant_id,
                    name=department.name,
                    description=department.description,
                    created_at=department.created_at,
                    updated_at=department.updated_at,
                )
                session.add(row)
            row.tenant_id = department.tenant_id
            row.name = department.name
            row.description = department.description
            row.updated_at = department.updated_at
            row.archived_at = department.archived_at
            await session.commit()

    async def department_member_count(
        self,
        department_id: UUID,
        tenant_id: UUID | None = None,
    ) -> int:
        async with self._session_factory() as session:
            statement = (
                select(func.count())
                .select_from(UserRow)
                .where(
                    UserRow.department_id == department_id,
                    UserRow.deleted_at.is_(None),
                )
            )
            if tenant_id is not None:
                statement = statement.where(UserRow.tenant_id == tenant_id)
            return int(
                await session.scalar(statement)
                or 0
            )

    async def _map_user(
        self,
        session: AsyncSession,
        row: UserRow,
    ) -> UserAccount:
        role_ids = set(
            await session.scalars(
                select(UserRoleRow.role_id).where(UserRoleRow.user_id == row.id)
            )
        )
        customer_ids = set(
            await session.scalars(
                select(CustomerAccessGrantRow.customer_id).where(
                    CustomerAccessGrantRow.user_id == row.id
                )
            )
        )
        task_ids = set(
            await session.scalars(
                select(TaskAccessGrantRow.task_id).where(
                    TaskAccessGrantRow.user_id == row.id
                )
            )
        )
        return self._user_from_row(
            row,
            role_ids=role_ids,
            customer_ids=customer_ids,
            task_ids=task_ids,
            tenant_name=await self._tenant_name(session, row.tenant_id),
        )

    async def _tenant_name(self, session: AsyncSession, tenant_id: UUID) -> str | None:
        return await session.scalar(select(TenantRow.name).where(TenantRow.id == tenant_id))

    async def _list_tenant_names(
        self,
        session: AsyncSession,
        tenant_ids: set[UUID],
    ) -> dict[UUID, str]:
        if not tenant_ids:
            return {}
        rows = await session.execute(
            select(TenantRow.id, TenantRow.name).where(TenantRow.id.in_(tenant_ids))
        )
        return {tenant_id: name for tenant_id, name in rows}

    async def _list_user_role_ids(
        self,
        session: AsyncSession,
        user_ids: set[UUID],
    ) -> defaultdict[UUID, set[UUID]]:
        role_ids_by_user: defaultdict[UUID, set[UUID]] = defaultdict(set)
        if not user_ids:
            return role_ids_by_user
        rows = await session.execute(
            select(UserRoleRow.user_id, UserRoleRow.role_id).where(
                UserRoleRow.user_id.in_(user_ids)
            )
        )
        for user_id, role_id in rows:
            role_ids_by_user[user_id].add(role_id)
        return role_ids_by_user

    async def _list_user_customer_ids(
        self,
        session: AsyncSession,
        user_ids: set[UUID],
    ) -> defaultdict[UUID, set[UUID]]:
        customer_ids_by_user: defaultdict[UUID, set[UUID]] = defaultdict(set)
        if not user_ids:
            return customer_ids_by_user
        rows = await session.execute(
            select(
                CustomerAccessGrantRow.user_id,
                CustomerAccessGrantRow.customer_id,
            ).where(CustomerAccessGrantRow.user_id.in_(user_ids))
        )
        for user_id, customer_id in rows:
            customer_ids_by_user[user_id].add(customer_id)
        return customer_ids_by_user

    async def _list_user_task_ids(
        self,
        session: AsyncSession,
        user_ids: set[UUID],
    ) -> defaultdict[UUID, set[UUID]]:
        task_ids_by_user: defaultdict[UUID, set[UUID]] = defaultdict(set)
        if not user_ids:
            return task_ids_by_user
        rows = await session.execute(
            select(TaskAccessGrantRow.user_id, TaskAccessGrantRow.task_id).where(
                TaskAccessGrantRow.user_id.in_(user_ids)
            )
        )
        for user_id, task_id in rows:
            task_ids_by_user[user_id].add(task_id)
        return task_ids_by_user

    def _user_from_row(
        self,
        row: UserRow,
        *,
        role_ids: set[UUID],
        customer_ids: set[UUID],
        task_ids: set[UUID],
        tenant_name: str | None = None,
    ) -> UserAccount:
        return UserAccount(
            id=row.id,
            tenant_id=row.tenant_id,
            tenant_name=tenant_name,
            email=row.email,
            display_name=row.display_name,
            status=AccountStatus(row.status),
            role_ids=role_ids,
            customer_ids=customer_ids,
            task_ids=task_ids,
            department_id=row.department_id,
            auth_provider=row.auth_provider,
            last_login_at=row.last_login_at,
            invited_at=row.invited_at,
            created_at=row.created_at,
            updated_at=row.updated_at,
            deleted_at=row.deleted_at,
        )


def _session_to_row(session: RefreshSession) -> RefreshSessionRow:
    return RefreshSessionRow(
        id=session.id,
        user_id=session.user_id,
        token_digest=session.token_digest,
        family_id=session.family_id,
        expires_at=session.expires_at,
        revoked_at=session.revoked_at,
        replaced_by_id=session.replaced_by_id,
    )


def _session_from_row(row: RefreshSessionRow) -> RefreshSession:
    return RefreshSession(
        id=row.id,
        user_id=row.user_id,
        token_digest=row.token_digest,
        family_id=row.family_id,
        expires_at=row.expires_at,
        revoked_at=row.revoked_at,
        replaced_by_id=row.replaced_by_id,
    )


def _password_reset_from_row(row: PasswordResetRow) -> PasswordReset:
    return PasswordReset(
        id=row.id,
        user_id=row.user_id,
        token_digest=row.token_digest,
        expires_at=row.expires_at,
        created_at=row.created_at,
        used_at=row.used_at,
        revoked_at=row.revoked_at,
    )


def _invitation_from_row(row: InvitationRow) -> UserInvitation:
    return UserInvitation(
        id=row.id,
        user_id=row.user_id,
        email=row.email,
        token_digest=row.token_digest,
        expires_at=row.expires_at,
        created_at=row.created_at,
        created_by=row.created_by,
        accepted_at=row.accepted_at,
        revoked_at=row.revoked_at,
    )


def _department_from_row(row: DepartmentRow) -> Department:
    return Department(
        id=row.id,
        tenant_id=row.tenant_id,
        name=row.name,
        description=row.description,
        created_at=row.created_at,
        updated_at=row.updated_at,
        archived_at=row.archived_at,
    )


def _tenant_from_row(row: TenantRow) -> Tenant:
    return Tenant(
        id=row.id,
        code=row.code,
        name=row.name,
        status=TenantStatus(row.status),
        created_at=row.created_at,
        updated_at=row.updated_at,
        disabled_at=row.disabled_at,
    )
