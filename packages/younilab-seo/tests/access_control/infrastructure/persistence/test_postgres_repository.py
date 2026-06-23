import asyncio
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import event, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlmodel import SQLModel

from younilab_seo.access_control.application import UserInvitation
from younilab_seo.access_control.domain import AccountStatus, UserAccount
from younilab_seo.access_control.infrastructure.persistence.postgres.models import (
    ACCESS_CONTROL_TABLES,
    CustomerAccessGrantRow,
    InvitationRow,
    RoleRow,
    TaskAccessGrantRow,
    UserRoleRow,
    UserRow,
)
from younilab_seo.access_control.infrastructure.persistence.postgres.repository import (
    PostgresAccessControlRepository,
)


def create_access_control_tables(connection) -> None:
    for table in ACCESS_CONTROL_TABLES:
        table.create(connection)


def test_replace_user_roles_preserves_existing_role_and_adds_new_role() -> None:
    async def scenario() -> None:
        engine = create_async_engine("sqlite+aiosqlite://")
        session_factory = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        user_id = UUID("22222222-2222-4222-8222-222222222222")
        existing_role_id = UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
        added_role_id = UUID("0c6fd207-c64b-4b8e-8a2d-f39bbd3a3cd3")
        existing_assignment_id = UUID("11111111-1111-4111-8111-111111111111")

        async with engine.begin() as connection:
            await connection.run_sync(create_access_control_tables)

        async with session_factory() as session:
            now = datetime.now(UTC)
            session.add(
                UserRow(
                    id=user_id,
                    email="employee@example.com",
                    display_name="Employee",
                    status="active",
                    created_at=now,
                    updated_at=now,
                )
            )
            session.add_all(
                [
                    RoleRow(id=existing_role_id, name="Existing"),
                    RoleRow(id=added_role_id, name="Added"),
                ]
            )
            session.add(
                UserRoleRow(
                    id=existing_assignment_id,
                    user_id=user_id,
                    role_id=existing_role_id,
                )
            )
            await session.commit()

        repository = PostgresAccessControlRepository(session_factory)
        await repository.replace_user_roles(
            user_id,
            {existing_role_id, added_role_id},
        )

        async with session_factory() as session:
            rows = (
                await session.scalars(
                    select(UserRoleRow).where(UserRoleRow.user_id == user_id)
                )
            ).all()

        assert {row.role_id for row in rows} == {existing_role_id, added_role_id}
        assert next(
            row.id for row in rows if row.role_id == existing_role_id
        ) == existing_assignment_id
        await engine.dispose()

    asyncio.run(scenario())


def test_create_invited_user_persists_user_before_grants() -> None:
    async def scenario() -> None:
        engine = create_async_engine("sqlite+aiosqlite://")

        @event.listens_for(engine.sync_engine, "connect")
        def enable_foreign_keys(connection, record) -> None:
            connection.execute("PRAGMA foreign_keys=ON")

        session_factory = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        actor_id = UUID("11111111-1111-4111-8111-111111111111")
        user_id = UUID("22222222-2222-4222-8222-222222222222")
        role_id = UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
        customer_id = UUID("33333333-3333-4333-8333-333333333333")
        task_id = UUID("44444444-4444-4444-8444-444444444444")
        invitation_id = UUID("55555555-5555-4555-8555-555555555555")

        async with engine.begin() as connection:
            await connection.run_sync(create_access_control_tables)

        now = datetime.now(UTC)
        async with session_factory() as session:
            session.add(
                UserRow(
                    id=actor_id,
                    email="admin@example.com",
                    display_name="Admin",
                    status="active",
                    created_at=now,
                    updated_at=now,
                )
            )
            session.add(RoleRow(id=role_id, name="Invited User Role"))
            await session.commit()

        repository = PostgresAccessControlRepository(session_factory)
        await repository.create_invited_user(
            user=UserAccount(
                id=user_id,
                email="invitee@example.com",
                display_name="Invitee",
                status=AccountStatus.INVITED,
                created_at=now,
                updated_at=now,
                invited_at=now,
            ),
            invitation=UserInvitation(
                id=invitation_id,
                user_id=user_id,
                email="invitee@example.com",
                token_digest="digest",
                expires_at=now,
                created_at=now,
                created_by=actor_id,
            ),
            role_ids={role_id},
            customer_ids={customer_id},
            task_ids={task_id},
        )

        async with session_factory() as session:
            user = await session.get(UserRow, user_id)
            invitation = await session.get(InvitationRow, invitation_id)
            role_grants = (
                await session.scalars(
                    select(UserRoleRow).where(UserRoleRow.user_id == user_id)
                )
            ).all()
            customer_grants = (
                await session.scalars(
                    select(CustomerAccessGrantRow).where(
                        CustomerAccessGrantRow.user_id == user_id
                    )
                )
            ).all()
            task_grants = (
                await session.scalars(
                    select(TaskAccessGrantRow).where(
                        TaskAccessGrantRow.user_id == user_id
                    )
                )
            ).all()

        assert user is not None
        assert invitation is not None
        assert [grant.role_id for grant in role_grants] == [role_id]
        assert [grant.customer_id for grant in customer_grants] == [customer_id]
        assert [grant.task_id for grant in task_grants] == [task_id]
        await engine.dispose()

    asyncio.run(scenario())


def test_role_member_count_and_delete_role() -> None:
    async def scenario() -> None:
        engine = create_async_engine("sqlite+aiosqlite://")
        session_factory = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        used_role_id = UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
        unused_role_id = UUID("0c6fd207-c64b-4b8e-8a2d-f39bbd3a3cd3")
        user_id = UUID("22222222-2222-4222-8222-222222222222")

        async with engine.begin() as connection:
            await connection.run_sync(create_access_control_tables)

        async with session_factory() as session:
            now = datetime.now(UTC)
            session.add(
                UserRow(
                    id=user_id,
                    email="employee@example.com",
                    display_name="Employee",
                    status="active",
                    created_at=now,
                    updated_at=now,
                )
            )
            session.add_all(
                [
                    RoleRow(id=used_role_id, name="Used"),
                    RoleRow(id=unused_role_id, name="Unused"),
                ]
            )
            session.add(UserRoleRow(user_id=user_id, role_id=used_role_id))
            await session.commit()

        repository = PostgresAccessControlRepository(session_factory)

        assert await repository.role_member_count(used_role_id) == 1
        assert await repository.role_member_count(unused_role_id) == 0

        await repository.delete_role(unused_role_id)

        async with session_factory() as session:
            deleted = await session.get(RoleRow, unused_role_id)
            used = await session.get(RoleRow, used_role_id)

        assert deleted is None
        assert used is not None
        await engine.dispose()

    asyncio.run(scenario())


def test_delete_role_removes_assignments_for_deleted_users() -> None:
    async def scenario() -> None:
        engine = create_async_engine("sqlite+aiosqlite://")
        session_factory = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        role_id = UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
        user_id = UUID("22222222-2222-4222-8222-222222222222")

        async with engine.begin() as connection:
            await connection.run_sync(create_access_control_tables)

        async with session_factory() as session:
            now = datetime.now(UTC)
            session.add(
                UserRow(
                    id=user_id,
                    email="deleted@example.com",
                    display_name="Deleted",
                    status="disabled",
                    created_at=now,
                    updated_at=now,
                    deleted_at=now,
                )
            )
            session.add(RoleRow(id=role_id, name="Unused By Active Users"))
            session.add(UserRoleRow(user_id=user_id, role_id=role_id))
            await session.commit()

        repository = PostgresAccessControlRepository(session_factory)

        assert await repository.role_member_count(role_id) == 0

        await repository.delete_role(role_id)

        async with session_factory() as session:
            role = await session.get(RoleRow, role_id)
            assignments = (
                await session.scalars(
                    select(UserRoleRow).where(UserRoleRow.role_id == role_id)
                )
            ).all()

        assert role is None
        assert assignments == []
        await engine.dispose()

    asyncio.run(scenario())
