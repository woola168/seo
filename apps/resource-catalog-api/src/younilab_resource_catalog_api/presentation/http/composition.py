from dataclasses import dataclass

from younilab_seo.resource_catalog.application import (
    PermissionAuthorizer,
    ResourceCatalogRepository,
    ResourceCatalogService,
)
from younilab_seo.resource_catalog.infrastructure import (
    AccessControlAuthorizer,
    MemoryResourceCatalogRepository,
    ResourceCatalogSettings,
    SystemClock,
    UuidGenerator,
    build_postgres_repository,
)


@dataclass(frozen=True)
class ResourceCatalogApiDependencies:
    catalog: ResourceCatalogService
    authorizer: PermissionAuthorizer


def build_dependencies(
    *,
    settings: ResourceCatalogSettings | None = None,
    repository: ResourceCatalogRepository | None = None,
    authorizer: PermissionAuthorizer | None = None,
) -> ResourceCatalogApiDependencies:
    resolved_settings = settings or ResourceCatalogSettings()
    resolved_repository = repository or _repository(resolved_settings)
    return ResourceCatalogApiDependencies(
        catalog=ResourceCatalogService(
            resolved_repository,
            SystemClock(),
            UuidGenerator(),
        ),
        authorizer=authorizer
        or AccessControlAuthorizer(resolved_settings.access_control_url),
    )


def _repository(settings: ResourceCatalogSettings) -> ResourceCatalogRepository:
    if settings.database_url:
        return build_postgres_repository(settings.database_url)
    if settings.is_production:
        raise RuntimeError("RESOURCE_CATALOG_DATABASE_URL is required in production")
    return MemoryResourceCatalogRepository()
