from collections.abc import Mapping
from dataclasses import dataclass

from younilab_geo_tracking_application import (
    AnswerProvider,
    QueryGenerationProvider,
    QueryGenerationService,
    QueryResearchProvider,
    QueryResearchService,
    RunEngineService,
)
from younilab_geo_tracking_domain import ProviderCode
from younilab_geo_tracking_infrastructure import (
    GeoTrackingSettings,
    SystemClock,
    UuidGenerator,
    build_answer_providers,
    build_query_generation_providers,
    build_query_research_providers,
)


@dataclass(frozen=True)
class GeoTrackingApiDependencies:
    query_generation: QueryGenerationService
    query_research: QueryResearchService
    run_engine: RunEngineService
    closeables: tuple[object, ...] = ()

    async def close(self) -> None:
        for closeable in self.closeables:
            close = getattr(closeable, "close", None)
            if close is not None:
                await close()


def build_dependencies(
    *,
    settings: GeoTrackingSettings | None = None,
    answer_provider: AnswerProvider | None = None,
    answer_providers: Mapping[ProviderCode, AnswerProvider] | None = None,
    query_generation_providers: (
        Mapping[ProviderCode, QueryGenerationProvider] | None
    ) = None,
    query_research_providers: Mapping[ProviderCode, QueryResearchProvider]
    | None = None,
) -> GeoTrackingApiDependencies:
    id_generator = UuidGenerator()
    resolved_settings = settings or GeoTrackingSettings()
    resolved_providers = (
        dict(answer_providers)
        if answer_providers is not None
        else build_answer_providers(resolved_settings)
    )
    if answer_provider is not None:
        resolved_providers = {
            provider_code: answer_provider for provider_code in ProviderCode
        }
    resolved_query_research_providers = (
        dict(query_research_providers)
        if query_research_providers is not None
        else build_query_research_providers(resolved_settings)
    )
    resolved_query_generation_providers = (
        dict(query_generation_providers)
        if query_generation_providers is not None
        else build_query_generation_providers(resolved_settings)
    )
    return GeoTrackingApiDependencies(
        query_generation=QueryGenerationService(
            id_generator,
            resolved_query_generation_providers,
        ),
        query_research=QueryResearchService(
            resolved_query_research_providers,
        ),
        run_engine=RunEngineService(
            resolved_providers,
            id_generator,
            SystemClock(),
        ),
        closeables=tuple(
            {
                id(provider): provider
                for provider in (
                    list(resolved_providers.values())
                    + list(resolved_query_research_providers.values())
                    + list(resolved_query_generation_providers.values())
                )
            }.values()
        ),
    )
