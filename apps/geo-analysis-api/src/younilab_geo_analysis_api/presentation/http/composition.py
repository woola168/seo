import os
from dataclasses import dataclass
from datetime import UTC, datetime

from younilab_geo_analysis_api.presentation.http.store import GeoApiStore
from younilab_seo.geo_analysis.application import (
    Clock,
    DispatchQueryRunJob,
    GeoAnalysisRepository,
    KMindHubWorkspaceClient,
    ManageGeoSetup,
    ManageKMindHubWorkspaceMapping,
    ManageQueryPlanning,
    ManageQueryRunJobs,
    MessagePublisher,
    PermissionAuthorizer,
    QueryPlanningClient,
    ReceiveExternalRunCallback,
    ResourceCatalogReferenceVerifier,
    RunKMindHubAnalysisExtraction,
)
from younilab_seo.geo_analysis.infrastructure import (
    AccessControlAuthorizer,
    ResourceCatalogHttpReferenceVerifier,
)
from younilab_seo.geo_analysis.infrastructure.persistence.postgres import (
    build_postgres_repository,
)


@dataclass(frozen=True)
class GeoAnalysisApiDependencies:
    repository: GeoAnalysisRepository
    authorizer: PermissionAuthorizer
    manage_geo_setup: ManageGeoSetup
    manage_kmindhub_workspace_mapping: ManageKMindHubWorkspaceMapping
    manage_query_planning: ManageQueryPlanning
    manage_query_run_jobs: ManageQueryRunJobs
    run_kmindhub_analysis_extraction: RunKMindHubAnalysisExtraction
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
    repository: GeoAnalysisRepository | None = None,
    clock: Clock | None = None,
    publisher: MessagePublisher | None = None,
    planning_client: QueryPlanningClient | None = None,
    kmindhub_client: KMindHubWorkspaceClient | None = None,
    authorizer: PermissionAuthorizer | None = None,
    reference_verifier: ResourceCatalogReferenceVerifier | None = None,
    callback_base_url: str | None = None,
) -> GeoAnalysisApiDependencies:
    active_repository = repository or _build_repository()
    active_clock = clock or SystemClock()
    active_publisher = publisher or _build_publisher()
    active_planning_client = planning_client or _build_planning_client()
    active_kmindhub_client = kmindhub_client or _build_kmindhub_client()
    active_authorizer = authorizer or _build_authorizer()
    active_reference_verifier = reference_verifier or _build_reference_verifier()
    closeables = tuple(
        item
        for item in (active_publisher, active_planning_client, active_kmindhub_client)
        if item is not None
    )
    return GeoAnalysisApiDependencies(
        repository=active_repository,
        authorizer=active_authorizer,
        manage_geo_setup=ManageGeoSetup(active_repository, active_reference_verifier),
        manage_kmindhub_workspace_mapping=ManageKMindHubWorkspaceMapping(
            active_repository,
            active_kmindhub_client,
        ),
        manage_query_planning=ManageQueryPlanning(
            active_repository,
            active_planning_client,
            active_clock,
        ),
        manage_query_run_jobs=ManageQueryRunJobs(active_repository, active_clock),
        run_kmindhub_analysis_extraction=RunKMindHubAnalysisExtraction(
            active_repository,
            ManageKMindHubWorkspaceMapping(active_repository, active_kmindhub_client),
            active_kmindhub_client,
            active_clock,
        ),
        dispatch_query_run_job=(
            DispatchQueryRunJob(active_repository, active_publisher, active_clock)
            if active_publisher is not None
            else None
        ),
        receive_external_run_callback=ReceiveExternalRunCallback(
            active_repository,
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


def _build_repository() -> GeoAnalysisRepository:
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
        base_url=os.getenv("KMINDHUB_INSIGHT_BASE_URL", "http://kmindhub-insight-api:8000"),
        timeout_seconds=float(os.getenv("KMINDHUB_INSIGHT_TIMEOUT_SECONDS", "30")),
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
