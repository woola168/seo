from fastapi import FastAPI

from younilab_geo_analysis_api.presentation.http.errors import register_error_handlers
from younilab_geo_analysis_api.presentation.http.routes import router
from younilab_geo_analysis_api.presentation.http.store import GeoApiStore


def create_app(*, store: GeoApiStore | None = None) -> FastAPI:
    app = FastAPI(title="Younilab SEO GEO Analysis API", version="0.1.0")
    app.state.geo_store = store or GeoApiStore()
    register_error_handlers(app)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(router)
    return app
