import os
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType
from uuid import uuid4

import asyncpg
import pytest
from sqlalchemy import Boolean, Date, DateTime, Integer, JSON, Numeric, String, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql.schema import CheckConstraint, UniqueConstraint
from younilab_provider_request_audit import (
    PostgresProviderRequestRecorder,
    ProviderRequestContext,
    ProviderRequestStarted,
    ProviderRequestUsage,
)

from younilab_seo.access_control.infrastructure.persistence.postgres import (
    models as access_control_models,
)
from younilab_seo.geo_analysis.infrastructure.persistence.postgres import (
    models as geo_analysis_models,
)
from younilab_seo.resource_catalog.infrastructure.persistence.postgres import (
    models as resource_catalog_models,
)


POSTGRES_DIR = Path(__file__).parents[3] / "deploy" / "local" / "postgresql"


def _model_tables(module: ModuleType) -> dict[str, object]:
    tables = {}
    for value in vars(module).values():
        table = getattr(value, "__table__", None)
        if table is not None and table.name not in tables:
            tables[table.name] = table
    return tables


def _schema_sql(baseline_name: str, schema: str) -> str:
    sql = (POSTGRES_DIR / "baseline" / baseline_name).read_text(encoding="utf-8")
    return "\n".join(
        line for line in sql.splitlines() if not line.startswith("\\")
    ).replace("public.", f'"{schema}".')


@pytest.mark.parametrize(
    "baseline_name",
    ["access_control.sql", "resource_catalog.sql", "geo_analysis.sql"],
)
def test_baseline_fails_fast_and_is_atomic(baseline_name: str) -> None:
    sql = (POSTGRES_DIR / "baseline" / baseline_name).read_text(encoding="utf-8")

    assert "\\set ON_ERROR_STOP on" in sql
    assert sql.index("BEGIN;") < sql.index("CREATE TABLE")
    assert sql.index("COMMIT;") > sql.rindex("ALTER TABLE")


def _assert_type_contract(column: object, actual: asyncpg.Record) -> None:
    column_type = column.type
    if type(column_type).__name__ == "AutoString":
        column_type = String()
    data_type = actual["data_type"]
    if isinstance(column_type, Text):
        assert data_type == "text"
    elif isinstance(column_type, String):
        assert data_type == "character varying"
        if column_type.length is not None:
            assert actual["character_maximum_length"] == column_type.length
    elif isinstance(column_type, DateTime):
        expected = "timestamp with time zone" if column_type.timezone else "timestamp without time zone"
        assert data_type == expected
    elif isinstance(column_type, Uuid):
        assert actual["udt_name"] == "uuid"
    elif isinstance(column_type, Boolean):
        assert data_type == "boolean"
    elif isinstance(column_type, Integer):
        assert data_type == "integer"
    elif isinstance(column_type, Numeric):
        assert data_type == "numeric"
        assert actual["numeric_precision"] == column_type.precision
        assert actual["numeric_scale"] == column_type.scale
    elif isinstance(column_type, Date):
        assert data_type == "date"
    elif isinstance(column_type, (JSON, JSONB)):
        assert actual["udt_name"] in {"json", "jsonb"}
    else:
        raise AssertionError(f"Unsupported model type: {column_type!r}")


async def _assert_model_contract(
    connection: asyncpg.Connection,
    schema: str,
    models: ModuleType,
) -> None:
    model_tables = _model_tables(models)
    column_rows = await connection.fetch(
        """
        SELECT table_name, column_name, is_nullable, data_type, udt_name,
               character_maximum_length, numeric_precision, numeric_scale,
               column_default, is_generated, generation_expression
        FROM information_schema.columns
        WHERE table_schema = $1
        """,
        schema,
    )
    actual_columns = {
        (row["table_name"], row["column_name"]): row for row in column_rows
    }

    assert model_tables.keys() <= {row["table_name"] for row in column_rows}
    for table_name, table in model_tables.items():
        actual_names = {
            row["column_name"]
            for row in column_rows
            if row["table_name"] == table_name
        }
        assert actual_names == set(table.columns.keys()), table_name
        for column in table.columns:
            actual = actual_columns[(table_name, column.name)]
            if actual["is_generated"] != "ALWAYS":
                assert (actual["is_nullable"] == "YES") is column.nullable
            _assert_type_contract(column, actual)
            if column.server_default is not None and actual["is_generated"] != "ALWAYS":
                assert actual["column_default"] is not None

    foreign_key_rows = await connection.fetch(
        """
        SELECT tc.table_name, tc.constraint_name, kcu.column_name,
               ccu.table_name AS foreign_table_name,
               ccu.column_name AS foreign_column_name
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
          ON tc.constraint_catalog = kcu.constraint_catalog
         AND tc.constraint_schema = kcu.constraint_schema
         AND tc.constraint_name = kcu.constraint_name
        JOIN information_schema.constraint_column_usage ccu
          ON tc.constraint_catalog = ccu.constraint_catalog
         AND tc.constraint_schema = ccu.constraint_schema
         AND tc.constraint_name = ccu.constraint_name
        WHERE tc.constraint_schema = $1 AND tc.constraint_type = 'FOREIGN KEY'
        """,
        schema,
    )
    actual_foreign_keys = [
        (
            row["table_name"],
            row["column_name"],
            row["foreign_table_name"],
            row["foreign_column_name"],
        )
        for row in foreign_key_rows
        if row["table_name"] in model_tables
    ]
    expected_foreign_keys = {
        (table.name, column.name, foreign.column.table.name, foreign.column.name)
        for table in model_tables.values()
        for column in table.columns
        for foreign in column.foreign_keys
    }
    assert set(actual_foreign_keys) == expected_foreign_keys
    assert len(actual_foreign_keys) == len(set(actual_foreign_keys))

    constraint_rows = await connection.fetch(
        """
        SELECT rel.relname AS table_name, con.conname AS constraint_name,
               con.contype AS constraint_type
        FROM pg_constraint con
        JOIN pg_class rel ON rel.oid = con.conrelid
        JOIN pg_namespace ns ON ns.oid = rel.relnamespace
        WHERE ns.nspname = $1
        """,
        schema,
    )
    actual_constraints = {
        (row["table_name"], row["constraint_name"]): row[
            "constraint_type"
        ].decode()
        for row in constraint_rows
    }
    for table in model_tables.values():
        for constraint in table.constraints:
            if isinstance(constraint, UniqueConstraint) and constraint.name:
                assert actual_constraints[(table.name, constraint.name)] == "u"
            if isinstance(constraint, CheckConstraint) and constraint.name:
                assert actual_constraints[(table.name, constraint.name)] == "c"

    index_rows = await connection.fetch(
        """
        SELECT tablename, indexname, indexdef
        FROM pg_indexes
        WHERE schemaname = $1
        """,
        schema,
    )
    actual_indexes = {
        (row["tablename"], row["indexname"]): row["indexdef"]
        for row in index_rows
    }
    for table in model_tables.values():
        for index in table.indexes:
            definition = actual_indexes.get((table.name, index.name))
            if definition is None:
                expected_prefix = ", ".join(column.name for column in index.columns)
                definition = next(
                    candidate
                    for (table_name, _), candidate in actual_indexes.items()
                    if table_name == table.name
                    and f"({expected_prefix}" in candidate
                )
            if index.unique:
                assert "CREATE UNIQUE INDEX" in definition


async def _assert_geo_raw_sql_contract(
    connection: asyncpg.Connection,
    database_url: str,
    schema: str,
) -> None:
    columns = {
        (row["table_name"], row["column_name"]): row
        for row in await connection.fetch(
            """
            SELECT table_name, column_name, column_default,
                   is_generated, generation_expression
            FROM information_schema.columns
            WHERE table_schema = $1
              AND table_name IN ('geo_query_run_job', 'geo_daily_run_batch')
            """,
            schema,
        )
    }
    assert "{}" in columns[("geo_query_run_job", "execution_snapshot")][
        "column_default"
    ]
    assert "false" in columns[("geo_daily_run_batch", "budget_enforced")][
        "column_default"
    ]
    business_date = columns[("geo_query_run_job", "business_date")]
    assert business_date["is_generated"] == "ALWAYS"
    assert "Asia/Taipei" in business_date["generation_expression"]

    indexes = {
        row["indexname"]: row["indexdef"]
        for row in await connection.fetch(
            "SELECT indexname, indexdef FROM pg_indexes WHERE schemaname = $1",
            schema,
        )
    }
    assert " WHERE " in indexes["ux_geo_query_run_job_daily_slot"]
    assert " WHERE " in indexes["ix_geo_query_run_job_project_preparing"]

    project_id = uuid4()
    now = datetime.now(UTC)
    await connection.execute(
        f"""
        INSERT INTO "{schema}".geo_project (
            id, tenant_id, name, status, created_at, updated_at
        ) VALUES ($1, $2, 'Contract Project', 'active', $3, $3)
        """,
        project_id,
        uuid4(),
        now,
    )
    await connection.execute(
        f"""
        INSERT INTO "{schema}".geo_project_query_settings (
            project_id, research_provider, run_provider, keywords, market_type,
            max_queries, audience_name, audience_description, intents,
            should_mention_own_brand, should_mention_competitor, created_at, updated_at
        ) VALUES (
            $1, 'openai', 'gemini', '["ERP"]'::jsonb, 'b2b_procurement',
            4, '採購決策者', '企業軟體採購決策者',
            '[{{"category":"informational","description":"了解方案"}}]'::jsonb,
            true, true, $2, $2
        )
        """,
        project_id,
        now,
    )
    with pytest.raises(asyncpg.CheckViolationError):
        await connection.execute(
            f'UPDATE "{schema}".geo_project_query_settings '
            "SET run_provider = 'openai' WHERE project_id = $1",
            project_id,
        )
    with pytest.raises(asyncpg.CheckViolationError):
        await connection.execute(
            f'UPDATE "{schema}".geo_project_query_settings '
            "SET max_queries = 0 WHERE project_id = $1",
            project_id,
        )

    recorder = PostgresProviderRequestRecorder(database_url)
    recorder._pool = await asyncpg.create_pool(  # type: ignore[assignment]
        database_url.replace("postgresql+asyncpg://", "postgresql://", 1),
        min_size=1,
        max_size=1,
        server_settings={"search_path": schema},
    )
    request_id = uuid4()
    try:
        await recorder.start(
            ProviderRequestStarted(
                id=request_id,
                operation_id=uuid4(),
                request_number=1,
                request_kind="initial",
                context=ProviderRequestContext(
                    platform_code="gemini",
                    provider_code="google_vertex_ai",
                    provider_operation="generate_content",
                    use_case="geo_query_answer",
                    source_service="baseline-contract-test",
                    model="gemini-3.1-flash-lite",
                    provider_region="global",
                ),
                started_at=now,
                expects_usage=True,
            )
        )
        await recorder.succeed(
            request_id,
            completed_at=now,
            duration_ms=12,
            http_status=200,
            usage=ProviderRequestUsage(
                input_token_count=10,
                output_token_count=4,
                total_token_count=14,
                traffic_type="ON_DEMAND",
            ),
            usage_capture_status="recorded",
        )
        row = await connection.fetchrow(
            f'SELECT status, usage_capture_status, total_token_count '
            f'FROM "{schema}".provider_request WHERE id = $1',
            request_id,
        )
        assert dict(row) == {
            "status": "succeeded",
            "usage_capture_status": "recorded",
            "total_token_count": 14,
        }
    finally:
        await recorder.close()


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("baseline_name", "models"),
    [
        ("access_control.sql", access_control_models),
        ("resource_catalog.sql", resource_catalog_models),
        ("geo_analysis.sql", geo_analysis_models),
    ],
)
async def test_fresh_baseline_matches_current_persistence_contract(
    baseline_name: str,
    models: ModuleType,
) -> None:
    database_url = os.getenv("GEO_ANALYSIS_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip(
            "Set GEO_ANALYSIS_TEST_DATABASE_URL to compare baselines with persistence models."
        )

    asyncpg_url = database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
    connection = await asyncpg.connect(asyncpg_url)
    schema = f"baseline_contract_{uuid4().hex}"
    try:
        await connection.execute(f'CREATE SCHEMA "{schema}"')
        await connection.execute(_schema_sql(baseline_name, schema))
        await _assert_model_contract(connection, schema, models)
        if baseline_name == "geo_analysis.sql":
            await _assert_geo_raw_sql_contract(connection, database_url, schema)
    finally:
        await connection.execute("ROLLBACK")
        await connection.execute(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')
        await connection.close()
