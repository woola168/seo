import os
from dataclasses import dataclass
from datetime import UTC, datetime

from younilab_geo_analysis_api.presentation.http.store import GeoApiStore
from younilab_seo.geo_analysis.application import (
    Clock,
    DispatchQueryRunJob,
    GeoAnalysisRepository,
    ManageGeoSetup,
    ManageQueryRunJobs,
    MessagePublisher,
    ReceiveExternalRunCallback,
)
from younilab_seo.geo_analysis.infrastructure import (
    RabbitMqMessagePublisher,
    build_postgres_repository,
)


@dataclass(frozen=True)
class GeoAnalysisApiDependencies:
    repository: GeoAnalysisRepository
    manage_geo_setup: ManageGeoSetup
    manage_query_run_jobs: ManageQueryRunJobs
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
    callback_base_url: str | None = None,
) -> GeoAnalysisApiDependencies:
    active_repository = repository or _build_repository()
    active_clock = clock or SystemClock()
    active_publisher = publisher or _build_publisher()
    closeables = (active_publisher,) if active_publisher is not None else ()
    return GeoAnalysisApiDependencies(
        repository=active_repository,
        manage_geo_setup=ManageGeoSetup(active_repository),
        manage_query_run_jobs=ManageQueryRunJobs(active_repository, active_clock),
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
