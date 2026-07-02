from contextlib import asynccontextmanager

from fastapi import FastAPI

from younilab_geo_analysis_api.presentation.http.composition import build_dependencies
from younilab_geo_analysis_api.presentation.http.errors import register_error_handlers
from younilab_geo_analysis_api.presentation.http.routes import router
from younilab_seo.geo_analysis.application import (
    Clock,
    GeoAnalysisRepository,
    KMindHubWorkspaceClient,
    MessagePublisher,
    PermissionAuthorizer,
    QueryPlanningClient,
    ResourceCatalogReferenceVerifier,
)


def create_app(
    *,
    repository: GeoAnalysisRepository | None = None,
    clock: Clock | None = None,
    publisher: MessagePublisher | None = None,
    planning_client: QueryPlanningClient | None = None,
    kmindhub_client: KMindHubWorkspaceClient | None = None,
    authorizer: PermissionAuthorizer | None = None,
    reference_verifier: ResourceCatalogReferenceVerifier | None = None,
    callback_base_url: str | None = None,
) -> FastAPI:
    dependencies = build_dependencies(
        repository=repository,
        clock=clock,
        publisher=publisher,
        planning_client=planning_client,
        kmindhub_client=kmindhub_client,
        authorizer=authorizer,
        reference_verifier=reference_verifier,
        callback_base_url=callback_base_url,
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        try:
            yield
        finally:
            await app.state.geo_analysis_dependencies.close()

    app = FastAPI(
        title="Younilab SEO GEO Analysis API",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.state.geo_repository = dependencies.repository
    app.state.geo_authorizer = dependencies.authorizer
    app.state.manage_geo_setup = dependencies.manage_geo_setup
    app.state.manage_kmindhub_workspace_mapping = (
        dependencies.manage_kmindhub_workspace_mapping
    )
    app.state.manage_query_planning = dependencies.manage_query_planning
    app.state.manage_query_run_jobs = dependencies.manage_query_run_jobs
    app.state.dispatch_query_run_job = dependencies.dispatch_query_run_job
    app.state.receive_external_run_callback = dependencies.receive_external_run_callback
    app.state.geo_callback_base_url = dependencies.callback_base_url
    app.state.geo_analysis_dependencies = dependencies
    register_error_handlers(app)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(router)
    return app
