from younilab_seo.geo_analysis.infrastructure.persistence.postgres.models import (
    GeoAiPlatformRow,
    GeoEntityAliasRow,
    GeoEntityRow,
    GeoExternalRunReferenceRow,
    GeoJobDispatchEventRow,
    GeoMarketRow,
    GeoMessageDispatchLogRow,
    GeoProjectRow,
    GeoQueryDraftRow,
    GeoQueryDraftSelectionRow,
    GeoQueryGenerationRunRow,
    GeoQueryKeywordRow,
    GeoQueryPlatformRow,
    GeoQueryResearchRunRow,
    GeoQueryRow,
    GeoQueryRunJobRow,
    GeoQueryScheduleRow,
    GeoRunRequestRow,
    GeoRunResultReferenceRow,
    GeoRunResultRow,
    GeoTopicRow,
    GeoWorkerLeaseRow,
)
from younilab_seo.geo_analysis.infrastructure.persistence.postgres.database import (
    build_postgres_repository,
    build_postgres_session_factory,
)
from younilab_seo.geo_analysis.infrastructure.persistence.postgres.repository import (
    PostgresGeoAnalysisRepository,
)
__all__ = [
    "GeoAiPlatformRow",
    "GeoEntityAliasRow",
    "GeoEntityRow",
    "GeoExternalRunReferenceRow",
    "GeoJobDispatchEventRow",
    "GeoMarketRow",
    "GeoMessageDispatchLogRow",
    "GeoProjectRow",
    "GeoQueryDraftRow",
    "GeoQueryDraftSelectionRow",
    "GeoQueryGenerationRunRow",
    "GeoQueryKeywordRow",
    "GeoQueryPlatformRow",
    "GeoQueryResearchRunRow",
    "GeoQueryRow",
    "GeoQueryRunJobRow",
    "GeoQueryScheduleRow",
    "GeoRunRequestRow",
    "GeoRunResultReferenceRow",
    "GeoRunResultRow",
    "GeoTopicRow",
    "GeoWorkerLeaseRow",
    "PostgresGeoAnalysisRepository",
    "HttpTrackingRunClient",
    "RabbitMqMessagePublisher",
    "RabbitMqQueryRunJobConsumer",
    "build_postgres_repository",
    "build_postgres_session_factory",
]


def __getattr__(name: str):
    if name == "HttpTrackingRunClient":
        from younilab_seo.geo_analysis.infrastructure.tracking import (
            HttpTrackingRunClient,
        )

        return HttpTrackingRunClient
    if name == "RabbitMqMessagePublisher":
        from younilab_seo.geo_analysis.infrastructure.messaging import (
            RabbitMqMessagePublisher,
        )

        return RabbitMqMessagePublisher
    if name == "RabbitMqQueryRunJobConsumer":
        from younilab_seo.geo_analysis.infrastructure.messaging import (
            RabbitMqQueryRunJobConsumer,
        )

        return RabbitMqQueryRunJobConsumer
    raise AttributeError(name)
