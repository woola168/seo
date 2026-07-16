import asyncio
from dataclasses import dataclass
from datetime import date

from younilab_seo.geo_analysis.application import DailySchedulerTickResult
from younilab_geo_analysis_scheduler.scheduler import GeoAnalysisScheduler


@dataclass
class FakeTick:
    error: Exception | None = None
    calls: int = 0

    async def execute(self) -> DailySchedulerTickResult:
        self.calls += 1
        if self.error is not None:
            raise self.error
        return DailySchedulerTickResult(
            due=True,
            business_date=date(2026, 7, 16),
        )


def test_run_once_executes_tick() -> None:
    async def run() -> None:
        tick = FakeTick()
        scheduler = GeoAnalysisScheduler(tick=tick)

        await scheduler.run_once()

        assert tick.calls == 1

    asyncio.run(run())
