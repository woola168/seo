import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID

import pytest

from younilab_seo.geo_analysis.application import (
    GetGeoDashboardReport,
    GeoMetricEntityMentionInput,
    GeoMetricFormulaQuery,
    GeoMetricFormulaSource,
    GeoMetricFormulaSourceProjectNotFound,
    GeoMetricRunResultInput,
    GeoMetricSentimentInput,
    GeoRunResultCitationFact,
)


TENANT_ID = UUID("00000000-0000-4000-8000-000000000001")
PROJECT_ID = UUID("00000000-0000-4000-8000-000000000002")
CURRENT_RESULT_ID = UUID("00000000-0000-4000-8000-000000000003")
COMPARISON_RESULT_ID = UUID("00000000-0000-4000-8000-000000000004")
OWN_BRAND_ID = UUID("00000000-0000-4000-8000-000000000005")
COMPETITOR_ID = UUID("00000000-0000-4000-8000-000000000006")
REFERENCE_ID = UUID("00000000-0000-4000-8000-000000000007")


@dataclass
class FakeSourceBuilder:
    source: GeoMetricFormulaSource = field(default_factory=GeoMetricFormulaSource)
    error: Exception | None = None
    calls: list[tuple[UUID, UUID, GeoMetricFormulaQuery]] = field(default_factory=list)

    async def execute(self, tenant_id, project_id, query):
        self.calls.append((tenant_id, project_id, query))
        if self.error is not None:
            raise self.error
        return self.source


def test_dashboard_report_composes_overview_and_entity_rows() -> None:
    async def run() -> None:
        result = await GetGeoDashboardReport(
            source_builder=FakeSourceBuilder(source=_source()),
        ).execute(TENANT_ID, PROJECT_ID, _query())

        overview = {item.metric_name: item.metric for item in result.overview}
        assert overview["visibility"].value == 100
        assert overview["visibility"].comparison_value == 0
        assert overview["visibility"].delta == 100
        assert overview["mentions"].value == 1
        assert overview["sov"].value == 50
        assert overview["average_position"].value == 1

        own_brand = _entity(result.entities, OWN_BRAND_ID)
        competitor = _entity(result.entities, COMPETITOR_ID)
        assert own_brand.entity_role == "own_brand"
        assert own_brand.entity_name == "Acme"
        assert own_brand.visibility.value == 100
        assert own_brand.mentions.value == 1
        assert competitor.entity_role == "competitor"
        assert competitor.visibility.value == 100

    asyncio.run(run())


def test_dashboard_report_composes_citation_and_sentiment_rows() -> None:
    async def run() -> None:
        result = await GetGeoDashboardReport(
            source_builder=FakeSourceBuilder(source=_source()),
        ).execute(TENANT_ID, PROJECT_ID, _query())

        citation_url = result.citation_urls[0]
        citation_domain = result.citation_domains[0]
        assert citation_url.value == "https://example.com/reference"
        assert citation_url.ownership == "other"
        assert citation_url.source_type == "unknown"
        assert citation_url.citation_count.value == 1
        assert citation_url.used_percent.value == 100
        assert citation_url.share_percent.value == 100
        assert citation_domain.value == "example.com"

        sentiments = {item.sentiment: item.statement_count for item in result.sentiments}
        assert sentiments["positive"].value == 1
        assert sentiments["positive"].comparison_value == 0
        assert sentiments["negative"].value == 0
        assert sentiments["negative"].comparison_value == 1
        assert sentiments["negative"].delta == -1

    asyncio.run(run())


def test_dashboard_report_returns_stable_empty_report() -> None:
    async def run() -> None:
        result = await GetGeoDashboardReport(
            source_builder=FakeSourceBuilder(source=GeoMetricFormulaSource()),
        ).execute(TENANT_ID, PROJECT_ID, _query())

        overview = {item.metric_name: item.metric for item in result.overview}
        assert result.period_start == datetime(2026, 7, 1, tzinfo=UTC)
        assert result.comparison_start == datetime(2026, 6, 24, tzinfo=UTC)
        assert overview["visibility"].value == 0
        assert overview["mentions"].value == 0
        assert overview["sov"].value == 0
        assert result.entities == []
        assert result.citation_urls == []
        assert result.citation_domains == []
        assert result.sentiments == []

    asyncio.run(run())


def test_dashboard_report_propagates_project_missing_error() -> None:
    async def run() -> None:
        source_builder = FakeSourceBuilder(
            error=GeoMetricFormulaSourceProjectNotFound("project not found")
        )

        with pytest.raises(GeoMetricFormulaSourceProjectNotFound):
            await GetGeoDashboardReport(source_builder=source_builder).execute(
                TENANT_ID,
                PROJECT_ID,
                _query(),
            )

    asyncio.run(run())


def _query() -> GeoMetricFormulaQuery:
    return GeoMetricFormulaQuery(
        periodStart=datetime(2026, 7, 1, tzinfo=UTC),
        periodEnd=datetime(2026, 7, 8, tzinfo=UTC),
    )


def _source() -> GeoMetricFormulaSource:
    return GeoMetricFormulaSource(
        runResults=[
            GeoMetricRunResultInput(
                runResultId=CURRENT_RESULT_ID,
                completedAt=datetime(2026, 7, 2, tzinfo=UTC),
            ),
            GeoMetricRunResultInput(
                runResultId=COMPARISON_RESULT_ID,
                completedAt=datetime(2026, 6, 26, tzinfo=UTC),
            ),
        ],
        entityMentions=[
            GeoMetricEntityMentionInput(
                runResultId=CURRENT_RESULT_ID,
                entityId=OWN_BRAND_ID,
                entityRole="own_brand",
                entityName="Acme",
                mentioned=True,
                firstMentionOrder=1,
            ),
            GeoMetricEntityMentionInput(
                runResultId=CURRENT_RESULT_ID,
                entityId=COMPETITOR_ID,
                entityRole="competitor",
                entityName="Beta",
                mentioned=True,
                firstMentionOrder=2,
            ),
            GeoMetricEntityMentionInput(
                runResultId=COMPARISON_RESULT_ID,
                entityId=OWN_BRAND_ID,
                entityRole="own_brand",
                entityName="Acme",
                mentioned=False,
            ),
            GeoMetricEntityMentionInput(
                runResultId=COMPARISON_RESULT_ID,
                entityId=COMPETITOR_ID,
                entityRole="competitor",
                entityName="Beta",
                mentioned=True,
                firstMentionOrder=1,
            ),
        ],
        sentiments=[
            GeoMetricSentimentInput(
                runResultId=CURRENT_RESULT_ID,
                entityId=OWN_BRAND_ID,
                entityRole="own_brand",
                entityName="Acme",
                sentiment="positive",
                theme="供應商比較",
                statement="Acme is recommended.",
            ),
            GeoMetricSentimentInput(
                runResultId=COMPARISON_RESULT_ID,
                entityId=OWN_BRAND_ID,
                entityRole="own_brand",
                entityName="Acme",
                sentiment="negative",
                theme="供應商比較",
                statement="Acme was not mentioned.",
            ),
        ],
        citations=[
            GeoRunResultCitationFact(
                runResultId=CURRENT_RESULT_ID,
                referenceId=REFERENCE_ID,
                url="https://example.com/reference",
                domain="example.com",
                position=1,
                ownership="other",
                sourceType="unknown",
            )
        ],
    )


def _entity(rows, entity_id):
    for row in rows:
        if row.entity_id == entity_id:
            return row
    raise AssertionError(f"entity row not found: {entity_id}")
