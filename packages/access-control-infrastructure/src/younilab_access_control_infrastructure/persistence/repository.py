from datetime import datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from younilab_access_control_application import RefreshSession
from younilab_access_control_domain import AccountStatus, Role, UserAccount
from younilab_access_control_infrastructure.persistence.models import (
    CustomerAccessGrantRow,
    RefreshSessionRow,
    RoleRow,
    TaskAccessGrantRow,
    UserRoleRow,
    UserRow,
)


class PostgresAccessControlRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def list_users(self) -> list[UserAccount]:
        async with self._session_factory() as session:
            rows = (await session.scalars(select(UserRow).order_by(UserRow.email))).all()
            return [await self._map_user(session, row) for row in rows]

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

    async def get_roles(self, role_ids: set[UUID]) -> list[Role]:
        if not role_ids:
            return []
        async with self._session_factory() as session:
            rows = (
                await session.scalars(select(RoleRow).where(RoleRow.id.in_(role_ids)))
            ).all()
            return [
                Role(
                    id=row.id,
                    name=row.name,
                    permissions=frozenset(row.permissions),
                    is_system=row.is_system,
                    has_global_resource_access=row.has_global_resource_access,
                )
                for row in rows
            ]

    async def list_roles(self) -> list[Role]:
        async with self._session_factory() as session:
            rows = (await session.scalars(select(RoleRow).order_by(RoleRow.name))).all()
            return [
                Role(
                    id=row.id,
                    name=row.name,
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
                row = RoleRow(id=role.id, name=role.name)
                session.add(row)
            row.name = role.name
            row.permissions = sorted(role.permissions)
            row.is_system = role.is_system
            row.has_global_resource_access = role.has_global_resource_access
            await session.commit()

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
            for row in existing:
                await session.delete(row)
            session.add_all(
                [UserRoleRow(user_id=user_id, role_id=role_id) for role_id in role_ids]
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
            for row in existing:
                await session.delete(row)
            session.add_all(
                [
                    CustomerAccessGrantRow(user_id=user_id, customer_id=customer_id)
                    for customer_id in customer_ids
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
            for row in existing:
                await session.delete(row)
            session.add_all(
                [
                    TaskAccessGrantRow(user_id=user_id, task_id=task_id)
                    for task_id in task_ids
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
        return UserAccount(
            id=row.id,
            email=row.email,
            display_name=row.display_name,
            status=AccountStatus(row.status),
            role_ids=role_ids,
            customer_ids=customer_ids,
            task_ids=task_ids,
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
