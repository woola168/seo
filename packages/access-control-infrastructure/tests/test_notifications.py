import asyncio
import json
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlmodel import SQLModel

from younilab_access_control_application import Notification
from younilab_access_control_infrastructure import PostgresOutboxPublisher
from younilab_access_control_infrastructure.persistence.postgres.models import (
    NotificationOutboxRow,
)


def test_postgres_outbox_publisher_stores_plain_json_payload() -> None:
    async def scenario() -> None:
        engine = create_async_engine("sqlite+aiosqlite://")
        session_factory = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        async with engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)

        publisher = PostgresOutboxPublisher(session_factory)
        await publisher.publish(
            Notification(
                id=UUID("11111111-1111-4111-8111-111111111111"),
                recipient="invitee@example.com",
                template="user-invitation",
                parameters={
                    "displayName": "測試帳號",
                    "invitationUrl": (
                        "http://127.0.0.1:5173/accept-invitation?token=demo"
                    ),
                },
                created_at=datetime.now(UTC),
            )
        )

        async with session_factory() as session:
            row = await session.scalar(select(NotificationOutboxRow))

        assert row is not None
        assert row.recipient == "invitee@example.com"
        assert row.template == "user-invitation"
        assert row.status == "pending"
        payload = json.loads(row.payload_ciphertext)
        assert payload == {
            "displayName": "測試帳號",
            "invitationUrl": (
                "http://127.0.0.1:5173/accept-invitation?token=demo"
            ),
        }
        await engine.dispose()

    asyncio.run(scenario())
