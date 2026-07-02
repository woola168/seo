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
    TenantKMindHubWorkspaceMappingRow,
)
from younilab_seo.geo_analysis.infrastructure.persistence.postgres.database import (
    build_postgres_repository,
    build_postgres_session_factory,
)
from younilab_seo.geo_analysis.infrastructure.persistence.postgres.repository import (
    PostgresGeoAnalysisRepository,
)
__all__ = [
    "AccessControlAuthorizer",
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
    "TenantKMindHubWorkspaceMappingRow",
    "HttpKMindHubWorkspaceClient",
    "PostgresGeoAnalysisRepository",
    "HttpTrackingRunClient",
    "RabbitMqMessagePublisher",
    "RabbitMqQueryRunJobConsumer",
    "ResourceCatalogHttpReferenceVerifier",
    "build_postgres_repository",
    "build_postgres_session_factory",
]


def __getattr__(name: str):
    if name == "AccessControlAuthorizer":
        from younilab_seo.geo_analysis.infrastructure.authorization import (
            AccessControlAuthorizer,
        )

        return AccessControlAuthorizer
    if name == "ResourceCatalogHttpReferenceVerifier":
        from younilab_seo.geo_analysis.infrastructure.authorization import (
            ResourceCatalogHttpReferenceVerifier,
        )

        return ResourceCatalogHttpReferenceVerifier
    if name == "HttpTrackingRunClient":
        from younilab_seo.geo_analysis.infrastructure.tracking import (
            HttpTrackingRunClient,
        )

        return HttpTrackingRunClient
    if name == "HttpKMindHubWorkspaceClient":
        from younilab_seo.geo_analysis.infrastructure.kmindhub import (
            HttpKMindHubWorkspaceClient,
        )

        return HttpKMindHubWorkspaceClient
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
