from datetime import UTC, datetime
from uuid import UUID

import pytest
from pydantic import ValidationError

from younilab_seo.geo_analysis.application import (
    CalculateGeoMetricFormulas,
    GeoMetricFormulaQuery,
    GeoMetricFormulaSource,
    GeoMetricRunResultInput,
    GeoMetricValue,
    GeoRunResultCitationFact,
)


RUN_1 = UUID("00000000-0000-4000-8000-000000000001")
RUN_2 = UUID("00000000-0000-4000-8000-000000000002")
RUN_3 = UUID("00000000-0000-4000-8000-000000000003")
RUN_4 = UUID("00000000-0000-4000-8000-000000000004")
QUERY_ID = UUID("00000000-0000-4000-8000-000000000010")
TOPIC_ID = UUID("00000000-0000-4000-8000-000000000011")
OWN_BRAND_ID = UUID("00000000-0000-4000-8000-000000000020")
COMPETITOR_ID = UUID("00000000-0000-4000-8000-000000000021")
OTHER_COMPETITOR_ID = UUID("00000000-0000-4000-8000-000000000022")


def test_calculates_visibility_mentions_position_and_previous_period() -> None:
    source = GeoMetricFormulaSource(
        runResults=[
            _run(RUN_1, datetime(2026, 7, 2, tzinfo=UTC)),
            _run(RUN_2, datetime(2026, 7, 3, tzinfo=UTC)),
            _run(RUN_3, datetime(2026, 6, 29, tzinfo=UTC)),
            _run(RUN_4, datetime(2026, 7, 8, tzinfo=UTC)),
        ],
        entityMentions=[
            _mention(RUN_1, OWN_BRAND_ID, "own_brand", "Acme", True, 1),
            _mention(RUN_2, OWN_BRAND_ID, "own_brand", "Acme", False),
            _mention(RUN_1, COMPETITOR_ID, "competitor", "Beta", True, 2),
            _mention(RUN_2, COMPETITOR_ID, "competitor", "Beta", True, 1),
            _mention(RUN_3, OWN_BRAND_ID, "own_brand", "Acme", True, 2),
        ],
    )

    result = CalculateGeoMetricFormulas().calculate(
        source,
        GeoMetricFormulaQuery(
            periodStart=datetime(2026, 7, 1, tzinfo=UTC),
            periodEnd=datetime(2026, 7, 8, tzinfo=UTC),
        ),
    )

    assert result.comparison_start == datetime(2026, 6, 24, tzinfo=UTC)
    assert result.comparison_end == datetime(2026, 7, 1, tzinfo=UTC)
    visibility = _metric(result.metrics, "visibility", "project")
    mentions = _metric(result.metrics, "mentions", "project")
    position = _metric(result.metrics, "average_position", "project")
    competitor_visibility = _metric(
        result.metrics,
        "visibility",
        "entity",
        str(COMPETITOR_ID),
    )
    competitor_mentions = _metric(
        result.metrics,
        "mentions",
        "entity",
        str(COMPETITOR_ID),
    )
    competitor_position = _metric(
        result.metrics,
        "average_position",
        "entity",
        str(COMPETITOR_ID),
    )

    assert visibility.value == 50
    assert visibility.numerator == 1
    assert visibility.denominator == 2
    assert visibility.comparison_value == 100
    assert visibility.delta == -50
    assert visibility.delta_unit == "pp"
    assert mentions.value == 1
    assert mentions.denominator == 2
    assert position.value == 1
    assert competitor_visibility.value == 100
    assert competitor_mentions.value == 2
    assert competitor_position.value == pytest.approx(1.5)


def test_calculates_sov_from_configured_entity_mentions_only() -> None:
    source = GeoMetricFormulaSource(
        runResults=[
            _run(RUN_1, datetime(2026, 7, 2, tzinfo=UTC)),
            _run(RUN_2, datetime(2026, 7, 3, tzinfo=UTC)),
        ],
        entityMentions=[
            _mention(RUN_1, OWN_BRAND_ID, "own_brand", "Acme", True, 1),
            _mention(RUN_2, OWN_BRAND_ID, "own_brand", "Acme", False),
            _mention(RUN_1, COMPETITOR_ID, "competitor", "Beta", True, 2),
            _mention(RUN_2, COMPETITOR_ID, "competitor", "Beta", True, 1),
            _mention(RUN_2, OTHER_COMPETITOR_ID, "competitor", "Gamma", False),
        ],
    )

    result = CalculateGeoMetricFormulas().calculate(source, _current_query())

    sov = _metric(result.metrics, "sov", "project")
    assert sov.value == pytest.approx(100 / 3)
    assert sov.numerator == 1
    assert sov.denominator == 3


def test_calculates_citation_count_used_percent_and_share_percent() -> None:
    source = GeoMetricFormulaSource(
        runResults=[
            _run(RUN_1, datetime(2026, 7, 2, tzinfo=UTC)),
            _run(RUN_2, datetime(2026, 7, 3, tzinfo=UTC)),
        ],
        entityMentions=[
            _mention(RUN_1, OWN_BRAND_ID, "own_brand", "Acme", True, 1),
            _mention(RUN_2, OWN_BRAND_ID, "own_brand", "Acme", True, 1),
        ],
        citations=[
            _citation(RUN_1, 1, "https://acme.example/a", "acme.example"),
            _citation(RUN_1, 2, "https://acme.example/a", "acme.example"),
            _citation(RUN_2, 1, "https://docs.example/b", "docs.example"),
        ],
    )

    result = CalculateGeoMetricFormulas().calculate(source, _current_query())

    url_count = _metric(
        result.metrics,
        "citation_count",
        "citation_url",
        "https://acme.example/a",
    )
    url_used = _metric(
        result.metrics,
        "used_percent",
        "citation_url",
        "https://acme.example/a",
    )
    url_share = _metric(
        result.metrics,
        "share_percent",
        "citation_url",
        "https://acme.example/a",
    )
    domain_share = _metric(
        result.metrics,
        "share_percent",
        "citation_domain",
        "acme.example",
    )

    assert url_count.value == 2
    assert url_count.denominator == 3
    assert url_used.value == 50
    assert url_used.numerator == 1
    assert url_used.denominator == 2
    assert url_share.value == pytest.approx(200 / 3)
    assert url_share.numerator == 2
    assert url_share.denominator == 3
    assert domain_share.value == pytest.approx(200 / 3)


def test_calculates_sentiment_counts_for_own_brand_only() -> None:
    source = GeoMetricFormulaSource(
        runResults=[_run(RUN_1, datetime(2026, 7, 2, tzinfo=UTC))],
        entityMentions=[_mention(RUN_1, OWN_BRAND_ID, "own_brand", "Acme", True, 1)],
        sentiments=[
            _sentiment(RUN_1, OWN_BRAND_ID, "own_brand", "Acme", "positive"),
            _sentiment(RUN_1, OWN_BRAND_ID, "own_brand", "Acme", "positive"),
            _sentiment(RUN_1, OWN_BRAND_ID, "own_brand", "Acme", "negative"),
            *[
                _sentiment(
                    RUN_1,
                    COMPETITOR_ID,
                    "competitor",
                    "Beta",
                    "positive",
                )
                for _ in range(5)
            ],
            *[
                _sentiment(
                    RUN_1,
                    COMPETITOR_ID,
                    "competitor",
                    "Beta",
                    "negative",
                )
                for _ in range(4)
            ],
        ],
    )

    result = CalculateGeoMetricFormulas().calculate(source, _current_query())

    positive = _metric(result.metrics, "sentiment_count", "sentiment", "positive")
    negative = _metric(result.metrics, "sentiment_count", "sentiment", "negative")
    assert positive.value == 2
    assert positive.denominator == 3
    assert negative.value == 1
    assert negative.denominator == 3


def test_keeps_metrics_that_disappear_from_current_period_for_comparison() -> None:
    source = GeoMetricFormulaSource(
        runResults=[
            _run(RUN_1, datetime(2026, 7, 2, tzinfo=UTC)),
            _run(RUN_3, datetime(2026, 6, 29, tzinfo=UTC)),
        ],
        entityMentions=[
            _mention(RUN_1, OWN_BRAND_ID, "own_brand", "Acme", True, 1),
            _mention(RUN_3, OWN_BRAND_ID, "own_brand", "Acme", True, 1),
        ],
        citations=[
            _citation(RUN_3, 1, "https://legacy.example/a", "legacy.example"),
        ],
    )

    result = CalculateGeoMetricFormulas().calculate(source, _current_query())

    disappeared_count = _metric(
        result.metrics,
        "citation_count",
        "citation_url",
        "https://legacy.example/a",
    )
    disappeared_share = _metric(
        result.metrics,
        "share_percent",
        "citation_url",
        "https://legacy.example/a",
    )
    assert disappeared_count.value == 0
    assert disappeared_count.comparison_value == 1
    assert disappeared_count.delta == -1
    assert disappeared_share.value == 0
    assert disappeared_share.comparison_value == 100
    assert disappeared_share.delta == -100


def test_applies_query_topic_provider_region_and_language_filters() -> None:
    source = GeoMetricFormulaSource(
        runResults=[
            _run(RUN_1, datetime(2026, 7, 2, tzinfo=UTC), provider="gemini"),
            _run(RUN_2, datetime(2026, 7, 3, tzinfo=UTC), provider="chatgpt"),
        ],
        entityMentions=[
            _mention(RUN_1, OWN_BRAND_ID, "own_brand", "Acme", True, 1),
            _mention(RUN_2, OWN_BRAND_ID, "own_brand", "Acme", True, 1),
        ],
    )

    result = CalculateGeoMetricFormulas().calculate(
        source,
        GeoMetricFormulaQuery(
            periodStart=datetime(2026, 7, 1, tzinfo=UTC),
            periodEnd=datetime(2026, 7, 8, tzinfo=UTC),
            queryId=QUERY_ID,
            topicId=TOPIC_ID,
            provider="gemini",
            region="TW",
            language="zh-TW",
        ),
    )

    visibility = _metric(result.metrics, "visibility", "project")
    assert visibility.value == 100
    assert visibility.numerator == 1
    assert visibility.denominator == 1


def test_metric_periods_and_completed_at_must_be_timezone_aware() -> None:
    with pytest.raises(ValidationError):
        GeoMetricFormulaQuery(
            periodStart=datetime(2026, 7, 1),
            periodEnd=datetime(2026, 7, 8, tzinfo=UTC),
        )

    with pytest.raises(ValidationError):
        _run(RUN_1, datetime(2026, 7, 2))


def test_comparison_period_must_not_overlap_current_period() -> None:
    with pytest.raises(ValidationError):
        GeoMetricFormulaQuery(
            periodStart=datetime(2026, 7, 1, tzinfo=UTC),
            periodEnd=datetime(2026, 7, 8, tzinfo=UTC),
            comparisonStart=datetime(2026, 6, 28, tzinfo=UTC),
            comparisonEnd=datetime(2026, 7, 2, tzinfo=UTC),
        )


def _current_query() -> GeoMetricFormulaQuery:
    return GeoMetricFormulaQuery(
        periodStart=datetime(2026, 7, 1, tzinfo=UTC),
        periodEnd=datetime(2026, 7, 8, tzinfo=UTC),
    )


def _run(
    run_result_id: UUID,
    completed_at: datetime,
    *,
    provider: str = "gemini",
) -> GeoMetricRunResultInput:
    return GeoMetricRunResultInput(
        runResultId=run_result_id,
        queryId=QUERY_ID,
        topicId=TOPIC_ID,
        provider=provider,
        region="TW",
        language="zh-TW",
        completedAt=completed_at,
    )


def _mention(
    run_result_id: UUID,
    entity_id: UUID,
    entity_role: str,
    entity_name: str,
    mentioned: bool,
    first_mention_order: int | None = None,
) -> dict:
    return {
        "runResultId": run_result_id,
        "entityId": entity_id,
        "entityRole": entity_role,
        "entityName": entity_name,
        "mentioned": mentioned,
        "firstMentionOrder": first_mention_order,
    }


def _sentiment(
    run_result_id: UUID,
    entity_id: UUID,
    entity_role: str,
    entity_name: str,
    sentiment: str,
) -> dict:
    return {
        "runResultId": run_result_id,
        "entityId": entity_id,
        "entityRole": entity_role,
        "entityName": entity_name,
        "sentiment": sentiment,
        "theme": "quality",
        "statement": "Acme is reliable.",
    }


def _citation(
    run_result_id: UUID,
    position: int,
    url: str,
    domain: str,
) -> GeoRunResultCitationFact:
    return GeoRunResultCitationFact(
        runResultId=run_result_id,
        referenceId=UUID(f"00000000-0000-4000-8000-10000000000{position}"),
        url=url,
        domain=domain,
        position=position,
        ownership="other",
        sourceType="unknown",
    )


def _metric(
    metrics: list[GeoMetricValue],
    metric_name: str,
    scope_type: str,
    scope_value: str | None = None,
) -> GeoMetricValue:
    for metric in metrics:
        if (
            metric.metric_name == metric_name
            and metric.scope_type == scope_type
            and metric.scope_value == scope_value
        ):
            return metric
    raise AssertionError(f"metric not found: {metric_name} {scope_type} {scope_value}")
