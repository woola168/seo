from dataclasses import dataclass
from typing import Any

from younilab_seo.geo_analysis.application import ProcessQueryRunJobMessage


@dataclass(frozen=True)
class GeoAnalysisWorker:
    consumer: Any
    processor: ProcessQueryRunJobMessage

    async def run(self) -> None:
        await self.consumer.run(self.processor.execute)
