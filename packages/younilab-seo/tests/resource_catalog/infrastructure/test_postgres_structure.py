from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

from younilab_seo.resource_catalog.application import (
    CustomerRepository,
    ResourceCatalogRepository,
    TaskRepository,
)
from younilab_seo.resource_catalog.infrastructure import (
    PostgresResourceCatalogRepository,
)
from younilab_seo.resource_catalog.infrastructure.persistence.postgres import (
    CustomerRow,
    TaskRow,
    build_postgres_session_factory,
)


def test_postgres_repository_implements_application_ports() -> None:
    repository = PostgresResourceCatalogRepository(
        build_postgres_session_factory(
            "postgresql+asyncpg://user:pass@localhost/resource_catalog"
        )
    )

    assert isinstance(repository, CustomerRepository)
    assert isinstance(repository, TaskRepository)
    assert isinstance(repository, ResourceCatalogRepository)


def test_postgres_rows_preserve_uuid_and_timezone_types() -> None:
    customer_ddl = str(
        CreateTable(CustomerRow.__table__).compile(dialect=postgresql.dialect())
    )
    task_ddl = str(
        CreateTable(TaskRow.__table__).compile(dialect=postgresql.dialect())
    )

    assert "id UUID NOT NULL" in customer_ddl
    assert "created_at TIMESTAMP WITH TIME ZONE NOT NULL" in customer_ddl
    assert "customer_id UUID NOT NULL" in task_ddl
    assert "TIMESTAMP WITHOUT TIME ZONE" not in customer_ddl + task_ddl
