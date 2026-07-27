import os
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, cast

from younilab_provider_request_audit import PostgresProviderRequestRecorder
from younilab_seo.geo_analysis.application import (
    AnalyzeRunResult,
    CitationNormalizationPersistence,
    Clock,
    EvidenceTextRepairer,
    KMindHubTaskMappingPersistence,
    KMindHubWorkspaceClient,
    KMindHubWorkspaceMappingPersistence,
    ManageKMindHubWorkspaceMapping,
    NormalizeRunResultCitations,
    ProcessQueryRunJobMessage,
    RunExecutionPersistence,
    SemanticAnalysisPersistence,
    TrackingRunClient,
)
from younilab_seo.geo_analysis.infrastructure import (
    GeminiEvidenceTextRepairer,
    GeminiEvidenceTextRepairSettings,
    HttpCitationUrlResolver,
    KMindHubGeoRunResultAnalyzer,
)
from younilab_seo.geo_analysis.infrastructure.persistence.postgres import (
    build_postgres_repository,
)

_TRACKING_RUN_TIMEOUT_SECONDS = 210.0


@dataclass(frozen=True)
class GeoAnalysisWorkerDependencies:
    processor: ProcessQueryRunJobMessage
    consumer: Any
    analyze_run_result: AnalyzeRunResult
    normalize_run_result_citations: NormalizeRunResultCitations
    citation_url_resolver: HttpCitationUrlResolver
    evidence_text_repairer: EvidenceTextRepairer
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
    repository: object | None = None,
    tracking_client: TrackingRunClient | None = None,
    kmindhub_client: KMindHubWorkspaceClient | None = None,
    evidence_text_repairer: EvidenceTextRepairer | None = None,
    consumer: Any | None = None,
    clock: Clock | None = None,
    provider: str | None = None,
) -> GeoAnalysisWorkerDependencies:
    active_provider = provider or os.getenv("GEO_ANALYSIS_WORKER_PROVIDER", "gemini")
    active_repository = repository or _build_repository()
    active_tracking_client = tracking_client or _build_tracking_client()
    active_kmindhub_client = kmindhub_client or _build_kmindhub_client()
    active_evidence_text_repairer = (
        evidence_text_repairer or _build_evidence_text_repairer()
    )
    citation_url_resolver = _build_citation_url_resolver()
    active_consumer = consumer or _build_consumer(active_provider)
    active_clock = clock or SystemClock()
    workspace_mapping_persistence = cast(
        KMindHubWorkspaceMappingPersistence,
        active_repository,
    )
    task_mapping_persistence = cast(
        KMindHubTaskMappingPersistence,
        active_repository,
    )
    semantic_persistence = cast(SemanticAnalysisPersistence, active_repository)
    citation_persistence = cast(
        CitationNormalizationPersistence,
        active_repository,
    )
    execution_persistence = cast(RunExecutionPersistence, active_repository)
    kmindhub_workspace_resolver = ManageKMindHubWorkspaceMapping(
        workspace_mapping_persistence,
        active_kmindhub_client,
    )
    semantic_analyzer = KMindHubGeoRunResultAnalyzer(
        task_mapping_persistence,
        kmindhub_workspace_resolver,
        active_kmindhub_client,
        debug_payloads=_env_bool("GEO_KMINDHUB_DEBUG_PAYLOADS"),
        evidence_text_repairer=active_evidence_text_repairer,
    )
    analyze_run_result = AnalyzeRunResult(
        semantic_persistence,
        semantic_analyzer,
        active_clock,
    )
    normalize_run_result_citations = NormalizeRunResultCitations(
        citation_persistence,
        active_clock,
        url_resolver=citation_url_resolver,
    )
    return GeoAnalysisWorkerDependencies(
        processor=ProcessQueryRunJobMessage(
            repository=execution_persistence,
            tracking_client=active_tracking_client,
            clock=active_clock,
            supported_provider=active_provider,
            analyze_run_result=analyze_run_result,
            normalize_run_result_citations=normalize_run_result_citations,
        ),
        consumer=active_consumer,
        analyze_run_result=analyze_run_result,
        normalize_run_result_citations=normalize_run_result_citations,
        citation_url_resolver=citation_url_resolver,
        evidence_text_repairer=active_evidence_text_repairer,
        kmindhub_workspace_resolver=kmindhub_workspace_resolver,
        kmindhub_workspace_client=active_kmindhub_client,
        closeables=(
            active_tracking_client,
            active_kmindhub_client,
            citation_url_resolver,
            active_evidence_text_repairer,
        ),
    )


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC).replace(microsecond=0)


def _build_repository() -> object:
    return build_postgres_repository(_required_env("GEO_ANALYSIS_DATABASE_URL"))


def _build_tracking_client() -> TrackingRunClient:
    from younilab_seo.geo_analysis.infrastructure.tracking import HttpTrackingRunClient

    return HttpTrackingRunClient(
        base_url=os.getenv("GEO_TRACKING_BASE_URL", "http://geo-tracking-api:8003"),
        timeout_seconds=_TRACKING_RUN_TIMEOUT_SECONDS,
    )


def _build_kmindhub_client() -> KMindHubWorkspaceClient:
    from younilab_seo.geo_analysis.infrastructure import HttpKMindHubWorkspaceClient

    return HttpKMindHubWorkspaceClient(
        base_url=os.getenv(
            "KMINDHUB_INSIGHT_BASE_URL", "http://kmindhub-insight-api:8000"
        ),
        timeout_seconds=float(os.getenv("KMINDHUB_INSIGHT_TIMEOUT_SECONDS", "30")),
        debug_payloads=_env_bool("GEO_KMINDHUB_DEBUG_PAYLOADS"),
    )


def _build_evidence_text_repairer() -> EvidenceTextRepairer:
    recorder = PostgresProviderRequestRecorder(
        _required_env("GEO_ANALYSIS_DATABASE_URL")
    )
    return GeminiEvidenceTextRepairer(
        GeminiEvidenceTextRepairSettings.from_environment(),
        recorder,
        "geo-analysis-worker",
    )


def _build_citation_url_resolver() -> HttpCitationUrlResolver:
    return HttpCitationUrlResolver(
        timeout_seconds=float(
            os.getenv("GEO_CITATION_URL_RESOLVE_TIMEOUT_SECONDS", "5")
        ),
        max_redirects=int(os.getenv("GEO_CITATION_URL_RESOLVE_MAX_REDIRECTS", "5")),
    )


def _build_consumer(provider: str) -> Any:
    from younilab_seo.geo_analysis.infrastructure.messaging import (
        RabbitMqQueryRunJobConsumer,
    )

    queue_prefix = os.getenv(
        "GEO_ANALYSIS_RABBITMQ_QUEUE_PREFIX",
        "geo.query-runs",
    )
    return RabbitMqQueryRunJobConsumer(
        url=_required_env("GEO_ANALYSIS_RABBITMQ_URL"),
        queue_name=os.getenv(
            "GEO_ANALYSIS_WORKER_QUEUE",
            f"{queue_prefix}.{provider}",
        ),
        prefetch_count=int(os.getenv("GEO_ANALYSIS_WORKER_PREFETCH", "1")),
    )


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} is required")
    return value


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}
