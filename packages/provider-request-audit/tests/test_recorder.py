import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
import younilab_provider_request_audit.postgres as postgres_module

from younilab_provider_request_audit import (
    MemoryProviderRequestRecorder,
    ProviderRequestContext,
    ProviderRequestExecutor,
    ProviderRequestUsage,
    UnconfiguredProviderRequestRecorder,
)


def _context() -> ProviderRequestContext:
    return ProviderRequestContext(
        platform_code="gemini",
        provider_code="google_vertex_ai",
        provider_operation="generate_content",
        use_case="geo_query_answer",
        source_service="geo-tracking-api",
        model="gemini-test",
        uses_grounding=True,
        query_id=uuid4(),
    )


@pytest.mark.anyio
async def test_executor_records_one_row_for_each_request() -> None:
    recorder = MemoryProviderRequestRecorder()
    executor = ProviderRequestExecutor(recorder, _context())

    assert await executor.execute(_successful_request, request_kind="initial") == "ok"
    assert (
        await executor.execute(_successful_request, request_kind="transient_retry")
        == "ok"
    )

    requests = list(recorder.requests.values())
    assert [request.request_number for request in requests] == [1, 2]
    assert [request.request_kind for request in requests] == [
        "initial",
        "transient_retry",
    ]
    assert requests[0].operation_id == requests[1].operation_id
    assert list(recorder.outcomes.values()) == ["succeeded", "succeeded"]


@pytest.mark.anyio
async def test_executor_records_usage_from_successful_response() -> None:
    recorder = MemoryProviderRequestRecorder()
    executor = ProviderRequestExecutor(recorder, _context())
    usage = ProviderRequestUsage(
        input_token_count=100,
        output_token_count=40,
        total_token_count=150,
        reasoning_token_count=10,
        meter_usage={"google_web_search_query": 2},
    )

    result = await executor.execute(
        _successful_request,
        request_kind="initial",
        read_usage=lambda _: usage,
    )

    request_id = next(iter(recorder.requests))
    assert result == "ok"
    assert recorder.usages[request_id] == usage
    assert recorder.usage_capture_statuses[request_id] == "recorded"


@pytest.mark.anyio
async def test_executor_keeps_success_when_usage_reader_fails() -> None:
    recorder = MemoryProviderRequestRecorder()
    executor = ProviderRequestExecutor(recorder, _context())

    def fail_usage_reader(result: str) -> ProviderRequestUsage:
        raise RuntimeError("invalid usage")

    result = await executor.execute(
        _successful_request,
        request_kind="initial",
        read_usage=fail_usage_reader,
    )

    request_id = next(iter(recorder.requests))
    assert result == "ok"
    assert request_id not in recorder.usages
    assert recorder.usage_capture_statuses[request_id] == "unavailable"


@pytest.mark.anyio
async def test_executor_rejects_invalid_usage_reader_value_without_retry() -> None:
    recorder = MemoryProviderRequestRecorder()
    executor = ProviderRequestExecutor(recorder, _context())

    result = await executor.execute(
        _successful_request,
        request_kind="initial",
        read_usage=lambda _: {"input_token_count": 10},  # type: ignore[arg-type]
    )

    request_id = next(iter(recorder.requests))
    assert result == "ok"
    assert request_id not in recorder.usages
    assert recorder.usage_capture_statuses[request_id] == "unavailable"


@pytest.mark.anyio
async def test_executor_marks_failed_usage_request_unavailable() -> None:
    recorder = MemoryProviderRequestRecorder()
    executor = ProviderRequestExecutor(recorder, _context())

    async def fail() -> str:
        raise TimeoutError("timeout")

    with pytest.raises(TimeoutError):
        await executor.execute(
            fail,
            request_kind="initial",
            read_usage=lambda _: ProviderRequestUsage(),
        )

    request_id = next(iter(recorder.requests))
    assert recorder.usage_capture_statuses[request_id] == "unavailable"


def test_provider_request_usage_rejects_negative_counts() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        ProviderRequestUsage(input_token_count=-1)


@pytest.mark.anyio
async def test_executor_records_failed_request_without_error_message() -> None:
    recorder = MemoryProviderRequestRecorder()
    executor = ProviderRequestExecutor(recorder, _context())

    async def fail() -> str:
        raise TimeoutError("sensitive provider response")

    with pytest.raises(TimeoutError):
        await executor.execute(fail, request_kind="initial")

    request_id = next(iter(recorder.requests))
    failure = recorder.failures[request_id]
    assert recorder.outcomes[request_id] == "failed"
    assert failure.error_type == "TimeoutError"
    assert not hasattr(failure, "error_message")


@pytest.mark.anyio
async def test_start_failure_prevents_provider_request() -> None:
    called = False
    executor = ProviderRequestExecutor(
        UnconfiguredProviderRequestRecorder(),
        _context(),
    )

    async def request() -> str:
        nonlocal called
        called = True
        return "ok"

    with pytest.raises(RuntimeError, match="not configured"):
        await executor.execute(request, request_kind="initial")

    assert called is False


@pytest.mark.anyio
async def test_postgres_recorder_creates_one_pool_for_concurrent_first_use(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pools: list[object] = []

    async def create_pool(database_url: str) -> object:
        pool = object()
        pools.append(pool)
        await asyncio.sleep(0)
        return pool

    monkeypatch.setattr(postgres_module.asyncpg, "create_pool", create_pool)
    recorder = postgres_module.PostgresProviderRequestRecorder(
        "postgresql://postgres:postgres@localhost/postgres"
    )

    first, second = await asyncio.gather(
        recorder._get_pool(),
        recorder._get_pool(),
    )

    assert len(pools) == 1
    assert first is second


@pytest.mark.anyio
async def test_postgres_recorder_serializes_usage_json() -> None:
    calls: list[tuple[str, tuple[object, ...]]] = []

    class FakePool:
        async def execute(self, query: str, *arguments: object) -> str:
            calls.append((query, arguments))
            return "UPDATE 1"

    recorder = postgres_module.PostgresProviderRequestRecorder(
        "postgresql://postgres:postgres@localhost/postgres"
    )
    recorder._pool = FakePool()  # type: ignore[assignment]
    usage = ProviderRequestUsage(
        input_token_count=10,
        output_token_count=4,
        traffic_type="ON_DEMAND",
        usage_metadata={"promptTokenCount": 10},
        meter_usage={"google_web_search_query": 2},
    )

    await recorder.succeed(
        uuid4(),
        completed_at=datetime.now(UTC),
        duration_ms=5,
        usage=usage,
        usage_capture_status="recorded",
    )

    _, arguments = calls[0]
    assert json.loads(arguments[12]) == {"promptTokenCount": 10}
    assert json.loads(arguments[13]) == {"google_web_search_query": 2}


async def _successful_request() -> str:
    return "ok"


def test_geo_baseline_keeps_one_row_per_provider_request_contract() -> None:
    baseline = (
        Path(__file__).parents[3]
        / "deploy"
        / "local"
        / "postgresql"
        / "baseline"
        / "geo_analysis.sql"
    ).read_text(encoding="utf-8")

    assert "CREATE TABLE public.provider_request" in baseline
    assert "ux_provider_request_operation_number UNIQUE" in baseline
    for field in (
        "request_kind",
        "platform_code",
        "provider_code",
        "provider_operation",
        "use_case",
        "source_service",
        "uses_grounding",
        "run_request_id",
    ):
        assert field in baseline


def test_geo_baseline_contains_provider_usage_rates_and_views() -> None:
    postgres_dir = (
        Path(__file__).parents[3]
        / "deploy"
        / "local"
        / "postgresql"
    )
    baseline = (postgres_dir / "baseline" / "geo_analysis.sql").read_text(
        encoding="utf-8"
    )
    pricing_seed = (postgres_dir / "seed" / "provider_pricing_rates.sql").read_text(
        encoding="utf-8"
    )

    for field in (
        "input_token_count",
        "output_token_count",
        "total_token_count",
        "cached_input_token_count",
        "reasoning_token_count",
        "tool_input_token_count",
        "usage_metadata",
        "meter_usage",
    ):
        assert field in baseline
    assert "CREATE TABLE public.provider_pricing_rate" in baseline
    assert "CREATE VIEW public.provider_request_cost_estimate" in baseline
    assert "CREATE VIEW public.provider_request_daily_cost_estimate" in baseline
    assert "estimated_list_cost_usd" in baseline
    assert pricing_seed.count("'30000000-0000-4000-8000-00000000000") == 7
    assert "ON CONFLICT DO NOTHING" in pricing_seed
    assert "free" not in baseline.lower()
