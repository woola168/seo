import asyncio
import logging

from younilab_geo_analysis_scheduler.composition import build_dependencies
from younilab_geo_analysis_scheduler.scheduler import GeoAnalysisScheduler


async def _run() -> None:
    dependencies = build_dependencies()
    try:
        await GeoAnalysisScheduler(
            tick=dependencies.tick,
            poll_seconds=dependencies.poll_seconds,
        ).run()
    finally:
        await dependencies.close()


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    asyncio.run(_run())


if __name__ == "__main__":
    main()
