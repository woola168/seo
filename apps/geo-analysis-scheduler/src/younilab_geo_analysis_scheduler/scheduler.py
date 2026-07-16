import asyncio
import logging
from dataclasses import dataclass

from younilab_seo.geo_analysis.application import DailySchedulerTickResult, RunDailySchedulerTick


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GeoAnalysisScheduler:
    tick: RunDailySchedulerTick
    poll_seconds: float = 60

    async def run_once(self) -> DailySchedulerTickResult:
        result = await self.tick.execute()
        if (
            result.due
            or result.dispatched_jobs > 0
            or result.reconciled_jobs > 0
        ):
            logger.info(
                "GEO daily scheduler tick completed",
                extra=result.model_dump(mode="json"),
            )
        return result

    async def run(self) -> None:
        while True:
            try:
                await self.run_once()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("GEO daily scheduler tick failed")
            await asyncio.sleep(self.poll_seconds)
