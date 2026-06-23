from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from younilab_seo.access_control.infrastructure.persistence.postgres.repository import (
    PostgresAccessControlRepository,
)


def build_postgres_repository(
    database_url: str,
) -> PostgresAccessControlRepository:
    session_factory = build_postgres_session_factory(database_url)
    return PostgresAccessControlRepository(session_factory)


def build_postgres_session_factory(
    database_url: str,
) -> async_sessionmaker[AsyncSession]:
    engine = create_async_engine(database_url, pool_pre_ping=True)
    return async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
