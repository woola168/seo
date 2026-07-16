import os
from dataclasses import dataclass
from datetime import UTC, datetime, time
from zoneinfo import ZoneInfo

from younilab_seo.geo_analysis.application import DispatchQueryRunJob, RunDailySchedulerTick
from younilab_seo.geo_analysis.infrastructure.messaging import RabbitMqMessagePublisher
from younilab_seo.geo_analysis.infrastructure.persistence.postgres import (
    build_postgres_repository,
)


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC).replace(microsecond=0)


@dataclass(frozen=True)
class GeoAnalysisSchedulerDependencies:
    tick: RunDailySchedulerTick
    publisher: RabbitMqMessagePublisher
    poll_seconds: float

    async def close(self) -> None:
        await self.publisher.close()


def build_dependencies() -> GeoAnalysisSchedulerDependencies:
    repository = build_postgres_repository(_required_env("GEO_ANALYSIS_DATABASE_URL"))
    publisher = RabbitMqMessagePublisher(
        url=_required_env("GEO_ANALYSIS_RABBITMQ_URL")
    )
    clock = SystemClock()
    dispatcher = DispatchQueryRunJob(repository, publisher, clock)
    return GeoAnalysisSchedulerDependencies(
        tick=RunDailySchedulerTick(
            repository=repository,
            dispatcher=dispatcher,
            clock=clock,
            callback_base_url=os.getenv(
                "GEO_ANALYSIS_CALLBACK_BASE_URL",
                "http://geo-analysis-api:8002",
            ),
            timezone=ZoneInfo(os.getenv("GEO_SCHEDULER_TIMEZONE", "Asia/Taipei")),
            daily_time=_daily_time(os.getenv("GEO_SCHEDULER_DAILY_TIME", "03:00")),
        ),
        publisher=publisher,
        poll_seconds=float(os.getenv("GEO_SCHEDULER_POLL_SECONDS", "60")),
    )


def _daily_time(value: str) -> time:
    try:
        hour, minute = (int(part) for part in value.split(":"))
        return time(hour, minute)
    except (TypeError, ValueError) as exc:
        raise RuntimeError("GEO_SCHEDULER_DAILY_TIME must use HH:MM") from exc


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} is required")
    return value
