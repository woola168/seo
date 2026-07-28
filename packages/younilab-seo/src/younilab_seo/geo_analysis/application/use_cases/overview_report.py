from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from younilab_seo.geo_analysis.application.contracts import (
    GeoMetricFormulaSource,
    GeoOverviewCitationRow,
    GeoOverviewCitationSummary,
    GeoOverviewEntityRow,
    GeoOverviewKpi,
    GeoOverviewQuery,
    GeoOverviewQueryRow,
    GeoOverviewReport,
    GeoOverviewResponsePage,
    GeoOverviewResponsePageQuery,
    GeoOverviewSentimentPoint,
    GeoOverviewTopicRow,
    GeoOverviewTrendPoint,
    GeoOverviewVisibilitySeries,
)
from younilab_seo.geo_analysis.application.interfaces import Clock
from younilab_seo.geo_analysis.application.interfaces.overview_read import (
    OverviewReportReadModel,
    OverviewResponseReadModel,
)
from younilab_seo.geo_analysis.application.overview_filters import (
    overview_formula_query,
)
from younilab_seo.geo_analysis.application.use_cases.metric_source import (
    GeoMetricFormulaSourceProjectNotFound,
)
from younilab_seo.geo_analysis.application.use_cases.metrics_formula import (
    CalculateGeoMetricFormulas,
)


@dataclass(frozen=True)
class GetGeoOverviewReport:
    """依現有 normalized facts 組裝 GEO Overview 使用的 read model。"""

    read_model: OverviewReportReadModel
    clock: Clock
    normalizer_version: str = "url_domain:v2"
    calculator: CalculateGeoMetricFormulas = field(
        default_factory=CalculateGeoMetricFormulas
    )

    async def execute(
        self,
        tenant_id: UUID,
        project_id: UUID,
        query: GeoOverviewQuery,
    ) -> GeoOverviewReport:
        business_date = self.clock.now().astimezone(_time_zone("Asia/Taipei")).date()
        report_source = await self.read_model.load_overview_report_source(
            tenant_id,
            project_id,
            query,
            business_date,
            self.normalizer_version,
        )
        if report_source is None:
            raise GeoMetricFormulaSourceProjectNotFound("project not found")
        queries = report_source.queries
        topics = report_source.topics
        formula_query = overview_formula_query(query)
        source = report_source.formula_source
        metrics = self.calculator.calculate(source, formula_query)
        metric_index = {
            (item.metric_name, item.scope_type, item.scope_value): item
            for item in metrics.metrics
        }
        current = _period_source(source, query.period_start, query.period_end)
        current_results = {item.run_result_id: item for item in current.run_results}
        query_index = {item.id: item for item in queries}
        topic_index = {item.id: item for item in topics}
        entity_sov = _entity_sov(current)
        return GeoOverviewReport(
            period_start=query.period_start,
            period_end=query.period_end,
            comparison_start=metrics.comparison_start,
            comparison_end=metrics.comparison_end,
            is_preparing=report_source.is_preparing,
            filter_options=report_source.filter_options,
            overview=_overview_kpis(metric_index, entity_sov, current),
            citation_summary=_citation_summary(current),
            visibility_trend=_visibility_trend(current, query),
            sentiment_trend=_sentiment_trend(current, query),
            entities=_entity_rows(current, metric_index, entity_sov),
            topics=_topic_rows(
                current,
                queries,
                topic_index,
                self.calculator,
                query,
            ),
            citation_urls=_citation_rows(
                current,
                current_results,
                query_index,
                scope="url",
            ),
            citation_domains=_citation_rows(
                current,
                current_results,
                query_index,
                scope="domain",
            ),
        )


@dataclass(frozen=True)
class ListGeoOverviewResponses:
    """分頁列出 Overview 回答摘要，並保留 semantic analysis 未完成的未知狀態。"""

    read_model: OverviewResponseReadModel

    async def execute(
        self,
        tenant_id: UUID,
        project_id: UUID,
        query: GeoOverviewQuery,
        *,
        query_id: UUID | None = None,
        mention_status: str = "all",
        page: int = 1,
        page_size: int = 20,
    ) -> GeoOverviewResponsePage:
        if mention_status not in {"all", "mentioned", "not_mentioned"}:
            raise ValueError("mentionStatus is invalid")
        if page < 1:
            raise ValueError("page must be at least 1")
        if not 1 <= page_size <= 100:
            raise ValueError("pageSize must be between 1 and 100")
        result = await self.read_model.load_overview_response_page(
            tenant_id,
            project_id,
            GeoOverviewResponsePageQuery(
                report_query=query,
                query_id=query_id,
                mention_status=mention_status,
                page=page,
                page_size=page_size,
            ),
        )
        if result is None:
            raise GeoMetricFormulaSourceProjectNotFound("project not found")
        return result


def _period_source(
    source: GeoMetricFormulaSource,
    start: datetime,
    end: datetime,
) -> GeoMetricFormulaSource:
    selected_ids = {
        item.run_result_id
        for item in source.run_results
        if start <= item.completed_at < end
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


def _overview_kpis(metrics, entity_sov, source) -> list[GeoOverviewKpi]:
    visibility = metrics.get(("visibility", "project", None))
    mentions = metrics.get(("mentions", "project", None))
    average = metrics.get(("average_position", "project", None))
    sov = metrics.get(("sov", "project", None))
    competitor_positions = [
        item.first_mention_order
        for item in source.entity_mentions
        if item.entity_role == "competitor"
        and item.mentioned
        and item.first_mention_order is not None
    ]
    competitor_sov = [
        value
        for entity_id, (role, _name, value) in entity_sov.items()
        if role == "competitor"
    ]
    cards = []
    if mentions and visibility:
        cards.append(_kpi(mentions, "覆蓋率", visibility.value, "percent"))
    if average:
        cards.append(
            _kpi(
                average,
                "競品最佳",
                min(competitor_positions) if competitor_positions else None,
                "position",
            )
        )
    if visibility:
        cards.append(_kpi(visibility, "產業均值", None, "percent"))
    if sov:
        cards.append(
            _kpi(
                sov,
                "次高",
                max(competitor_sov) if competitor_sov else None,
                "percent",
            )
        )
    return cards


def _kpi(metric, label, secondary, secondary_unit) -> GeoOverviewKpi:
    return GeoOverviewKpi(
        metric_name=metric.metric_name,
        value=metric.value,
        unit=metric.unit,
        numerator=metric.numerator,
        denominator=metric.denominator,
        secondary_label=label,
        secondary_value=secondary,
        secondary_unit=secondary_unit,
        delta=metric.delta,
        delta_unit=metric.delta_unit,
    )


def _entity_sov(source):
    mentioned = [
        item
        for item in source.entity_mentions
        if item.mentioned and item.entity_role in {"own_brand", "competitor"}
    ]
    total = len(mentioned)
    grouped = defaultdict(list)
    for item in mentioned:
        grouped[item.entity_id].append(item)
    return {
        entity_id: (
            items[0].entity_role,
            items[0].entity_name,
            _percent(len(items), total),
        )
        for entity_id, items in grouped.items()
    }


def _entity_rows(source, metrics, entity_sov) -> list[GeoOverviewEntityRow]:
    rows = []
    entities = {
        item.entity_id: (item.entity_role, item.entity_name)
        for item in source.entity_mentions
    }
    for entity_id, (role, name) in entities.items():
        visibility = metrics.get(("visibility", "entity", str(entity_id)))
        average = metrics.get(("average_position", "entity", str(entity_id)))
        if visibility is None or average is None:
            continue
        rows.append(
            GeoOverviewEntityRow(
                entity_id=entity_id,
                entity_name=name,
                entity_role=role,
                visibility_percent=visibility.value,
                visibility_delta_pp=visibility.delta,
                sov_percent=entity_sov.get(entity_id, (role, name, 0.0))[2],
                average_position=average.value,
            )
        )
    return sorted(rows, key=lambda item: (-item.visibility_percent, item.entity_name))


def _visibility_trend(source, query) -> list[GeoOverviewVisibilitySeries]:
    zone = _time_zone(query.time_zone)
    dates = _date_keys(query.period_start, query.period_end, zone)
    run_dates = {
        item.run_result_id: item.completed_at.astimezone(zone).date().isoformat()
        for item in source.run_results
    }
    totals = defaultdict(int)
    for date_key in run_dates.values():
        totals[date_key] += 1
    entities = {
        item.entity_id: (item.entity_name, item.entity_role)
        for item in source.entity_mentions
    }
    mentioned = defaultdict(set)
    for item in source.entity_mentions:
        if item.mentioned and item.run_result_id in run_dates:
            mentioned[(item.entity_id, run_dates[item.run_result_id])].add(
                item.run_result_id
            )
    return [
        GeoOverviewVisibilitySeries(
            entity_id=entity_id,
            entity_name=name,
            entity_role=role,
            points=[
                GeoOverviewTrendPoint(
                    date=date_key,
                    value=_percent(
                        len(mentioned[(entity_id, date_key)]), totals[date_key]
                    ),
                )
                for date_key in dates
            ],
        )
        for entity_id, (name, role) in sorted(
            entities.items(),
            key=lambda item: (
                0 if item[1][1] == "own_brand" else 1,
                item[1][0],
            ),
        )
    ]


def _sentiment_trend(source, query) -> list[GeoOverviewSentimentPoint]:
    zone = _time_zone(query.time_zone)
    dates = _date_keys(query.period_start, query.period_end, zone)
    run_dates = {
        item.run_result_id: item.completed_at.astimezone(zone).date().isoformat()
        for item in source.run_results
    }
    counts = defaultdict(lambda: {"positive": 0, "negative": 0})
    for item in source.sentiments:
        if item.entity_role == "own_brand" and item.run_result_id in run_dates:
            counts[run_dates[item.run_result_id]][item.sentiment] += 1
    return [
        GeoOverviewSentimentPoint(
            date=date_key,
            positive_count=counts[date_key]["positive"],
            negative_count=counts[date_key]["negative"],
            positive_negative_ratio=(
                round(
                    counts[date_key]["positive"] / counts[date_key]["negative"],
                    2,
                )
                if counts[date_key]["negative"]
                else None
            ),
        )
        for date_key in dates
    ]


def _date_keys(start, end, zone) -> list[str]:
    current = start.astimezone(zone).date()
    last = (end - timedelta(microseconds=1)).astimezone(zone).date()
    values = []
    while current <= last:
        values.append(current.isoformat())
        current += timedelta(days=1)
    return values


def _time_zone(value: str):
    try:
        return ZoneInfo(value)
    except ZoneInfoNotFoundError:
        if value == "Asia/Taipei":
            return timezone(timedelta(hours=8))
        raise


def _topic_rows(source, queries, topic_index, calculator, overview_query):
    rows = []
    grouped = defaultdict(list)
    for item in queries:
        grouped[item.topic_id].append(item)
    for topic_id, topic_queries in grouped.items():
        query_rows = [
            _query_row(source, item, calculator, overview_query)
            for item in topic_queries
        ]
        topic_source = _source_for_query_ids(
            source, {item.id for item in topic_queries}
        )
        stats = _scope_stats(topic_source, calculator, overview_query)
        rows.append(
            GeoOverviewTopicRow(
                topic_id=topic_id,
                topic_name=topic_index[topic_id].name
                if topic_id in topic_index
                else "未分類",
                visibility_percent=stats[0],
                sov_percent=stats[1],
                citation_count=len(topic_source.citations),
                queries=query_rows,
            )
        )
    return sorted(rows, key=lambda item: item.topic_name)


def _query_row(source, query_record, calculator, overview_query):
    query_source = _source_for_query_ids(source, {query_record.id})
    visibility, sov = _scope_stats(query_source, calculator, overview_query)
    return GeoOverviewQueryRow(
        query_id=query_record.id,
        query_text=query_record.query_text,
        visibility_percent=visibility,
        sov_percent=sov,
        citation_count=len(query_source.citations),
    )


def _scope_stats(source, calculator, overview_query):
    metrics = calculator.calculate(
        source,
        overview_formula_query(overview_query),
    ).metrics
    index = {(item.metric_name, item.scope_type): item.value for item in metrics}
    return index.get(("visibility", "project"), 0.0), index.get(("sov", "project"), 0.0)


def _source_for_query_ids(source, query_ids):
    selected_ids = {
        item.run_result_id for item in source.run_results if item.query_id in query_ids
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


def _citation_summary(source) -> GeoOverviewCitationSummary:
    owned = sum(item.ownership == "owned" for item in source.citations)
    cited_result_ids = {item.run_result_id for item in source.citations}
    return GeoOverviewCitationSummary(
        owned_share_percent=_percent(owned, len(source.citations)),
        citation_count=len(source.citations),
        cited_page_count=len({item.url for item in source.citations}),
        cited_response_percent=_percent(len(cited_result_ids), len(source.run_results)),
    )


def _citation_rows(source, run_results, queries, *, scope):
    grouped = defaultdict(list)
    for item in source.citations:
        grouped[item.url if scope == "url" else item.domain].append(item)
    total = len(source.citations)
    completed = len(source.run_results)
    rows = []
    for value, citations in grouped.items():
        run_ids = {item.run_result_id for item in citations}
        query_ids = {
            run_results[item_id].query_id
            for item_id in run_ids
            if item_id in run_results
        }
        ownerships = {item.ownership for item in citations}
        source_types = {item.source_type for item in citations}
        rows.append(
            GeoOverviewCitationRow(
                scope_type=scope,
                value=value,
                title=next((item.title for item in citations if item.title), None),
                citation_count=len(citations),
                query_count=len(query_ids & set(queries)),
                citation_rate_percent=_percent(len(run_ids), completed),
                citation_share_percent=_percent(len(citations), total),
                ownership=next(iter(ownerships)) if len(ownerships) == 1 else "mixed",
                source_type=next(iter(source_types))
                if len(source_types) == 1
                else "mixed",
            )
        )
    return sorted(rows, key=lambda item: (-item.citation_count, item.value))


def _percent(numerator: int, denominator: int) -> float:
    return round(numerator / denominator * 100, 2) if denominator else 0.0
