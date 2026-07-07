import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID

import pytest

from younilab_seo.geo_analysis.application import (
    BuildGeoMetricFormulaSource,
    GeoMetricFormulaQuery,
    GeoMetricFormulaSource,
    GeoMetricFormulaSourceProjectNotFound,
    GeoMetricRunResultInput,
    GeoProjectRecord,
)


TENANT_ID = UUID("00000000-0000-4000-8000-000000000001")
PROJECT_ID = UUID("00000000-0000-4000-8000-000000000002")
RUN_RESULT_ID = UUID("00000000-0000-4000-8000-000000000003")


@dataclass
class FakeRepository:
    project: GeoProjectRecord | None = None
    source: GeoMetricFormulaSource = field(default_factory=GeoMetricFormulaSource)
    captured_query: GeoMetricFormulaQuery | None = None
    captured_normalizer_version: str | None = None

    async def get_project(self, tenant_id, project_id):
        if tenant_id == TENANT_ID and project_id == PROJECT_ID:
            return self.project
        return None

    async def get_metric_formula_source(
        self,
        tenant_id,
        project_id,
        query,
        normalizer_version,
    ):
        self.captured_query = query
        self.captured_normalizer_version = normalizer_version
        return self.source


def test_build_metric_formula_source_normalizes_implicit_comparison_period() -> None:
    async def run() -> None:
        source = GeoMetricFormulaSource(
            runResults=[
                GeoMetricRunResultInput(
                    runResultId=RUN_RESULT_ID,
                    completedAt=datetime(2026, 7, 2, tzinfo=UTC),
                )
            ]
        )
        repository = FakeRepository(
            project=_project(),
            source=source,
        )
        query = GeoMetricFormulaQuery(
            periodStart=datetime(2026, 7, 1, tzinfo=UTC),
            periodEnd=datetime(2026, 7, 8, tzinfo=UTC),
        )

        result = await BuildGeoMetricFormulaSource(repository).execute(
            TENANT_ID,
            PROJECT_ID,
            query,
        )

        assert result == source
        assert repository.captured_query is not None
        assert repository.captured_query.comparison_start == datetime(
            2026,
            6,
            24,
            tzinfo=UTC,
        )
        assert repository.captured_query.comparison_end == datetime(
            2026,
            7,
            1,
            tzinfo=UTC,
        )
        assert repository.captured_normalizer_version == "url_domain:v2"

    asyncio.run(run())


def test_build_metric_formula_source_keeps_explicit_comparison_period() -> None:
    async def run() -> None:
        repository = FakeRepository(project=_project())
        query = GeoMetricFormulaQuery(
            periodStart=datetime(2026, 7, 1, tzinfo=UTC),
            periodEnd=datetime(2026, 7, 8, tzinfo=UTC),
            comparisonStart=datetime(2026, 6, 1, tzinfo=UTC),
            comparisonEnd=datetime(2026, 6, 8, tzinfo=UTC),
        )

        await BuildGeoMetricFormulaSource(
            repository,
            normalizer_version="url_domain:v2",
        ).execute(TENANT_ID, PROJECT_ID, query)

        assert repository.captured_query == query
        assert repository.captured_normalizer_version == "url_domain:v2"

    asyncio.run(run())


def test_build_metric_formula_source_rejects_missing_project() -> None:
    async def run() -> None:
        repository = FakeRepository(project=None)

        with pytest.raises(GeoMetricFormulaSourceProjectNotFound):
            await BuildGeoMetricFormulaSource(repository).execute(
                TENANT_ID,
                PROJECT_ID,
                GeoMetricFormulaQuery(
                    periodStart=datetime(2026, 7, 1, tzinfo=UTC),
                    periodEnd=datetime(2026, 7, 8, tzinfo=UTC),
                ),
            )

    asyncio.run(run())


def _project() -> GeoProjectRecord:
    now = datetime(2026, 7, 1, tzinfo=UTC)
    return GeoProjectRecord(
        id=PROJECT_ID,
        tenantId=TENANT_ID,
        name="Acme GEO",
        createdAt=now,
        updatedAt=now,
    )
