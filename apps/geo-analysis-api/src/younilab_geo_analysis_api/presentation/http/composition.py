import os
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import cast

from younilab_provider_request_audit import (
    PostgresProviderRequestRecorder,
    UnconfiguredProviderRequestRecorder,
)
from younilab_seo.geo_analysis.application import (
    AnalyzeRunResult,
    BuildGeoMetricFormulaSource,
    CalculateGeoReportMetrics,
    Clock,
    DispatchQueryRunJob,
    EntityCatalogPersistence,
    EvidenceTextRepairer,
    GetGeoDashboardReport,
    GetGeoOverviewReport,
    KMindHubTaskMappingPersistence,
    KMindHubWorkspaceClient,
    KMindHubWorkspaceMappingPersistence,
    ListGeoOverviewResponses,
    ManageGeoSetup,
    ManageKMindHubWorkspaceMapping,
    ManageQueryPlanning,
    ManageQueryRunJobs,
    MessagePublisher,
    MetricsReadPersistence,
    OverviewReadPersistence,
    PermissionAuthorizer,
    ProjectSetupPersistence,
    QueryCatalogPersistence,
    QueryPlanningClient,
    QueryPlanningPersistence,
    ReceiveExternalRunCallback,
    ResourceCatalogCustomerReader,
    ResourceCatalogReferenceVerifier,
    RunCallbackPersistence,
    RunDispatchPersistence,
    RunJobManagementPersistence,
    SemanticAnalysisPersistence,
)
from younilab_seo.geo_analysis.infrastructure import (
    AccessControlAuthorizer,
    GeminiEvidenceTextRepairer,
    GeminiEvidenceTextRepairSettings,
    KMindHubGeoRunResultAnalyzer,
    ResourceCatalogHttpReferenceVerifier,
)
from younilab_seo.geo_analysis.infrastructure.persistence.postgres import (
    build_postgres_repository,
)

from younilab_geo_analysis_api.presentation.http.store import GeoApiStore


@dataclass(frozen=True)
class GeoAnalysisApiDependencies:
    repository: object
    authorizer: PermissionAuthorizer
    manage_geo_setup: ManageGeoSetup
    manage_kmindhub_workspace_mapping: ManageKMindHubWorkspaceMapping
    manage_query_planning: ManageQueryPlanning
    manage_query_run_jobs: ManageQueryRunJobs
    analyze_run_result: AnalyzeRunResult
    evidence_text_repairer: EvidenceTextRepairer
    calculate_geo_report_metrics: CalculateGeoReportMetrics
    get_geo_dashboard_report: GetGeoDashboardReport
    get_geo_overview_report: GetGeoOverviewReport
    list_geo_overview_responses: ListGeoOverviewResponses
    dispatch_query_run_job: DispatchQueryRunJob | None
    receive_external_run_callback: ReceiveExternalRunCallback
    callback_base_url: str
    closeables: tuple[object, ...] = ()

    async def close(self) -> None:
        for closeable in self.closeables:
            close = getattr(closeable, "close", None)
            if close is not None:
                await close()


def build_dependencies(
    *,
    repository: object | None = None,
    clock: Clock | None = None,
    publisher: MessagePublisher | None = None,
    planning_client: QueryPlanningClient | None = None,
    kmindhub_client: KMindHubWorkspaceClient | None = None,
    evidence_text_repairer: EvidenceTextRepairer | None = None,
    authorizer: PermissionAuthorizer | None = None,
    reference_verifier: ResourceCatalogReferenceVerifier | None = None,
    customer_reader: ResourceCatalogCustomerReader | None = None,
    callback_base_url: str | None = None,
) -> GeoAnalysisApiDependencies:
    active_repository = repository or _build_repository()
    active_clock = clock or SystemClock()
    active_publisher = publisher or _build_publisher()
    active_planning_client = planning_client or _build_planning_client()
    active_kmindhub_client = kmindhub_client or _build_kmindhub_client()
    active_evidence_text_repairer = (
        evidence_text_repairer or _build_evidence_text_repairer()
    )
    active_authorizer = authorizer or _build_authorizer()
    active_reference_verifier = reference_verifier or _build_reference_verifier()
    active_customer_reader = customer_reader
    if active_customer_reader is None and hasattr(
        active_reference_verifier, "list_customer_names"
    ):
        active_customer_reader = active_reference_verifier
    project_persistence = cast(ProjectSetupPersistence, active_repository)
    entity_persistence = cast(EntityCatalogPersistence, active_repository)
    query_catalog_persistence = cast(QueryCatalogPersistence, active_repository)
    workspace_mapping_persistence = cast(
        KMindHubWorkspaceMappingPersistence,
        active_repository,
    )
    task_mapping_persistence = cast(
        KMindHubTaskMappingPersistence,
        active_repository,
    )
    metrics_persistence = cast(MetricsReadPersistence, active_repository)
    planning_persistence = cast(QueryPlanningPersistence, active_repository)
    job_management_persistence = cast(
        RunJobManagementPersistence,
        active_repository,
    )
    semantic_persistence = cast(SemanticAnalysisPersistence, active_repository)
    overview_persistence = cast(OverviewReadPersistence, active_repository)
    dispatch_persistence = cast(RunDispatchPersistence, active_repository)
    callback_persistence = cast(RunCallbackPersistence, active_repository)
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
    metric_source_builder = BuildGeoMetricFormulaSource(metrics_persistence)
    closeables = tuple(
        item
        for item in (
            active_publisher,
            active_planning_client,
            active_kmindhub_client,
            active_evidence_text_repairer,
        )
        if item is not None
    )
    return GeoAnalysisApiDependencies(
        repository=active_repository,
        authorizer=active_authorizer,
        manage_geo_setup=ManageGeoSetup(
            project_persistence,
            active_reference_verifier,
            active_customer_reader,
            entity_persistence=entity_persistence,
            query_catalog_persistence=query_catalog_persistence,
        ),
        manage_kmindhub_workspace_mapping=kmindhub_workspace_resolver,
        manage_query_planning=ManageQueryPlanning(
            planning_persistence,
            active_planning_client,
            active_clock,
        ),
        manage_query_run_jobs=ManageQueryRunJobs(
            job_management_persistence,
            active_clock,
        ),
        analyze_run_result=AnalyzeRunResult(
            semantic_persistence,
            semantic_analyzer,
            active_clock,
        ),
        evidence_text_repairer=active_evidence_text_repairer,
        calculate_geo_report_metrics=CalculateGeoReportMetrics(
            metric_source_builder,
        ),
        get_geo_dashboard_report=GetGeoDashboardReport(
            metric_source_builder,
        ),
        get_geo_overview_report=GetGeoOverviewReport(
            overview_persistence,
            metric_source_builder,
            active_clock,
        ),
        list_geo_overview_responses=ListGeoOverviewResponses(
            overview_persistence,
            metric_source_builder,
        ),
        dispatch_query_run_job=(
            DispatchQueryRunJob(dispatch_persistence, active_publisher, active_clock)
            if active_publisher is not None
            else None
        ),
        receive_external_run_callback=ReceiveExternalRunCallback(
            callback_persistence,
            active_clock,
        ),
        callback_base_url=(
            callback_base_url
            or os.getenv("GEO_ANALYSIS_CALLBACK_BASE_URL")
            or "http://geo-analysis-api:8002"
        ),
        closeables=closeables,
    )


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC).replace(microsecond=0)


def _build_repository() -> object:
    database_url = os.getenv("GEO_ANALYSIS_DATABASE_URL")
    if database_url:
        return build_postgres_repository(database_url)
    return GeoApiStore()


def _build_publisher() -> MessagePublisher | None:
    if os.getenv("GEO_ANALYSIS_PUBLISHER_BACKEND", "").lower() != "rabbitmq":
        return None
    url = os.getenv("GEO_ANALYSIS_RABBITMQ_URL")
    if not url:
        return None
    from younilab_seo.geo_analysis.infrastructure.messaging import (
        RabbitMqMessagePublisher,
    )

    return RabbitMqMessagePublisher(
        url=url,
        exchange_name=os.getenv(
            "GEO_ANALYSIS_RABBITMQ_EXCHANGE",
            "geo.query-runs",
        ),
        queue_prefix=os.getenv(
            "GEO_ANALYSIS_RABBITMQ_QUEUE_PREFIX",
            "geo.query-runs",
        ),
        routing_key_prefix=os.getenv(
            "GEO_ANALYSIS_RABBITMQ_ROUTING_KEY_PREFIX",
            "geo.query-runs",
        ),
    )


def _build_planning_client() -> QueryPlanningClient:
    from younilab_seo.geo_analysis.infrastructure.tracking import HttpTrackingRunClient

    return HttpTrackingRunClient(
        base_url=os.getenv("GEO_TRACKING_BASE_URL", "http://geo-tracking-api:8003"),
        timeout_seconds=float(os.getenv("GEO_TRACKING_TIMEOUT_SECONDS", "60")),
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
    database_url = os.getenv("GEO_ANALYSIS_DATABASE_URL")
    recorder = (
        PostgresProviderRequestRecorder(database_url)
        if database_url
        else UnconfiguredProviderRequestRecorder()
    )
    return GeminiEvidenceTextRepairer(
        GeminiEvidenceTextRepairSettings.from_environment(),
        recorder,
        "geo-analysis-api",
    )


def _build_authorizer() -> PermissionAuthorizer:
    return AccessControlAuthorizer(
        os.getenv("GEO_ANALYSIS_ACCESS_CONTROL_URL", "http://access-control-api:8000")
    )


def _build_reference_verifier() -> ResourceCatalogReferenceVerifier:
    return ResourceCatalogHttpReferenceVerifier(
        os.getenv(
            "GEO_ANALYSIS_RESOURCE_CATALOG_URL",
            "http://resource-catalog-api:8001",
        )
    )


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}
