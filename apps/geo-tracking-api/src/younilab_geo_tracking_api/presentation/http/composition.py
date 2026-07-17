from collections.abc import Mapping
from dataclasses import dataclass

from younilab_geo_tracking_application import (
    AnswerProvider,
    ProjectDiscoveryProvider,
    ProjectDiscoveryService,
    QueryGenerationProvider,
    QueryGenerationService,
    QueryResearchProvider,
    QueryResearchService,
    RunEngineService,
)
from younilab_geo_tracking_domain import ProviderCode
from younilab_provider_request_audit import (
    PostgresProviderRequestRecorder,
    ProviderRequestRecorder,
    UnconfiguredProviderRequestRecorder,
)
from younilab_geo_tracking_infrastructure import (
    GeminiProjectDiscoveryProvider,
    GeoTrackingSettings,
    SystemClock,
    UuidGenerator,
    build_answer_providers,
    build_query_generation_providers,
    build_query_research_providers,
)


@dataclass(frozen=True)
class GeoTrackingApiDependencies:
    project_discovery: ProjectDiscoveryService
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
    project_discovery_provider: ProjectDiscoveryProvider | None = None,
    provider_request_recorder: ProviderRequestRecorder | None = None,
) -> GeoTrackingApiDependencies:
    id_generator = UuidGenerator()
    resolved_settings = settings or GeoTrackingSettings()
    resolved_recorder = provider_request_recorder or _build_provider_request_recorder()
    resolved_providers = (
        dict(answer_providers)
        if answer_providers is not None
        else build_answer_providers(resolved_settings, resolved_recorder)
    )
    if answer_provider is not None:
        resolved_providers = {
            provider_code: answer_provider for provider_code in ProviderCode
        }
    resolved_query_research_providers = (
        dict(query_research_providers)
        if query_research_providers is not None
        else build_query_research_providers(resolved_settings, resolved_recorder)
    )
    resolved_query_generation_providers = (
        dict(query_generation_providers)
        if query_generation_providers is not None
        else build_query_generation_providers(resolved_settings, resolved_recorder)
    )
    resolved_project_discovery_provider = (
        project_discovery_provider
        if project_discovery_provider is not None
        else GeminiProjectDiscoveryProvider(resolved_settings, resolved_recorder)
    )
    return GeoTrackingApiDependencies(
        project_discovery=ProjectDiscoveryService(
            resolved_project_discovery_provider,
        ),
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
                    + [resolved_project_discovery_provider]
                    + [resolved_recorder]
                )
            }.values()
        ),
    )


def _build_provider_request_recorder() -> ProviderRequestRecorder:
    import os

    database_url = os.getenv("GEO_ANALYSIS_DATABASE_URL")
    if not database_url:
        return UnconfiguredProviderRequestRecorder()
    return PostgresProviderRequestRecorder(database_url)
