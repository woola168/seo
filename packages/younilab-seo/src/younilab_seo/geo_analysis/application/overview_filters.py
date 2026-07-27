from younilab_seo.geo_analysis.application.contracts import (
    GeoMetricFormulaQuery,
    GeoMetricFormulaSource,
    GeoOverviewFilterOption,
    GeoOverviewFilterOptions,
    GeoOverviewQuery,
    GeoQueryRecord,
    GeoTopicRecord,
)


def overview_formula_query(query: GeoOverviewQuery) -> GeoMetricFormulaQuery:
    duration = query.period_end - query.period_start
    return GeoMetricFormulaQuery(
        period_start=query.period_start,
        period_end=query.period_end,
        comparison_start=query.period_start - duration,
        comparison_end=query.period_start,
    )


def filter_overview_formula_source(
    source: GeoMetricFormulaSource,
    queries: list[GeoQueryRecord],
    query: GeoOverviewQuery,
) -> GeoMetricFormulaSource:
    query_index = {item.id: item for item in queries}
    selected_ids = {
        item.run_result_id
        for item in source.run_results
        if overview_run_matches(item, query_index.get(item.query_id), query)
    }
    return GeoMetricFormulaSource(
        run_results=[
            item for item in source.run_results if item.run_result_id in selected_ids
        ],
        entity_mentions=[
            item
            for item in source.entity_mentions
            if item.run_result_id in selected_ids
        ],
        sentiments=[
            item for item in source.sentiments if item.run_result_id in selected_ids
        ],
        citations=[
            item for item in source.citations if item.run_result_id in selected_ids
        ],
    )


def select_overview_queries(
    queries: list[GeoQueryRecord],
    query: GeoOverviewQuery,
) -> list[GeoQueryRecord]:
    return [
        item
        for item in queries
        if (not query.topic_ids or item.topic_id in query.topic_ids)
        and overview_metadata_matches(
            item.metadata.get("industry"),
            query.metadata_industry,
        )
        and overview_metadata_matches(
            item.metadata.get("type"),
            query.metadata_type,
        )
    ]


def overview_filter_options(
    source: GeoMetricFormulaSource,
    queries: list[GeoQueryRecord],
    topics: list[GeoTopicRecord],
    query: GeoOverviewQuery,
) -> GeoOverviewFilterOptions:
    current_runs = [
        item
        for item in source.run_results
        if query.period_start <= item.completed_at < query.period_end
    ]
    return overview_filter_options_from_dimensions(
        queries,
        topics,
        {item.provider for item in current_runs if item.provider},
        {item.region for item in current_runs if item.region},
    )


def overview_filter_options_from_dimensions(
    queries: list[GeoQueryRecord],
    topics: list[GeoTopicRecord],
    providers: set[str],
    regions: set[str],
) -> GeoOverviewFilterOptions:
    return GeoOverviewFilterOptions(
        topics=[
            GeoOverviewFilterOption(value=str(item.id), label=item.name)
            for item in sorted(topics, key=lambda item: item.name)
        ],
        platforms=[
            GeoOverviewFilterOption(value=value, label=_provider_label(value))
            for value in sorted(providers)
        ],
        regions=sorted(regions),
        metadata_industries=_metadata_options(queries, "industry"),
        metadata_types=_metadata_options(queries, "type"),
    )


def overview_run_matches(
    run_result,
    source_query: GeoQueryRecord | None,
    query: GeoOverviewQuery,
) -> bool:
    if query.topic_ids and (
        source_query is None or source_query.topic_id not in query.topic_ids
    ):
        return False
    if query.providers and run_result.provider not in query.providers:
        return False
    if query.region and run_result.region != query.region:
        return False
    if source_query is None:
        return not query.metadata_industry and not query.metadata_type
    return overview_metadata_matches(
        source_query.metadata.get("industry"), query.metadata_industry
    ) and overview_metadata_matches(
        source_query.metadata.get("type"), query.metadata_type
    )


def overview_metadata_matches(value, selected: list[str]) -> bool:
    if not selected:
        return True
    values = value if isinstance(value, list) else [value]
    return any(item in selected for item in values if isinstance(item, str))


def _metadata_options(queries: list[GeoQueryRecord], key: str) -> list[str]:
    values: set[str] = set()
    for item in queries:
        value = item.metadata.get(key)
        candidates = value if isinstance(value, list) else [value]
        values.update(
            candidate for candidate in candidates if isinstance(candidate, str)
        )
    return sorted(values)


def _provider_label(provider: str) -> str:
    return {"gemini": "Gemini", "google_aio": "Google AI Overview"}.get(
        provider,
        provider.replace("_", " ").title(),
    )
