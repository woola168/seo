from collections import defaultdict
from dataclasses import dataclass, field
from uuid import UUID

from younilab_seo.geo_analysis.application.contracts import (
    GeoDashboardCitationRow,
    GeoDashboardEntityRow,
    GeoDashboardMetricValue,
    GeoDashboardOverviewCard,
    GeoDashboardReport,
    GeoDashboardSentimentRow,
    GeoMetricFormulaQuery,
    GeoMetricFormulaSource,
    GeoMetricValue,
)
from younilab_seo.geo_analysis.application.use_cases.metric_source import (
    BuildGeoMetricFormulaSource,
)
from younilab_seo.geo_analysis.application.use_cases.metrics_formula import (
    CalculateGeoMetricFormulas,
)


@dataclass(frozen=True)
class GetGeoDashboardReport:
    """把 facts 與 flat metrics 組成 dashboard read model，不保存資料。"""

    source_builder: BuildGeoMetricFormulaSource
    calculator: CalculateGeoMetricFormulas = field(
        default_factory=CalculateGeoMetricFormulas
    )

    async def execute(
        self,
        tenant_id: UUID,
        project_id: UUID,
        query: GeoMetricFormulaQuery,
    ) -> GeoDashboardReport:
        source_query = self._with_explicit_comparison(query)
        source = await self.source_builder.execute(tenant_id, project_id, source_query)
        metrics = self.calculator.calculate(source, source_query)
        metric_index = {
            (metric.metric_name, metric.scope_type, metric.scope_value): metric
            for metric in metrics.metrics
        }
        return GeoDashboardReport(
            period_start=metrics.period_start,
            period_end=metrics.period_end,
            comparison_start=metrics.comparison_start,
            comparison_end=metrics.comparison_end,
            overview=self._overview(metric_index),
            entities=self._entities(source, metric_index),
            citation_urls=self._citations(source, metric_index, scope="url"),
            citation_domains=self._citations(source, metric_index, scope="domain"),
            sentiments=self._sentiments(metric_index),
        )

    def _with_explicit_comparison(
        self,
        query: GeoMetricFormulaQuery,
    ) -> GeoMetricFormulaQuery:
        if query.comparison_start is not None and query.comparison_end is not None:
            return query
        duration = query.period_end - query.period_start
        return query.model_copy(
            update={
                "comparison_start": query.period_start - duration,
                "comparison_end": query.period_start,
            }
        )

    def _overview(
        self,
        metrics: dict[tuple[str, str, str | None], GeoMetricValue],
    ) -> list[GeoDashboardOverviewCard]:
        labels = {
            "visibility": "Visibility",
            "mentions": "Mentions",
            "sov": "SOV",
            "average_position": "Average Position",
        }
        return [
            GeoDashboardOverviewCard(
                metric_name=metric_name,
                label=label,
                metric=self._metric_value(
                    metrics[(metric_name, "project", None)]
                ),
            )
            for metric_name, label in labels.items()
            if (metric_name, "project", None) in metrics
        ]

    def _entities(
        self,
        source: GeoMetricFormulaSource,
        metrics: dict[tuple[str, str, str | None], GeoMetricValue],
    ) -> list[GeoDashboardEntityRow]:
        entities: dict[UUID, tuple[str, str]] = {}
        for mention in source.entity_mentions:
            entities.setdefault(
                mention.entity_id,
                (mention.entity_role, mention.entity_name),
            )
        return [
            GeoDashboardEntityRow(
                entity_id=entity_id,
                entity_role=role,
                entity_name=name,
                visibility=self._metric_value(
                    metrics[("visibility", "entity", str(entity_id))]
                ),
                mentions=self._metric_value(
                    metrics[("mentions", "entity", str(entity_id))]
                ),
                average_position=self._metric_value(
                    metrics[("average_position", "entity", str(entity_id))]
                ),
            )
            for entity_id, (role, name) in sorted(
                entities.items(),
                key=lambda item: (item[1][0], item[1][1]),
            )
            if ("visibility", "entity", str(entity_id)) in metrics
            and ("mentions", "entity", str(entity_id)) in metrics
            and ("average_position", "entity", str(entity_id)) in metrics
        ]

    def _citations(
        self,
        source: GeoMetricFormulaSource,
        metrics: dict[tuple[str, str, str | None], GeoMetricValue],
        *,
        scope: str,
    ) -> list[GeoDashboardCitationRow]:
        scope_type = "citation_url" if scope == "url" else "citation_domain"
        groups = defaultdict(list)
        for citation in source.citations:
            key = citation.url if scope == "url" else citation.domain
            groups[key].append(citation)

        rows: list[GeoDashboardCitationRow] = []
        for value, citations in sorted(groups.items()):
            if ("citation_count", scope_type, value) not in metrics:
                continue
            rows.append(
                GeoDashboardCitationRow(
                    scope_type=scope,
                    value=value,
                    label=value,
                    ownership=self._single_or_mixed(
                        {citation.ownership for citation in citations}
                    ),
                    source_type=self._single_or_mixed(
                        {citation.source_type for citation in citations}
                    ),
                    citation_count=self._metric_value(
                        metrics[("citation_count", scope_type, value)]
                    ),
                    used_percent=self._metric_value(
                        metrics[("used_percent", scope_type, value)]
                    ),
                    share_percent=self._metric_value(
                        metrics[("share_percent", scope_type, value)]
                    ),
                )
            )
        return rows

    def _sentiments(
        self,
        metrics: dict[tuple[str, str, str | None], GeoMetricValue],
    ) -> list[GeoDashboardSentimentRow]:
        rows = []
        for sentiment in ("positive", "negative"):
            metric = metrics.get(("sentiment_count", "sentiment", sentiment))
            if metric is None:
                continue
            rows.append(
                GeoDashboardSentimentRow(
                    sentiment=sentiment,
                    statement_count=self._metric_value(metric),
                )
            )
        return rows

    def _metric_value(self, metric: GeoMetricValue) -> GeoDashboardMetricValue:
        return GeoDashboardMetricValue(
            value=metric.value,
            unit=metric.unit,
            numerator=metric.numerator,
            denominator=metric.denominator,
            comparison_value=metric.comparison_value,
            delta=metric.delta,
            delta_unit=metric.delta_unit,
        )

    def _single_or_mixed(self, values: set[str]) -> str | None:
        if not values:
            return None
        if len(values) == 1:
            return next(iter(values))
        return "mixed"
