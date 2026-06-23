import logging
from time import perf_counter

from fastapi import FastAPI
from fastapi import Request

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

logger = logging.getLogger("younilab.resource_catalog.http")


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
    _register_timing_middleware(app)
    return app


def _register_timing_middleware(app: FastAPI) -> None:
    @app.middleware("http")
    async def timing_middleware(request: Request, call_next):
        started_at = perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            duration_ms = (perf_counter() - started_at) * 1000
            logger.exception(
                "%s %s 500 %.2fms",
                request.method,
                request.url.path,
                duration_ms,
            )
            raise
        duration_ms = (perf_counter() - started_at) * 1000
        response.headers["X-Process-Time-Ms"] = f"{duration_ms:.2f}"
        logger.info(
            "%s %s %s %.2fms",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        return response
