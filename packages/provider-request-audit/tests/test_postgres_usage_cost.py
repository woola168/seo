import os
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import asyncpg
import pytest


@pytest.mark.anyio
async def test_usage_cost_baseline_and_views_with_postgresql() -> None:
    database_url = os.getenv("GEO_ANALYSIS_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip(
            "Set GEO_ANALYSIS_TEST_DATABASE_URL to run provider usage integration tests."
        )
    connection = await asyncpg.connect(
        database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
    )
    schema = f"provider_usage_{uuid4().hex}"
    postgres_dir = Path(__file__).parents[3] / "deploy" / "local" / "postgresql"
    try:
        await connection.execute(f'CREATE SCHEMA "{schema}"')
        baseline = (postgres_dir / "baseline" / "geo_analysis.sql").read_text(
            encoding="utf-8"
        )
        baseline = "\n".join(
            line for line in baseline.splitlines() if not line.startswith("\\")
        ).replace("public.", f'"{schema}".')
        await connection.execute(baseline)
        await connection.execute(f'SET search_path TO "{schema}"')
        await connection.execute(
            (postgres_dir / "seed" / "provider_pricing_rates.sql").read_text(
                encoding="utf-8"
            )
        )
        await connection.execute(
            """
            INSERT INTO provider_request (
                id, operation_id, request_number, request_kind,
                platform_code, provider_code, provider_operation, use_case,
                source_service, model, uses_grounding, status, started_at,
                provider_region, traffic_type, usage_capture_status,
                input_token_count, output_token_count, total_token_count,
                cached_input_token_count, reasoning_token_count,
                tool_input_token_count, meter_usage
            ) VALUES
                (
                    '40000000-0000-4000-8000-000000000001',
                    '41000000-0000-4000-8000-000000000001', 1, 'initial',
                    'gemini', 'google_vertex_ai', 'generate_content',
                    'geo_query_answer', 'test', 'gemini-3.1-flash-lite', true,
                    'succeeded', '2026-07-24T00:00:00Z', 'global',
                    'ON_DEMAND', 'recorded', 1000, 100, 1350, 200, 50, 300,
                    '{"google_web_search_query": 2}'::jsonb
                ),
                (
                    '40000000-0000-4000-8000-000000000002',
                    '41000000-0000-4000-8000-000000000002', 1, 'initial',
                    'gemini', 'google_vertex_ai', 'generate_content',
                    'project_inspection', 'test', 'gemini-3.1-flash-lite', false,
                    'succeeded', '2026-07-24T00:00:00Z', 'us-central1',
                    'ON_DEMAND', 'recorded', 1000, 100, 1400, 0, 0, 300,
                    '{}'::jsonb
                ),
                (
                    '40000000-0000-4000-8000-000000000003',
                    '41000000-0000-4000-8000-000000000003', 1, 'initial',
                    'gemini', 'google_vertex_ai', 'generate_content',
                    'query_generation', 'test', 'unknown-model', false,
                    'succeeded', '2026-07-24T00:00:00Z', 'global',
                    'ON_DEMAND', 'recorded', 10, 5, 15, 0, 0, 0, '{}'::jsonb
                )
            """
        )

        rows = await connection.fetch(
            """
            SELECT use_case, billable_input_token_count,
                   google_web_search_query_count, estimation_status,
                   estimated_list_cost_usd
            FROM provider_request_cost_estimate
            ORDER BY id
            """
        )

        assert dict(rows[0]) == {
            "use_case": "geo_query_answer",
            "billable_input_token_count": 800,
            "google_web_search_query_count": 2,
            "estimation_status": "estimated",
            "estimated_list_cost_usd": Decimal("0.028430000000000000000000000000"),
        }
        assert dict(rows[1]) == {
            "use_case": "project_inspection",
            "billable_input_token_count": 1300,
            "google_web_search_query_count": 0,
            "estimation_status": "estimated",
            "estimated_list_cost_usd": Decimal(
                "0.0005225000000000000000000000000000"
            ),
        }
        assert rows[2]["estimation_status"] == "rate_missing"
        assert rows[2]["estimated_list_cost_usd"] is None

        daily = await connection.fetchrow(
            """
            SELECT request_count, estimated_request_count,
                   unestimated_request_count, estimated_list_cost_usd
            FROM provider_request_daily_cost_estimate
            WHERE usage_date = '2026-07-24'
              AND use_case = 'geo_query_answer'
            """
        )
        assert daily is not None
        assert daily["request_count"] == 1
        assert daily["estimated_request_count"] == 1
        assert daily["unestimated_request_count"] == 0
        assert daily["estimated_list_cost_usd"] == Decimal(
            "0.028430000000000000000000000000"
        )

        with pytest.raises(asyncpg.CheckViolationError):
            await connection.execute(
                """
                UPDATE provider_request
                SET input_token_count = -1
                WHERE id = '40000000-0000-4000-8000-000000000001'
                """
            )
    finally:
        await connection.execute("ROLLBACK")
        await connection.execute("RESET search_path")
        await connection.execute(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')
        await connection.close()
