import os
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from younilab_seo.geo_analysis.application import (
    AnalyzeRunResult,
    Clock,
    GeoAnalysisRepository,
    KMindHubWorkspaceClient,
    ManageKMindHubWorkspaceMapping,
    NormalizeRunResultCitations,
    ProcessQueryRunJobMessage,
    TrackingRunClient,
)
from younilab_seo.geo_analysis.infrastructure import KMindHubGeoRunResultAnalyzer
from younilab_seo.geo_analysis.infrastructure.persistence.postgres import (
    build_postgres_repository,
)


@dataclass(frozen=True)
class GeoAnalysisWorkerDependencies:
    processor: ProcessQueryRunJobMessage
    consumer: Any
    analyze_run_result: AnalyzeRunResult
    normalize_run_result_citations: NormalizeRunResultCitations
    kmindhub_workspace_resolver: ManageKMindHubWorkspaceMapping
    kmindhub_workspace_client: KMindHubWorkspaceClient
    closeables: tuple[object, ...] = ()

    async def close(self) -> None:
        for closeable in self.closeables:
            close = getattr(closeable, "close", None)
            if close is not None:
                await close()


def build_dependencies(
    *,
    repository: GeoAnalysisRepository | None = None,
    tracking_client: TrackingRunClient | None = None,
    kmindhub_client: KMindHubWorkspaceClient | None = None,
    consumer: Any | None = None,
    clock: Clock | None = None,
    provider: str | None = None,
) -> GeoAnalysisWorkerDependencies:
    active_provider = provider or os.getenv("GEO_ANALYSIS_WORKER_PROVIDER", "gemini")
    active_repository = repository or _build_repository()
    active_tracking_client = tracking_client or _build_tracking_client()
    active_kmindhub_client = kmindhub_client or _build_kmindhub_client()
    active_consumer = consumer or _build_consumer(active_provider)
    active_clock = clock or SystemClock()
    kmindhub_workspace_resolver = ManageKMindHubWorkspaceMapping(
        active_repository,
        active_kmindhub_client,
    )
    semantic_analyzer = KMindHubGeoRunResultAnalyzer(
        active_repository,
        kmindhub_workspace_resolver,
        active_kmindhub_client,
    )
    analyze_run_result = AnalyzeRunResult(
        active_repository,
        semantic_analyzer,
        active_clock,
    )
    normalize_run_result_citations = NormalizeRunResultCitations(
        active_repository,
        active_clock,
    )
    return GeoAnalysisWorkerDependencies(
        processor=ProcessQueryRunJobMessage(
            repository=active_repository,
            tracking_client=active_tracking_client,
            clock=active_clock,
            supported_provider=active_provider,
            analyze_run_result=analyze_run_result,
            normalize_run_result_citations=normalize_run_result_citations,
        ),
        consumer=active_consumer,
        analyze_run_result=analyze_run_result,
        normalize_run_result_citations=normalize_run_result_citations,
        kmindhub_workspace_resolver=kmindhub_workspace_resolver,
        kmindhub_workspace_client=active_kmindhub_client,
        closeables=(active_tracking_client, active_kmindhub_client),
    )


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC).replace(microsecond=0)


def _build_repository() -> GeoAnalysisRepository:
    return build_postgres_repository(_required_env("GEO_ANALYSIS_DATABASE_URL"))


def _build_tracking_client() -> TrackingRunClient:
    from younilab_seo.geo_analysis.infrastructure.tracking import HttpTrackingRunClient

    return HttpTrackingRunClient(
        base_url=os.getenv("GEO_TRACKING_BASE_URL", "http://geo-tracking-api:8003"),
        timeout_seconds=float(os.getenv("GEO_TRACKING_TIMEOUT_SECONDS", "60")),
    )


def _build_kmindhub_client() -> KMindHubWorkspaceClient:
    from younilab_seo.geo_analysis.infrastructure import HttpKMindHubWorkspaceClient

    return HttpKMindHubWorkspaceClient(
        base_url=os.getenv("KMINDHUB_INSIGHT_BASE_URL", "http://kmindhub-insight-api:8000"),
        timeout_seconds=float(os.getenv("KMINDHUB_INSIGHT_TIMEOUT_SECONDS", "30")),
    )


def _build_consumer(provider: str) -> Any:
    from younilab_seo.geo_analysis.infrastructure.messaging import (
        RabbitMqQueryRunJobConsumer,
    )

    return RabbitMqQueryRunJobConsumer(
        url=_required_env("GEO_ANALYSIS_RABBITMQ_URL"),
        queue_name=os.getenv(
            "GEO_ANALYSIS_WORKER_QUEUE",
            f"{os.getenv('GEO_ANALYSIS_RABBITMQ_QUEUE_PREFIX', 'geo.query-runs')}.{provider}",
        ),
        prefetch_count=int(os.getenv("GEO_ANALYSIS_WORKER_PREFETCH", "1")),
    )


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} is required")
    return value
