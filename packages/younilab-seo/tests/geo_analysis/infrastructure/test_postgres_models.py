import os
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlmodel import SQLModel
from younilab_seo.geo_analysis.application import (
    AcceptQueryDraftCommand,
    GeoAnalysisRepository,
    GeoProjectCommand,
    QueryAudience,
    QueryDraftSelectionCommand,
    QueryGenerationCommand,
    QueryResearchCommand,
    GeoQueryRunJobRepository,
)


TENANT_ID = UUID("00000000-0000-4000-8000-000000000001")
from younilab_seo.geo_analysis.infrastructure import (
    GeoMessageDispatchLogRow,
    GeoProjectRow,
    GeoQueryDraftRow,
    GeoQueryDraftSelectionRow,
    GeoQueryGenerationRunRow,
    GeoQueryResearchRunRow,
    GeoQueryRunJobRow,
    GeoRunRequestRow,
    GeoRunResultReferenceRow,
    GeoRunResultRow,
    PostgresGeoAnalysisRepository,
    TenantKMindHubWorkspaceMappingRow,
    build_postgres_session_factory,
)


def test_postgres_rows_use_timezone_aware_timestamps_and_neutral_message_names() -> None:
    tables = [GeoProjectRow.__table__, GeoQueryRunJobRow.__table__, GeoMessageDispatchLogRow.__table__]
    column_types = "\n".join(
        str(column.type)
        for table in tables
        for column in table.columns
    )
    table_names = {table.name for table in tables}
    dispatch_columns = set(GeoMessageDispatchLogRow.__table__.columns.keys())

    assert "DATETIME" in column_types or "TIMESTAMP" in column_types
    assert "geo_message_dispatch_log" in table_names
    assert "message_backend" in dispatch_columns
    assert not any("pubsub" in table_name for table_name in table_names)


def test_run_result_tables_exist_without_metric_tables() -> None:
    defined_tables = {
        GeoProjectRow.__tablename__,
        GeoQueryRunJobRow.__tablename__,
        GeoMessageDispatchLogRow.__tablename__,
        GeoQueryResearchRunRow.__tablename__,
        GeoQueryGenerationRunRow.__tablename__,
        GeoQueryDraftRow.__tablename__,
        GeoQueryDraftSelectionRow.__tablename__,
        GeoRunRequestRow.__tablename__,
        GeoRunResultRow.__tablename__,
        GeoRunResultReferenceRow.__tablename__,
        TenantKMindHubWorkspaceMappingRow.__tablename__,
    }

    assert "geo_run_request" in defined_tables
    assert "tenant_kmindhub_workspace_mapping" in defined_tables
    assert "geo_query_research_run" in defined_tables
    assert "geo_query_generation_run" in defined_tables
    assert "geo_query_draft" in defined_tables
    assert "geo_query_draft_selection" in defined_tables
    assert "geo_run_result" in defined_tables
    assert "geo_run_result_reference" in defined_tables
    assert "geo_response_mention" not in defined_tables
    assert "geo_daily_query_metric" not in defined_tables


def test_postgres_repository_implements_job_repository_port() -> None:
    repository = PostgresGeoAnalysisRepository(
        build_postgres_session_factory(
            "postgresql+asyncpg://user:pass@localhost/resource_catalog"
        )
    )

    assert isinstance(repository, GeoQueryRunJobRepository)
    assert isinstance(repository, GeoAnalysisRepository)


def test_local_schema_file_contains_geo_orchestration_tables() -> None:
    postgres_dir = Path(__file__).parents[5] / "deploy" / "local" / "postgresql"
    schema_path = postgres_dir / "004_geo_analysis_schema.sql"
    patch_path = postgres_dir / "005_geo_analysis_query_planning_patch.sql"
    schema = schema_path.read_text(encoding="utf-8")
    patch = patch_path.read_text(encoding="utf-8")

    assert "CREATE TABLE IF NOT EXISTS geo_project" in schema
    assert "tenant_id uuid NOT NULL" in schema
    assert "ix_geo_project_tenant_id" in schema
    assert "customer_id uuid," in schema
    assert "customer_id uuid NOT NULL" not in schema
    assert GeoProjectRow.__table__.columns["customer_id"].nullable is True
    assert not GeoProjectRow.__table__.columns["customer_id"].foreign_keys
    assert not GeoProjectRow.__table__.columns["seo_task_id"].foreign_keys
    assert "CREATE TABLE IF NOT EXISTS geo_query_research_run" in schema
    assert "CREATE TABLE IF NOT EXISTS geo_query_generation_run" in schema
    assert "CREATE TABLE IF NOT EXISTS geo_query_draft" in schema
    assert "CREATE TABLE IF NOT EXISTS geo_query_draft_selection" in schema
    assert "CREATE TABLE IF NOT EXISTS geo_query_run_job" in schema
    assert "CREATE TABLE IF NOT EXISTS geo_message_dispatch_log" in schema
    assert "CREATE TABLE IF NOT EXISTS geo_external_run_reference" in schema
    assert "CREATE TABLE IF NOT EXISTS geo_run_request" in schema
    assert "CREATE TABLE IF NOT EXISTS geo_run_result" in schema
    assert "CREATE TABLE IF NOT EXISTS geo_run_result_reference" in schema
    assert "CREATE TABLE IF NOT EXISTS tenant_kmindhub_workspace_mapping" in schema
    assert "ux_tenant_kmindhub_workspace_mapping_tenant" in schema
    assert not TenantKMindHubWorkspaceMappingRow.__table__.columns["tenant_id"].foreign_keys
    assert not TenantKMindHubWorkspaceMappingRow.__table__.columns["workspace_id"].foreign_keys
    assert "ALTER COLUMN customer_id DROP NOT NULL" in patch
    assert "CREATE TABLE IF NOT EXISTS geo_query_research_run" in patch
    assert "CREATE TABLE IF NOT EXISTS geo_query_generation_run" in patch
    assert "CREATE TABLE IF NOT EXISTS geo_query_draft" in patch
    assert "CREATE TABLE IF NOT EXISTS geo_query_draft_selection" in patch


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_postgres_repository_query_planning_crud_with_real_database() -> None:
    database_url = os.getenv("GEO_ANALYSIS_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("Set GEO_ANALYSIS_TEST_DATABASE_URL to run Postgres repository integration tests.")

    engine = create_async_engine(database_url, pool_pre_ping=True)
    session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=True,
    )
    repository = PostgresGeoAnalysisRepository(session_factory)
    now = datetime.now(timezone.utc).replace(microsecond=0)

    async with engine.begin() as connection:
        await connection.run_sync(SQLModel.metadata.create_all)

    try:
        project = await repository.create_project(
            GeoProjectCommand(tenant_id=TENANT_ID, name=f"Query Planning {uuid4()}")
        )
        research_run = await repository.create_query_research_run(
            TENANT_ID,
            project.id,
            QueryResearchCommand(
                provider="gemini",
                brand_name="Acme",
                keywords=["erp"],
                region="TW",
                language="zh-TW",
                market_type="b2b_procurement",
            ),
            {"provider": "gemini"},
            {
                "researchContext": "研究摘要",
                "searchedKeywords": ["erp"],
                "sourceUrls": ["https://example.com/source"],
            },
            "completed",
            None,
            now,
        )
        generation_run = await repository.create_query_generation_run(
            TENANT_ID,
            project.id,
            QueryGenerationCommand(
                seo_task_id=uuid4(),
                provider="gemini",
                brand_name="Acme",
                keywords=["erp"],
                region="TW",
                language="zh-TW",
                market_type="b2b_procurement",
                topic_names=["ERP 導入"],
                audience=QueryAudience(name="採購", description="B2B 採購人員"),
            ),
            {"provider": "gemini"},
            {
                "queries": [
                    {
                        "queryText": "Acme ERP 適合哪些採購情境?",
                        "keywords": ["erp"],
                        "region": "TW",
                        "language": "zh-TW",
                        "marketType": "b2b_procurement",
                        "isBranded": True,
                        "attributes": {"topicName": "ERP 導入"},
                    }
                ]
            },
            "completed",
            None,
            now,
        )

        assert research_run is not None
        assert research_run.result is not None
        assert research_run.result.research_context == "研究摘要"
        assert generation_run is not None
        assert len(generation_run.drafts) == 1

        draft_id = generation_run.drafts[0].id
        accepted_query = await repository.accept_query_draft(
            TENANT_ID,
            draft_id,
            AcceptQueryDraftCommand(create_topic_if_missing=True),
        )

        assert accepted_query is not None
        with pytest.raises(ValueError, match="query draft already accepted"):
            await repository.update_query_draft_selection(
                TENANT_ID,
                draft_id,
                QueryDraftSelectionCommand(selection_status="rejected"),
            )
    finally:
        await engine.dispose()
