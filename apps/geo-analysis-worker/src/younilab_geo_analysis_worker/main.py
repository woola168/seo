import asyncio
import logging

from younilab_geo_analysis_worker.composition import build_dependencies
from younilab_geo_analysis_worker.worker import GeoAnalysisWorker


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    dependencies = build_dependencies()
    try:
        await GeoAnalysisWorker(
            consumer=dependencies.consumer,
            processor=dependencies.processor,
        ).run()
    finally:
        await dependencies.close()


if __name__ == "__main__":
    asyncio.run(main())
