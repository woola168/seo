import asyncio
from pathlib import Path
from uuid import uuid4

import pytest
import younilab_provider_request_audit.postgres as postgres_module

from younilab_provider_request_audit import (
    MemoryProviderRequestRecorder,
    ProviderRequestContext,
    ProviderRequestExecutor,
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


async def _successful_request() -> str:
    return "ok"


def test_provider_request_migration_keeps_one_row_per_request_contract() -> None:
    migration = (
        Path(__file__).parents[3]
        / "deploy"
        / "local"
        / "postgresql"
        / "018_provider_request_audit.sql"
    ).read_text(encoding="utf-8")

    assert "CREATE TABLE IF NOT EXISTS provider_request" in migration
    assert "UNIQUE (operation_id, request_number)" in migration
    assert "input_token_count" not in migration
    assert "output_token_count" not in migration
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
        assert field in migration
