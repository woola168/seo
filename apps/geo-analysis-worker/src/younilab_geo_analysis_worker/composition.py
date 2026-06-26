import os
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from younilab_seo.geo_analysis.application import (
    Clock,
    GeoQueryRunJobRepository,
    ProcessQueryRunJobMessage,
    TrackingRunClient,
)
from younilab_seo.geo_analysis.infrastructure.persistence.postgres import (
    build_postgres_repository,
)


@dataclass(frozen=True)
class GeoAnalysisWorkerDependencies:
    processor: ProcessQueryRunJobMessage
    consumer: Any
    closeables: tuple[object, ...] = ()

    async def close(self) -> None:
        for closeable in self.closeables:
            close = getattr(closeable, "close", None)
            if close is not None:
                await close()


def build_dependencies(
    *,
    repository: GeoQueryRunJobRepository | None = None,
    tracking_client: TrackingRunClient | None = None,
    consumer: Any | None = None,
    clock: Clock | None = None,
    provider: str | None = None,
) -> GeoAnalysisWorkerDependencies:
    active_provider = provider or os.getenv("GEO_ANALYSIS_WORKER_PROVIDER", "gemini")
    active_repository = repository or _build_repository()
    active_tracking_client = tracking_client or _build_tracking_client()
    active_consumer = consumer or _build_consumer(active_provider)
    active_clock = clock or SystemClock()
    return GeoAnalysisWorkerDependencies(
        processor=ProcessQueryRunJobMessage(
            repository=active_repository,
            tracking_client=active_tracking_client,
            clock=active_clock,
            supported_provider=active_provider,
        ),
        consumer=active_consumer,
        closeables=(active_tracking_client,),
    )


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC).replace(microsecond=0)


def _build_repository() -> GeoQueryRunJobRepository:
    return build_postgres_repository(_required_env("GEO_ANALYSIS_DATABASE_URL"))


def _build_tracking_client() -> TrackingRunClient:
    from younilab_seo.geo_analysis.infrastructure.tracking import HttpTrackingRunClient

    return HttpTrackingRunClient(
        base_url=os.getenv("GEO_TRACKING_BASE_URL", "http://geo-tracking-api:8003"),
        timeout_seconds=float(os.getenv("GEO_TRACKING_TIMEOUT_SECONDS", "60")),
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
