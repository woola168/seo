import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID

import pytest

from younilab_seo.geo_analysis.application import (
    CalculateGeoReportMetrics,
    GeoMetricFormulaQuery,
    GeoMetricFormulaResult,
    GeoMetricFormulaSource,
    GeoMetricFormulaSourceProjectNotFound,
    GeoMetricRunResultInput,
    GeoMetricValue,
)


TENANT_ID = UUID("00000000-0000-4000-8000-000000000001")
PROJECT_ID = UUID("00000000-0000-4000-8000-000000000002")
RUN_RESULT_ID = UUID("00000000-0000-4000-8000-000000000003")
QUERY_ID = UUID("00000000-0000-4000-8000-000000000004")
TOPIC_ID = UUID("00000000-0000-4000-8000-000000000005")


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


@dataclass
class FakeCalculator:
    result: GeoMetricFormulaResult
    calls: list[tuple[GeoMetricFormulaSource, GeoMetricFormulaQuery]] = field(
        default_factory=list
    )

    def calculate(self, source, query):
        self.calls.append((source, query))
        return self.result


def test_calculate_geo_report_metrics_builds_source_and_calculates_result() -> None:
    async def run() -> None:
        source = GeoMetricFormulaSource(
            runResults=[
                GeoMetricRunResultInput(
                    runResultId=RUN_RESULT_ID,
                    queryId=QUERY_ID,
                    topicId=TOPIC_ID,
                    provider="gemini",
                    region="TW",
                    language="zh-TW",
                    completedAt=datetime(2026, 7, 2, tzinfo=UTC),
                )
            ]
        )
        query = _query(provider="gemini")
        expected = _result(query)
        source_builder = FakeSourceBuilder(source=source)
        calculator = FakeCalculator(result=expected)

        result = await CalculateGeoReportMetrics(
            source_builder=source_builder,
            calculator=calculator,
        ).execute(TENANT_ID, PROJECT_ID, query)

        assert result == expected
        assert len(source_builder.calls) == 1
        captured_query = source_builder.calls[0][2]
        assert source_builder.calls[0][:2] == (TENANT_ID, PROJECT_ID)
        assert captured_query.comparison_start == datetime(2026, 6, 24, tzinfo=UTC)
        assert captured_query.comparison_end == query.period_start
        assert calculator.calls == [(source, captured_query)]

    asyncio.run(run())


def test_calculate_geo_report_metrics_propagates_project_missing_error() -> None:
    async def run() -> None:
        source_builder = FakeSourceBuilder(
            error=GeoMetricFormulaSourceProjectNotFound("project not found")
        )
        calculator = FakeCalculator(result=_result(_query()))

        with pytest.raises(GeoMetricFormulaSourceProjectNotFound):
            await CalculateGeoReportMetrics(
                source_builder=source_builder,
                calculator=calculator,
            ).execute(TENANT_ID, PROJECT_ID, _query())

        assert calculator.calls == []

    asyncio.run(run())


def test_calculate_geo_report_metrics_passes_explicit_comparison_and_filters() -> None:
    async def run() -> None:
        query = GeoMetricFormulaQuery(
            periodStart=datetime(2026, 7, 1, tzinfo=UTC),
            periodEnd=datetime(2026, 7, 8, tzinfo=UTC),
            comparisonStart=datetime(2026, 6, 1, tzinfo=UTC),
            comparisonEnd=datetime(2026, 6, 8, tzinfo=UTC),
            queryId=QUERY_ID,
            topicId=TOPIC_ID,
            provider="gemini",
            region="TW",
            language="zh-TW",
        )
        source_builder = FakeSourceBuilder()
        calculator = FakeCalculator(result=_result(query))

        await CalculateGeoReportMetrics(
            source_builder=source_builder,
            calculator=calculator,
        ).execute(TENANT_ID, PROJECT_ID, query)

        captured_query = source_builder.calls[0][2]
        assert captured_query == query
        assert calculator.calls[0][1] == query

    asyncio.run(run())


def test_calculate_geo_report_metrics_returns_valid_result_for_empty_source() -> None:
    async def run() -> None:
        query = _query()

        result = await CalculateGeoReportMetrics(
            source_builder=FakeSourceBuilder(source=GeoMetricFormulaSource()),
        ).execute(TENANT_ID, PROJECT_ID, query)

        assert result.period_start == query.period_start
        assert result.period_end == query.period_end
        assert result.comparison_start == datetime(2026, 6, 24, tzinfo=UTC)
        assert result.comparison_end == query.period_start
        assert _metric(result.metrics, "visibility").value == 0
        assert _metric(result.metrics, "mentions").value == 0
        assert _metric(result.metrics, "sov").value == 0

    asyncio.run(run())


def _query(**overrides) -> GeoMetricFormulaQuery:
    payload = {
        "periodStart": datetime(2026, 7, 1, tzinfo=UTC),
        "periodEnd": datetime(2026, 7, 8, tzinfo=UTC),
    }
    payload.update(overrides)
    return GeoMetricFormulaQuery(**payload)


def _result(query: GeoMetricFormulaQuery) -> GeoMetricFormulaResult:
    return GeoMetricFormulaResult(
        periodStart=query.period_start,
        periodEnd=query.period_end,
        comparisonStart=query.comparison_start or datetime(2026, 6, 24, tzinfo=UTC),
        comparisonEnd=query.comparison_end or query.period_start,
        metrics=[
            GeoMetricValue(
                metricName="visibility",
                scopeType="project",
                value=100,
                unit="percent",
            )
        ],
    )


def _metric(metrics: list[GeoMetricValue], metric_name: str) -> GeoMetricValue:
    for metric in metrics:
        if metric.metric_name == metric_name and metric.scope_type == "project":
            return metric
    raise AssertionError(f"metric not found: {metric_name}")
