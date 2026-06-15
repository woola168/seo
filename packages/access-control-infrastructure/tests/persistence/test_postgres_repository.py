import asyncio
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlmodel import SQLModel

from younilab_access_control_infrastructure.persistence.postgres.models import (
    RoleRow,
    UserRoleRow,
    UserRow,
)
from younilab_access_control_infrastructure.persistence.postgres.repository import (
    PostgresAccessControlRepository,
)


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
            await connection.run_sync(SQLModel.metadata.create_all)

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
