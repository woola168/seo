from collections.abc import Mapping
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from younilab_geo_tracking_application import (
    AnswerProvider,
    QueryGenerationProvider,
    QueryResearchProvider,
)
from younilab_geo_tracking_domain import ProviderCode
from younilab_geo_tracking_infrastructure import GeoTrackingSettings

from younilab_geo_tracking_api.presentation.http.composition import (
    build_dependencies,
)
from younilab_geo_tracking_api.presentation.http.routes import router


def create_app(
    *,
    settings: GeoTrackingSettings | None = None,
    answer_provider: AnswerProvider | None = None,
    answer_providers: Mapping[ProviderCode, AnswerProvider] | None = None,
    query_generation_providers: (
        Mapping[ProviderCode, QueryGenerationProvider] | None
    ) = None,
    query_research_providers: Mapping[ProviderCode, QueryResearchProvider]
    | None = None,
) -> FastAPI:
    dependencies = build_dependencies(
        settings=settings,
        answer_provider=answer_provider,
        answer_providers=answer_providers,
        query_generation_providers=query_generation_providers,
        query_research_providers=query_research_providers,
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        try:
            yield
        finally:
            await app.state.geo_tracking_dependencies.close()

    app = FastAPI(
        title="Younilab SEO GEO Tracking API",
        version="0.1.0",
        lifespan=lifespan,
    )
    _register_cors_middleware(app)
    app.state.query_generation = dependencies.query_generation
    app.state.query_research = dependencies.query_research
    app.state.run_engine = dependencies.run_engine
    app.state.geo_tracking_dependencies = dependencies

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(router)
    return app


def _register_cors_middleware(app: FastAPI) -> None:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://127.0.0.1:5173",
            "http://localhost:5173",
        ],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )
