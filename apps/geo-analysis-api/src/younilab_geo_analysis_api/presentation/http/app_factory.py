from fastapi import FastAPI

from younilab_geo_analysis_api.presentation.http.composition import build_dependencies
from younilab_geo_analysis_api.presentation.http.errors import register_error_handlers
from younilab_geo_analysis_api.presentation.http.routes import router
from younilab_seo.geo_analysis.application import Clock, GeoAnalysisRepository


def create_app(
    *,
    repository: GeoAnalysisRepository | None = None,
    clock: Clock | None = None,
) -> FastAPI:
    app = FastAPI(title="Younilab SEO GEO Analysis API", version="0.1.0")
    dependencies = build_dependencies(repository=repository, clock=clock)
    app.state.geo_repository = dependencies.repository
    app.state.manage_geo_setup = dependencies.manage_geo_setup
    app.state.manage_query_run_jobs = dependencies.manage_query_run_jobs
    register_error_handlers(app)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(router)
    return app
