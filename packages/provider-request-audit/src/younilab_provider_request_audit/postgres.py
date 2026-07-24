import asyncio
import json
from datetime import datetime
from uuid import UUID

import asyncpg

from younilab_provider_request_audit.recorder import (
    ProviderRequestFailure,
    ProviderRequestStarted,
    ProviderRequestUsage,
)


class PostgresProviderRequestRecorder:
    def __init__(self, database_url: str) -> None:
        self._database_url = _asyncpg_database_url(database_url)
        self._pool: asyncpg.Pool | None = None
        self._pool_lock = asyncio.Lock()

    async def start(self, request: ProviderRequestStarted) -> None:
        context = request.context
        pool = await self._get_pool()
        await pool.execute(
            """
            INSERT INTO provider_request (
                id, operation_id, request_number, request_kind,
                platform_code, provider_code, provider_operation, use_case,
                source_service, model, uses_grounding, status, started_at,
                tenant_id, project_id, job_id, query_id, run_request_id,
                provider_region, usage_capture_status
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11,
                'started', $12, $13, $14, $15, $16, $17, $18, $19
            )
            """,
            request.id,
            request.operation_id,
            request.request_number,
            request.request_kind,
            context.platform_code,
            context.provider_code,
            context.provider_operation,
            context.use_case,
            context.source_service,
            context.model,
            context.uses_grounding,
            request.started_at,
            context.tenant_id,
            context.project_id,
            context.job_id,
            context.query_id,
            context.run_request_id,
            context.provider_region,
            "pending" if request.expects_usage else "not_applicable",
        )

    async def succeed(
        self,
        request_id: UUID,
        *,
        completed_at: datetime,
        duration_ms: int,
        http_status: int | None = None,
        usage: ProviderRequestUsage | None = None,
        usage_capture_status: str = "not_applicable",
    ) -> None:
        pool = await self._get_pool()
        result = await pool.execute(
            """
            UPDATE provider_request
            SET status = 'succeeded', completed_at = $2, duration_ms = $3,
                http_status = $4, usage_capture_status = $5,
                input_token_count = $6, output_token_count = $7,
                total_token_count = $8, cached_input_token_count = $9,
                reasoning_token_count = $10, tool_input_token_count = $11,
                traffic_type = $12, usage_metadata = $13, meter_usage = $14
            WHERE id = $1 AND status = 'started'
            """,
            request_id,
            completed_at,
            duration_ms,
            http_status,
            usage_capture_status,
            usage.input_token_count if usage else None,
            usage.output_token_count if usage else None,
            usage.total_token_count if usage else None,
            usage.cached_input_token_count if usage else None,
            usage.reasoning_token_count if usage else None,
            usage.tool_input_token_count if usage else None,
            usage.traffic_type if usage else None,
            _encode_json(usage.usage_metadata) if usage else None,
            _encode_json(usage.meter_usage if usage and usage.meter_usage else {}),
        )
        _ensure_updated(result, request_id)

    async def fail(
        self,
        request_id: UUID,
        *,
        completed_at: datetime,
        duration_ms: int,
        failure: ProviderRequestFailure,
    ) -> None:
        pool = await self._get_pool()
        result = await pool.execute(
            """
            UPDATE provider_request
            SET status = 'failed', completed_at = $2, duration_ms = $3,
                http_status = $4, error_code = $5, error_type = $6,
                usage_capture_status = CASE
                    WHEN usage_capture_status = 'pending' THEN 'unavailable'
                    ELSE usage_capture_status
                END
            WHERE id = $1 AND status = 'started'
            """,
            request_id,
            completed_at,
            duration_ms,
            failure.http_status,
            failure.error_code,
            failure.error_type,
        )
        _ensure_updated(result, request_id)

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

    async def _get_pool(self) -> asyncpg.Pool:
        if self._pool is None:
            async with self._pool_lock:
                if self._pool is None:
                    self._pool = await asyncpg.create_pool(self._database_url)
        return self._pool


def _asyncpg_database_url(database_url: str) -> str:
    return database_url.replace("postgresql+asyncpg://", "postgresql://", 1)


def _ensure_updated(result: str, request_id: UUID) -> None:
    if result != "UPDATE 1":
        raise RuntimeError(f"provider request {request_id} was not in started state")


def _encode_json(value: object | None) -> str | None:
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
