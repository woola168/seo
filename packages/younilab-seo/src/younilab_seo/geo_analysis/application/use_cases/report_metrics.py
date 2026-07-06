from dataclasses import dataclass, field
from uuid import UUID

from younilab_seo.geo_analysis.application.contracts import (
    GeoMetricFormulaQuery,
    GeoMetricFormulaResult,
)
from younilab_seo.geo_analysis.application.use_cases.metric_source import (
    BuildGeoMetricFormulaSource,
)
from younilab_seo.geo_analysis.application.use_cases.metrics_formula import (
    CalculateGeoMetricFormulas,
)


@dataclass(frozen=True)
class CalculateGeoReportMetrics:
    """組合 metrics source assembly 與公式核心，產出報表 metrics。"""

    source_builder: BuildGeoMetricFormulaSource
    calculator: CalculateGeoMetricFormulas = field(
        default_factory=CalculateGeoMetricFormulas
    )

    async def execute(
        self,
        tenant_id: UUID,
        project_id: UUID,
        query: GeoMetricFormulaQuery,
    ) -> GeoMetricFormulaResult:
        source_query = self._with_explicit_comparison(query)
        source = await self.source_builder.execute(tenant_id, project_id, source_query)
        return self.calculator.calculate(source, source_query)

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
