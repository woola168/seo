from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from younilab_seo.geo_analysis.application.contracts import (
    GeoMetricEntityMentionInput,
    GeoMetricFormulaQuery,
    GeoMetricFormulaResult,
    GeoMetricFormulaSource,
    GeoMetricRunResultInput,
    GeoMetricSentimentInput,
    GeoMetricValue,
    GeoRunResultCitationFact,
)


@dataclass(frozen=True)
class _MetricInputs:
    run_results: list[GeoMetricRunResultInput]
    entity_mentions: list[GeoMetricEntityMentionInput]
    sentiments: list[GeoMetricSentimentInput]
    citations: list[GeoRunResultCitationFact]


@dataclass(frozen=True)
class CalculateGeoMetricFormulas:
    """依已正規化 facts 計算報表 metrics，不讀寫 persistence。"""

    def calculate(
        self,
        source: GeoMetricFormulaSource,
        query: GeoMetricFormulaQuery,
    ) -> GeoMetricFormulaResult:
        comparison_start, comparison_end = self._comparison_period(query)
        current = self._select_inputs(source, query, query.period_start, query.period_end)
        comparison = self._select_inputs(source, query, comparison_start, comparison_end)

        current_metrics = self._calculate_period_metrics(current)
        current_by_key = {self._metric_key(metric): metric for metric in current_metrics}
        comparison_metrics = {
            self._metric_key(metric): metric
            for metric in self._calculate_period_metrics(comparison)
        }
        metric_keys = list(current_by_key)
        metric_keys.extend(key for key in comparison_metrics if key not in current_by_key)

        metrics = [
            self._with_comparison(
                current_by_key.get(key) or self._zero_metric(comparison_metrics[key]),
                comparison_metrics.get(key),
            )
            for key in metric_keys
        ]
        return GeoMetricFormulaResult(
            period_start=query.period_start,
            period_end=query.period_end,
            comparison_start=comparison_start,
            comparison_end=comparison_end,
            metrics=metrics,
        )

    def _comparison_period(self, query: GeoMetricFormulaQuery) -> tuple[datetime, datetime]:
        if query.comparison_start is not None and query.comparison_end is not None:
            return query.comparison_start, query.comparison_end
        duration = query.period_end - query.period_start
        return query.period_start - duration, query.period_start

    def _select_inputs(
        self,
        source: GeoMetricFormulaSource,
        query: GeoMetricFormulaQuery,
        period_start: datetime,
        period_end: datetime,
    ) -> _MetricInputs:
        run_results = [
            item
            for item in source.run_results
            if period_start <= item.completed_at < period_end
            and self._matches_filters(item, query)
        ]
        run_result_ids = {item.run_result_id for item in run_results}
        return _MetricInputs(
            run_results=run_results,
            entity_mentions=[
                item
                for item in source.entity_mentions
                if item.run_result_id in run_result_ids
            ],
            sentiments=[
                item for item in source.sentiments if item.run_result_id in run_result_ids
            ],
            citations=[
                item for item in source.citations if item.run_result_id in run_result_ids
            ],
        )

    def _matches_filters(
        self,
        run_result: GeoMetricRunResultInput,
        query: GeoMetricFormulaQuery,
    ) -> bool:
        return (
            (query.query_id is None or run_result.query_id == query.query_id)
            and (query.topic_id is None or run_result.topic_id == query.topic_id)
            and (query.provider is None or run_result.provider == query.provider)
            and (query.region is None or run_result.region == query.region)
            and (query.language is None or run_result.language == query.language)
        )

    def _calculate_period_metrics(self, inputs: _MetricInputs) -> list[GeoMetricValue]:
        metrics: list[GeoMetricValue] = []
        metrics.extend(self._own_brand_metrics(inputs))
        metrics.extend(self._entity_metrics(inputs))
        metrics.append(self._sov_metric(inputs))
        metrics.extend(self._citation_metrics(inputs, by="url"))
        metrics.extend(self._citation_metrics(inputs, by="domain"))
        metrics.extend(self._sentiment_metrics(inputs))
        return metrics

    def _own_brand_metrics(self, inputs: _MetricInputs) -> list[GeoMetricValue]:
        own_brand_mentions = [
            item
            for item in inputs.entity_mentions
            if item.entity_role == "own_brand" and item.mentioned
        ]
        completed_count = len(inputs.run_results)
        mentioned_result_ids = {item.run_result_id for item in own_brand_mentions}
        mentioned_count = len(mentioned_result_ids)
        positions = [
            item.first_mention_order
            for item in own_brand_mentions
            if item.first_mention_order is not None
        ]
        return [
            GeoMetricValue(
                metric_name="visibility",
                scope_type="project",
                value=self._percent(mentioned_count, completed_count),
                unit="percent",
                numerator=mentioned_count,
                denominator=completed_count,
            ),
            GeoMetricValue(
                metric_name="mentions",
                scope_type="project",
                value=float(mentioned_count),
                unit="count",
                numerator=mentioned_count,
                denominator=completed_count,
            ),
            GeoMetricValue(
                metric_name="average_position",
                scope_type="project",
                value=self._average(positions),
                unit="position",
                numerator=sum(positions),
                denominator=len(positions),
            ),
        ]

    def _entity_metrics(self, inputs: _MetricInputs) -> list[GeoMetricValue]:
        by_entity: dict[UUID, list[GeoMetricEntityMentionInput]] = defaultdict(list)
        for item in inputs.entity_mentions:
            by_entity[item.entity_id].append(item)

        metrics: list[GeoMetricValue] = []
        completed_count = len(inputs.run_results)
        for entity_id, mentions in sorted(
            by_entity.items(),
            key=lambda item: (item[1][0].entity_role, item[1][0].entity_name),
        ):
            label = mentions[0].entity_name
            mentioned = [item for item in mentions if item.mentioned]
            mentioned_count = len({item.run_result_id for item in mentioned})
            positions = [
                item.first_mention_order
                for item in mentioned
                if item.first_mention_order is not None
            ]
            metrics.extend(
                [
                    GeoMetricValue(
                        metric_name="visibility",
                        scope_type="entity",
                        scope_value=str(entity_id),
                        scope_label=label,
                        value=self._percent(mentioned_count, completed_count),
                        unit="percent",
                        numerator=mentioned_count,
                        denominator=completed_count,
                    ),
                    GeoMetricValue(
                        metric_name="mentions",
                        scope_type="entity",
                        scope_value=str(entity_id),
                        scope_label=label,
                        value=float(mentioned_count),
                        unit="count",
                        numerator=mentioned_count,
                        denominator=completed_count,
                    ),
                    GeoMetricValue(
                        metric_name="average_position",
                        scope_type="entity",
                        scope_value=str(entity_id),
                        scope_label=label,
                        value=self._average(positions),
                        unit="position",
                        numerator=sum(positions),
                        denominator=len(positions),
                    ),
                ]
            )
        return metrics

    def _sov_metric(self, inputs: _MetricInputs) -> GeoMetricValue:
        configured_mentions = [
            item
            for item in inputs.entity_mentions
            if item.entity_role in {"own_brand", "competitor"} and item.mentioned
        ]
        own_brand_count = len(
            [item for item in configured_mentions if item.entity_role == "own_brand"]
        )
        return GeoMetricValue(
            metric_name="sov",
            scope_type="project",
            value=self._percent(own_brand_count, len(configured_mentions)),
            unit="percent",
            numerator=own_brand_count,
            denominator=len(configured_mentions),
        )

    def _citation_metrics(
        self,
        inputs: _MetricInputs,
        *,
        by: str,
    ) -> list[GeoMetricValue]:
        groups: dict[str, list[GeoRunResultCitationFact]] = defaultdict(list)
        for citation in inputs.citations:
            key = citation.url if by == "url" else citation.domain
            groups[key].append(citation)

        total_citation_rows = len(inputs.citations)
        completed_count = len(inputs.run_results)
        scope_type = "citation_url" if by == "url" else "citation_domain"
        metrics: list[GeoMetricValue] = []
        for value, citations in sorted(groups.items()):
            citation_count = len(citations)
            used_count = len({item.run_result_id for item in citations})
            metrics.extend(
                [
                    GeoMetricValue(
                        metric_name="citation_count",
                        scope_type=scope_type,
                        scope_value=value,
                        scope_label=value,
                        value=float(citation_count),
                        unit="count",
                        numerator=citation_count,
                        denominator=total_citation_rows,
                    ),
                    GeoMetricValue(
                        metric_name="used_percent",
                        scope_type=scope_type,
                        scope_value=value,
                        scope_label=value,
                        value=self._percent(used_count, completed_count),
                        unit="percent",
                        numerator=used_count,
                        denominator=completed_count,
                    ),
                    GeoMetricValue(
                        metric_name="share_percent",
                        scope_type=scope_type,
                        scope_value=value,
                        scope_label=value,
                        value=self._percent(citation_count, total_citation_rows),
                        unit="percent",
                        numerator=citation_count,
                        denominator=total_citation_rows,
                    ),
                ]
            )
        return metrics

    def _sentiment_metrics(self, inputs: _MetricInputs) -> list[GeoMetricValue]:
        counts: dict[str, int] = defaultdict(int)
        for sentiment in inputs.sentiments:
            counts[sentiment.sentiment] += 1

        return [
            GeoMetricValue(
                metric_name="sentiment_count",
                scope_type="sentiment",
                scope_value=sentiment,
                scope_label=sentiment,
                value=float(count),
                unit="count",
                numerator=count,
                denominator=len(inputs.sentiments),
            )
            for sentiment, count in sorted(counts.items())
        ]

    def _with_comparison(
        self,
        current: GeoMetricValue,
        comparison: GeoMetricValue | None,
    ) -> GeoMetricValue:
        if current.unit == "position":
            comparison_value = self._position_comparison_value(comparison)
            delta = (
                current.value - comparison_value
                if current.denominator not in (None, 0)
                and comparison_value is not None
                else None
            )
            return current.model_copy(
                update={
                    "comparison_value": comparison_value,
                    "delta": delta,
                    "delta_unit": "position" if delta is not None else None,
                }
            )

        comparison_value = comparison.value if comparison is not None else 0.0
        return current.model_copy(
            update={
                "comparison_value": comparison_value,
                "delta": current.value - comparison_value,
                "delta_unit": self._delta_unit(current),
            }
        )

    def _metric_key(self, metric: GeoMetricValue) -> tuple[str, str, str | None]:
        return metric.metric_name, metric.scope_type, metric.scope_value

    def _delta_unit(self, metric: GeoMetricValue) -> str:
        if metric.unit == "percent":
            return "pp"
        if metric.unit == "position":
            return "position"
        return "count"

    def _zero_metric(self, comparison: GeoMetricValue) -> GeoMetricValue:
        return comparison.model_copy(
            update={
                "value": 0.0,
                "numerator": 0.0,
                "denominator": 0.0,
            }
        )

    def _position_comparison_value(self, comparison: GeoMetricValue | None) -> float | None:
        if comparison is None or comparison.denominator in (None, 0):
            return None
        return comparison.value

    def _percent(self, numerator: int | float, denominator: int | float) -> float:
        if denominator == 0:
            return 0.0
        return float(numerator) / float(denominator) * 100

    def _average(self, values: list[int]) -> float:
        if not values:
            return 0.0
        return float(sum(values)) / len(values)
