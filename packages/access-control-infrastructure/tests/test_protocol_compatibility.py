from younilab_access_control_application import AccessControlRepository
from younilab_access_control_infrastructure import (
    MemoryAccessControlRepository,
    PostgresAccessControlRepository,
)


def test_memory_repository_implements_access_control_repository() -> None:
    assert isinstance(MemoryAccessControlRepository(), AccessControlRepository)


def test_postgres_repository_implements_access_control_repository() -> None:
    repository = PostgresAccessControlRepository(None)  # type: ignore[arg-type]

    assert isinstance(repository, AccessControlRepository)
