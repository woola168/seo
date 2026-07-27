from dataclasses import dataclass
from uuid import UUID

from younilab_seo.geo_analysis.application.contracts import (
    GeoMetricFormulaQuery,
    GeoMetricFormulaSource,
)
from younilab_seo.geo_analysis.application.interfaces.metrics import (
    MetricsReadPersistence,
)
from younilab_seo.geo_analysis.application.use_cases.citation_normalization import (
    DEFAULT_CITATION_NORMALIZER_VERSION,
)


class GeoMetricFormulaSourceProjectNotFound(LookupError):
    """找不到指定 project 時，停止組裝報表公式輸入。"""


@dataclass(frozen=True)
class BuildGeoMetricFormulaSource:
    """從 persistence read model 組出 metrics formula source，不計算 metrics。"""

    repository: MetricsReadPersistence
    normalizer_version: str = DEFAULT_CITATION_NORMALIZER_VERSION

    async def execute(
        self,
        tenant_id: UUID,
        project_id: UUID,
        query: GeoMetricFormulaQuery,
    ) -> GeoMetricFormulaSource:
        source_query = self._with_explicit_comparison(query)
        source = await self.repository.load_metric_formula_source(
            tenant_id,
            project_id,
            source_query,
            self.normalizer_version,
        )
        if source is None:
            raise GeoMetricFormulaSourceProjectNotFound("project not found")
        return source

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
