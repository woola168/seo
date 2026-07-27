from typing import Protocol, runtime_checkable
from uuid import UUID

from younilab_seo.geo_analysis.application.contracts import (
    GeoMetricFormulaQuery,
    GeoMetricFormulaSource,
)


@runtime_checkable
class MetricsReadPersistence(Protocol):
    """載入 metrics workflow 所需的已篩選公式輸入。"""

    async def load_metric_formula_source(
        self,
        tenant_id: UUID,
        project_id: UUID,
        query: GeoMetricFormulaQuery,
        normalizer_version: str,
    ) -> GeoMetricFormulaSource | None: ...
