from datetime import UTC, datetime
from uuid import UUID

import pytest

from younilab_access_control_api.presentation.composition import build_dependencies
from younilab_access_control_infrastructure import (
    AccessControlSettings,
    MemoryAccessControlRepository,
    MemoryNotificationPublisher,
    PostgresOutboxPublisher,
)


class FakePasswordHasher:
    def hash(self, password: str) -> str:
        return password

    def verify(self, password: str, password_hash: str) -> bool:
        return password == password_hash


class FakeTokenProvider:
    pass


class FakeClock:
    def now(self) -> datetime:
        return datetime(2026, 6, 11, tzinfo=UTC)


class FakeIdGenerator:
    def new_id(self) -> UUID:
        return UUID("11111111-1111-4111-8111-111111111111")


def test_build_dependencies_uses_injected_runtime_dependencies() -> None:
    repository = MemoryAccessControlRepository()
    password_hasher = FakePasswordHasher()
    token_provider = FakeTokenProvider()
    clock = FakeClock()
    id_generator = FakeIdGenerator()

    dependencies = build_dependencies(
        settings=AccessControlSettings(environment="development"),
        repository=repository,
        password_hasher=password_hasher,
        token_provider=token_provider,
        clock=clock,
        id_generator=id_generator,
    )

    assert dependencies.repository is repository
    assert dependencies.token_provider is token_provider
    assert dependencies.clock is clock
    assert dependencies.id_generator is id_generator
    assert dependencies.authentication._repository is repository
    assert dependencies.authentication._password_hasher is password_hasher
    assert dependencies.authentication._token_provider is token_provider
    assert dependencies.authentication._clock is clock
    assert dependencies.authentication._id_generator is id_generator
    assert dependencies.authorization._repository is repository
    assert dependencies.management._repository is repository
    assert dependencies.secure_cookies is False


def test_build_dependencies_uses_memory_repository_in_development() -> None:
    dependencies = build_dependencies(
        settings=AccessControlSettings(environment="development", database_url=None),
        token_provider=FakeTokenProvider(),
    )

    assert isinstance(dependencies.repository, MemoryAccessControlRepository)
    assert isinstance(dependencies.notifications, MemoryNotificationPublisher)


def test_build_dependencies_uses_postgres_outbox_when_database_is_configured() -> None:
    dependencies = build_dependencies(
        settings=AccessControlSettings(
            environment="development",
            database_url="sqlite+aiosqlite://",
            notification_encryption_key=None,
        ),
        token_provider=FakeTokenProvider(),
    )

    assert isinstance(dependencies.notifications, PostgresOutboxPublisher)


def test_build_dependencies_requires_database_in_production() -> None:
    with pytest.raises(
        RuntimeError,
        match="ACCESS_CONTROL_DATABASE_URL is required in production",
    ):
        build_dependencies(
            settings=AccessControlSettings(
                environment="production",
                database_url=None,
            ),
            token_provider=FakeTokenProvider(),
        )


def test_build_dependencies_requires_jwt_keys_in_production() -> None:
    with pytest.raises(
        RuntimeError,
        match="ACCESS_CONTROL_JWT_PRIVATE_KEY and ACCESS_CONTROL_JWT_PUBLIC_KEY",
    ):
        build_dependencies(
            settings=AccessControlSettings(
                environment="production",
                database_url="sqlite+aiosqlite://",
                notification_encryption_key=None,
            ),
            repository=MemoryAccessControlRepository(),
        )
