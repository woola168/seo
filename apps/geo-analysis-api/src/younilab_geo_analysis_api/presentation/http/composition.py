import os
from dataclasses import dataclass
from datetime import UTC, datetime

from younilab_geo_analysis_api.presentation.http.store import GeoApiStore
from younilab_seo.geo_analysis.application import (
    Clock,
    GeoAnalysisRepository,
    ManageGeoSetup,
    ManageQueryRunJobs,
)
from younilab_seo.geo_analysis.infrastructure import build_postgres_repository


@dataclass(frozen=True)
class GeoAnalysisApiDependencies:
    repository: GeoAnalysisRepository
    manage_geo_setup: ManageGeoSetup
    manage_query_run_jobs: ManageQueryRunJobs


def build_dependencies(
    *,
    repository: GeoAnalysisRepository | None = None,
    clock: Clock | None = None,
) -> GeoAnalysisApiDependencies:
    active_repository = repository or _build_repository()
    active_clock = clock or SystemClock()
    return GeoAnalysisApiDependencies(
        repository=active_repository,
        manage_geo_setup=ManageGeoSetup(active_repository),
        manage_query_run_jobs=ManageQueryRunJobs(active_repository, active_clock),
    )


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC).replace(microsecond=0)


def _build_repository() -> GeoAnalysisRepository:
    database_url = os.getenv("GEO_ANALYSIS_DATABASE_URL")
    if database_url:
        return build_postgres_repository(database_url)
    return GeoApiStore()
