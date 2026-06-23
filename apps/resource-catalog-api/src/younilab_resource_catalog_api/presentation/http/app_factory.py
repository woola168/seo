from fastapi import FastAPI

from younilab_resource_catalog_api.presentation.http.composition import (
    build_dependencies,
)
from younilab_resource_catalog_api.presentation.http.errors import (
    register_error_handlers,
)
from younilab_resource_catalog_api.presentation.http.routes import (
    customers_router,
    tasks_router,
)
from younilab_seo.resource_catalog.application import (
    PermissionAuthorizer,
    ResourceCatalogRepository,
)
from younilab_seo.resource_catalog.infrastructure import ResourceCatalogSettings


def create_app(
    *,
    settings: ResourceCatalogSettings | None = None,
    repository: ResourceCatalogRepository | None = None,
    authorizer: PermissionAuthorizer | None = None,
) -> FastAPI:
    dependencies = build_dependencies(
        settings=settings,
        repository=repository,
        authorizer=authorizer,
    )
    app = FastAPI(title="Younilab SEO Resource Catalog API", version="0.1.0")
    app.state.catalog = dependencies.catalog
    app.state.authorizer = dependencies.authorizer

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(customers_router)
    app.include_router(tasks_router)
    register_error_handlers(app)
    return app
