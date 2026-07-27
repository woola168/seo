import asyncio
import os
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlmodel import SQLModel
from younilab_seo.geo_analysis.application import (
    AcceptQueryDraftCommand,
    CitationNormalizationPersistence,
    CreateQueryRunJobCommand,
    EntityCatalogPersistence,
    GeoEntityAliasCommand,
    GeoEntityCommand,
    GeoEntityMentionDetectionItem,
    GeoEntityMentionFact,
    GeoMetricFormulaQuery,
    GeoProjectCommand,
    GeoProjectQuerySettingsCommand,
    GeoQueryCommand,
    GeoQueryPlatformCommand,
    GeoQueryScheduleCommand,
    GeoResponseSemanticFact,
    GeoRunResultAnalysis,
    GeoRunResultCitationFact,
    GeoRunResultCitationNormalization,
    GeoRunResultEntityDetection,
    GeoSentimentFact,
    KMindHubTaskMappingPersistence,
    KMindHubWorkspaceMappingPersistence,
    LegacyAnalysisExtractionPersistence,
    MetricsReadPersistence,
    OverviewReadPersistence,
    ProjectSetupPersistence,
    QueryAudience,
    QueryCatalogPersistence,
    QueryDraftSelectionCommand,
    QueryGenerationCommand,
    QueryPlanningPersistence,
    QueryResearchCommand,
    RunCallbackPersistence,
    RunDispatchPersistence,
    RunExecutionPersistence,
    RunJobManagementPersistence,
    RunResultReadPersistence,
    RunSchedulerPersistence,
    SaveRunResultAnalysisCommand,
    SaveRunResultCitationNormalizationCommand,
    SaveRunResultEntityDetectionCommand,
    SaveSemanticRunResultAnalysisCommand,
    SemanticAnalysisPersistence,
)
from younilab_seo.geo_analysis.infrastructure import (
    GeoAiPlatformRow,
    GeoMessageDispatchLogRow,
    GeoProjectQuerySettingsRow,
    GeoProjectRow,
    GeoQueryDraftRow,
    GeoQueryDraftSelectionRow,
    GeoQueryGenerationRunRow,
    GeoQueryPlatformRow,
    GeoQueryResearchRunRow,
    GeoQueryRow,
    GeoQueryRunJobRow,
    GeoResponseSemanticFactRow,
    GeoRunRequestRow,
    GeoRunResultAnalysisRow,
    GeoRunResultCitationNormalizationRow,
    GeoRunResultCitationRow,
    GeoRunResultEntityDetectionItemRow,
    GeoRunResultEntityDetectionRow,
    GeoRunResultEntityMentionRow,
    GeoRunResultReferenceRow,
    GeoRunResultRow,
    GeoRunResultStatementRow,
    PostgresGeoAnalysisRepository,
    TenantKMindHubWorkspaceMappingRow,
    build_postgres_session_factory,
)
from younilab_seo.geo_analysis.infrastructure.persistence.postgres.repository import (
    _project_query_settings_upsert_statement,
    _run_result_record,
)

TENANT_ID = UUID("00000000-0000-4000-8000-000000000001")
POSTGRES_INTEGRATION_SKIP_MESSAGE = (
    "Set GEO_ANALYSIS_TEST_DATABASE_URL to run Postgres repository integration tests."
)


def test_postgres_rows_use_timezone_aware_timestamps_and_neutral_message_names() -> (
    None
):
    tables = [
        GeoProjectRow.__table__,
        GeoQueryRunJobRow.__table__,
        GeoMessageDispatchLogRow.__table__,
    ]
    column_types = "\n".join(
        str(column.type) for table in tables for column in table.columns
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
        GeoResponseSemanticFactRow.__tablename__,
        GeoRunResultCitationNormalizationRow.__tablename__,
        GeoRunResultCitationRow.__tablename__,
        TenantKMindHubWorkspaceMappingRow.__tablename__,
        GeoProjectQuerySettingsRow.__tablename__,
    }

    assert "geo_run_request" in defined_tables
    assert "tenant_kmindhub_workspace_mapping" in defined_tables
    assert "geo_query_research_run" in defined_tables
    assert "geo_query_generation_run" in defined_tables
    assert "geo_query_draft" in defined_tables
    assert "geo_query_draft_selection" in defined_tables
    assert "geo_run_result" in defined_tables
    assert "geo_run_result_reference" in defined_tables
    assert "geo_response_semantic_fact" in defined_tables
    assert "geo_run_result_citation_normalization" in defined_tables
    assert "geo_run_result_citation" in defined_tables
    assert "geo_project_query_settings" in defined_tables
    assert "geo_response_mention" not in defined_tables
    assert "geo_daily_query_metric" not in defined_tables


def test_postgres_repository_implements_run_lifecycle_ports() -> None:
    repository = PostgresGeoAnalysisRepository(
        build_postgres_session_factory(
            "postgresql+asyncpg://user:pass@localhost/resource_catalog"
        )
    )

    assert isinstance(repository, RunDispatchPersistence)
    assert isinstance(repository, RunCallbackPersistence)
    assert isinstance(repository, RunExecutionPersistence)
    assert isinstance(repository, RunJobManagementPersistence)
    assert isinstance(repository, RunResultReadPersistence)
    assert isinstance(repository, RunSchedulerPersistence)


def test_postgres_repository_implements_semantic_analysis_persistence() -> None:
    repository = PostgresGeoAnalysisRepository(
        build_postgres_session_factory(
            "postgresql+asyncpg://user:pass@localhost/resource_catalog"
        )
    )

    assert isinstance(repository, SemanticAnalysisPersistence)


def test_postgres_repository_implements_citation_normalization_persistence() -> None:
    repository = PostgresGeoAnalysisRepository(
        build_postgres_session_factory(
            "postgresql+asyncpg://user:pass@localhost/resource_catalog"
        )
    )

    assert isinstance(repository, CitationNormalizationPersistence)


def test_postgres_repository_implements_metrics_read_persistence() -> None:
    repository = PostgresGeoAnalysisRepository(
        build_postgres_session_factory(
            "postgresql+asyncpg://user:pass@localhost/resource_catalog"
        )
    )

    assert isinstance(repository, MetricsReadPersistence)


def test_postgres_repository_implements_query_planning_persistence() -> None:
    repository = PostgresGeoAnalysisRepository(
        build_postgres_session_factory(
            "postgresql+asyncpg://user:pass@localhost/resource_catalog"
        )
    )

    assert isinstance(repository, QueryPlanningPersistence)


def test_postgres_repository_implements_setup_persistence_ports() -> None:
    repository = PostgresGeoAnalysisRepository(
        build_postgres_session_factory(
            "postgresql+asyncpg://user:pass@localhost/resource_catalog"
        )
    )

    assert isinstance(repository, ProjectSetupPersistence)
    assert isinstance(repository, EntityCatalogPersistence)
    assert isinstance(repository, QueryCatalogPersistence)


def test_postgres_repository_implements_remaining_workflow_ports() -> None:
    repository = PostgresGeoAnalysisRepository(
        build_postgres_session_factory(
            "postgresql+asyncpg://user:pass@localhost/resource_catalog"
        )
    )

    assert isinstance(repository, OverviewReadPersistence)
    assert isinstance(repository, KMindHubWorkspaceMappingPersistence)
    assert isinstance(repository, KMindHubTaskMappingPersistence)
    assert isinstance(repository, LegacyAnalysisExtractionPersistence)


def test_project_query_settings_upsert_is_atomic_and_skips_unchanged_payload() -> None:
    statement = _project_query_settings_upsert_statement(
        uuid4(),
        GeoProjectQuerySettingsCommand(
            researchProvider="gemini",
            runProvider="gemini",
            keywords=["ERP"],
            marketType="b2b_procurement",
            maxQueries=20,
            audience={"name": "採購主管", "description": "負責供應商評估"},
            intent={"category": "commercial", "description": "比較供應商"},
            shouldMentionOwnBrand=True,
            shouldMentionCompetitor=False,
        ),
        datetime.now(UTC),
    )

    sql = str(statement.compile(dialect=postgresql.dialect()))

    assert "ON CONFLICT (project_id) DO UPDATE" in sql
    assert "IS DISTINCT FROM excluded.research_provider" in sql
    assert "IS DISTINCT FROM excluded.should_mention_competitor" in sql


def test_local_schema_file_contains_geo_orchestration_tables() -> None:
    postgres_dir = Path(__file__).parents[5] / "deploy" / "local" / "postgresql"
    compose_path = postgres_dir.parent / "docker-compose.postgresql.yml"
    schema_path = postgres_dir / "004_geo_analysis_schema.sql"
    patch_path = postgres_dir / "005_geo_analysis_query_planning_patch.sql"
    analysis_metrics_patch_path = (
        postgres_dir / "012_geo_analysis_analysis_metrics_patch.sql"
    )
    nullable_seo_task_patch_path = (
        postgres_dir / "013_geo_analysis_nullable_seo_task_patch.sql"
    )
    scheduler_patch_path = postgres_dir / "015_geo_analysis_daily_scheduler.sql"
    seo_task_contract_path = (
        postgres_dir / "016_geo_analysis_remove_seo_task_contract.sql"
    )
    query_settings_path = postgres_dir / "019_geo_project_query_settings.sql"
    daily_uniqueness_path = postgres_dir / "020_geo_query_daily_run_uniqueness.sql"
    semantic_diagnostics_path = (
        postgres_dir / "021_geo_semantic_analysis_diagnostics.sql"
    )
    entity_detection_path = postgres_dir / "022_geo_run_result_entity_detection.sql"
    preparation_lookup_path = (
        postgres_dir / "024_geo_query_run_job_preparation_lookup.sql"
    )
    schema = schema_path.read_text(encoding="utf-8")
    patch = patch_path.read_text(encoding="utf-8")
    analysis_metrics_patch = analysis_metrics_patch_path.read_text(encoding="utf-8")
    nullable_seo_task_patch = nullable_seo_task_patch_path.read_text(encoding="utf-8")
    scheduler_patch = scheduler_patch_path.read_text(encoding="utf-8")
    seo_task_contract = seo_task_contract_path.read_text(encoding="utf-8")
    query_settings = query_settings_path.read_text(encoding="utf-8")
    daily_uniqueness = daily_uniqueness_path.read_text(encoding="utf-8")
    semantic_diagnostics = semantic_diagnostics_path.read_text(encoding="utf-8")
    entity_detection = entity_detection_path.read_text(encoding="utf-8")
    preparation_lookup = preparation_lookup_path.read_text(encoding="utf-8")
    compose = compose_path.read_text(encoding="utf-8")

    assert "CREATE TABLE IF NOT EXISTS geo_project" in schema
    assert "tenant_id uuid NOT NULL" in schema
    assert "ix_geo_project_tenant_id" in schema
    assert "customer_id uuid," in schema
    assert "customer_id uuid NOT NULL" not in schema
    assert GeoProjectRow.__table__.columns["customer_id"].nullable is True
    assert not GeoProjectRow.__table__.columns["customer_id"].foreign_keys
    assert "seo_task_id" not in GeoProjectRow.__table__.columns
    assert "CREATE TABLE IF NOT EXISTS geo_query_research_run" in schema
    assert "CREATE TABLE IF NOT EXISTS geo_query_generation_run" in schema
    assert "CREATE TABLE IF NOT EXISTS geo_query_draft" in schema
    assert "CREATE TABLE IF NOT EXISTS geo_query_draft_selection" in schema
    assert "CREATE TABLE IF NOT EXISTS geo_query_run_job" in schema
    assert "CREATE TABLE IF NOT EXISTS geo_daily_run_batch" in scheduler_patch
    assert "ux_geo_daily_run_batch_project_date" in scheduler_patch
    assert "ux_geo_query_run_job_scheduled_identity" in scheduler_patch
    assert "execution_snapshot jsonb NOT NULL" in scheduler_patch
    assert "budget_enforced boolean NOT NULL DEFAULT false" in scheduler_patch
    assert "WHERE code = 'google_aio'" in scheduler_patch
    assert "seo_task" not in scheduler_patch
    assert "DROP COLUMN IF EXISTS seo_task_id" not in scheduler_patch
    assert "FROM seo_task" not in seo_task_contract
    assert "customer_id must be backfilled" in seo_task_contract
    assert seo_task_contract.startswith("BEGIN;")
    assert seo_task_contract.rstrip().endswith("COMMIT;")
    assert seo_task_contract.count("DROP COLUMN IF EXISTS seo_task_id") == 2
    assert "CREATE TABLE IF NOT EXISTS geo_project_query_settings" in schema
    assert "CREATE TABLE IF NOT EXISTS geo_project_query_settings" in query_settings
    assert "project_id uuid PRIMARY KEY" in query_settings
    assert "ON DELETE CASCADE" in query_settings
    assert "jsonb_array_length(keywords) <= 10" in query_settings
    assert query_settings.startswith("BEGIN;")
    assert query_settings.rstrip().endswith("COMMIT;")
    assert "business_date date GENERATED ALWAYS" in schema
    assert "ux_geo_query_run_job_daily_slot" in schema
    assert "ix_geo_query_run_job_project_preparing" in schema
    assert "ix_geo_query_run_job_project_preparing" in preparation_lookup
    assert "is_daily_slot_owner = true" in preparation_lookup
    assert "(project_id, business_date, status)" in preparation_lookup
    assert preparation_lookup.startswith("BEGIN;")
    assert preparation_lookup.rstrip().endswith("COMMIT;")
    assert "PARTITION BY query_id, platform_id, business_date" in daily_uniqueness
    assert "is_daily_slot_owner = ranked_jobs.daily_rank = 1" in daily_uniqueness
    assert daily_uniqueness.startswith("BEGIN;")
    assert daily_uniqueness.rstrip().endswith("COMMIT;")
    assert "ALTER TABLE geo_run_result_analysis" in semantic_diagnostics
    assert "analyzer_request_payload jsonb" in semantic_diagnostics
    assert "analyzer_response_payload jsonb" in semantic_diagnostics
    assert "validation_failures jsonb NOT NULL" in semantic_diagnostics
    assert semantic_diagnostics.startswith("BEGIN;")
    assert semantic_diagnostics.rstrip().endswith("COMMIT;")
    assert "012_geo_analysis_analysis_metrics_patch.sql" in compose
    assert "021_geo_semantic_analysis_diagnostics.sql" in compose
    assert (
        "CREATE TABLE IF NOT EXISTS geo_run_result_entity_detection" in entity_detection
    )
    assert (
        "CREATE TABLE IF NOT EXISTS geo_run_result_entity_detection_item"
        in entity_detection
    )
    assert "ux_geo_run_result_entity_detection_version" in entity_detection
    assert "ux_geo_run_result_entity_detection_item_entity" in entity_detection
    assert entity_detection.startswith("BEGIN;")
    assert entity_detection.rstrip().endswith("COMMIT;")
    daily_slot_index = next(
        index
        for index in GeoQueryRunJobRow.__table__.indexes
        if index.name == "ux_geo_query_run_job_daily_slot"
    )
    assert daily_slot_index.unique is True
    preparation_index = next(
        index
        for index in GeoQueryRunJobRow.__table__.indexes
        if index.name == "ix_geo_query_run_job_project_preparing"
    )
    assert preparation_index.unique is False
    assert "CREATE TABLE IF NOT EXISTS geo_message_dispatch_log" in schema
    assert "CREATE TABLE IF NOT EXISTS geo_external_run_reference" in schema
    assert "CREATE TABLE IF NOT EXISTS geo_run_request" in schema
    assert "CREATE TABLE IF NOT EXISTS geo_run_result" in schema
    assert "CREATE TABLE IF NOT EXISTS geo_run_result_reference" in schema
    assert "seo_task_id" not in GeoRunRequestRow.__table__.columns
    assert "CREATE TABLE IF NOT EXISTS tenant_kmindhub_workspace_mapping" in schema
    assert "ux_tenant_kmindhub_workspace_mapping_tenant" in schema
    assert not TenantKMindHubWorkspaceMappingRow.__table__.columns[
        "tenant_id"
    ].foreign_keys
    assert not TenantKMindHubWorkspaceMappingRow.__table__.columns[
        "workspace_id"
    ].foreign_keys
    assert "ALTER COLUMN customer_id DROP NOT NULL" in patch
    assert "CREATE TABLE IF NOT EXISTS geo_query_research_run" in patch
    assert "CREATE TABLE IF NOT EXISTS geo_query_generation_run" in patch
    assert "CREATE TABLE IF NOT EXISTS geo_query_draft" in patch
    assert "CREATE TABLE IF NOT EXISTS geo_query_draft_selection" in patch
    assert "ADD COLUMN IF NOT EXISTS analyzer varchar(64)" in analysis_metrics_patch
    assert "ADD COLUMN IF NOT EXISTS mentioned boolean" in analysis_metrics_patch
    assert (
        "CREATE TABLE IF NOT EXISTS geo_response_semantic_fact"
        in analysis_metrics_patch
    )
    assert "ix_geo_response_semantic_fact_analysis" in analysis_metrics_patch
    assert "ix_geo_run_result_entity_mention_analysis" in analysis_metrics_patch
    assert "ix_geo_run_result_statement_analysis" in analysis_metrics_patch
    assert (
        "CREATE TABLE IF NOT EXISTS geo_run_result_citation_normalization"
        in analysis_metrics_patch
    )
    assert (
        "CREATE TABLE IF NOT EXISTS geo_run_result_citation" in analysis_metrics_patch
    )
    assert "ux_geo_run_result_citation_normalization_version" in analysis_metrics_patch
    assert "ix_geo_run_result_citation_reference" in analysis_metrics_patch
    assert "ALTER TABLE geo_run_request" in nullable_seo_task_patch
    assert "ALTER COLUMN seo_task_id DROP NOT NULL" in nullable_seo_task_patch


def test_semantic_analysis_rows_expose_phase_two_columns() -> None:
    assert "analyzer" in GeoRunResultAnalysisRow.__table__.columns
    assert "analyzer_version" in GeoRunResultAnalysisRow.__table__.columns
    assert "analyzer_request_payload" in GeoRunResultAnalysisRow.__table__.columns
    assert "analyzer_response_payload" in GeoRunResultAnalysisRow.__table__.columns
    assert "validation_failures" in GeoRunResultAnalysisRow.__table__.columns
    assert "entity_role" in GeoRunResultEntityMentionRow.__table__.columns
    assert "mentioned" in GeoRunResultEntityMentionRow.__table__.columns
    assert "first_mention_order" in GeoRunResultEntityMentionRow.__table__.columns
    assert "confidence" in GeoRunResultEntityMentionRow.__table__.columns
    assert "entity_id" in GeoRunResultStatementRow.__table__.columns
    assert "entity_role" in GeoRunResultStatementRow.__table__.columns
    assert "entity_name" in GeoRunResultStatementRow.__table__.columns
    assert "confidence" in GeoRunResultStatementRow.__table__.columns
    assert GeoResponseSemanticFactRow.__tablename__ == "geo_response_semantic_fact"


def test_entity_detection_rows_expose_versioned_match_snapshot_columns() -> None:
    assert (
        GeoRunResultEntityDetectionRow.__tablename__
        == "geo_run_result_entity_detection"
    )
    assert (
        GeoRunResultEntityDetectionItemRow.__tablename__
        == "geo_run_result_entity_detection_item"
    )
    assert "detector_version" in GeoRunResultEntityDetectionRow.__table__.columns
    assert "matched_by" in GeoRunResultEntityDetectionItemRow.__table__.columns
    assert "matched_value" in GeoRunResultEntityDetectionItemRow.__table__.columns
    assert "match_type" in GeoRunResultEntityDetectionItemRow.__table__.columns


def test_citation_normalization_rows_expose_phase_six_columns() -> None:
    assert (
        GeoRunResultCitationNormalizationRow.__tablename__
        == "geo_run_result_citation_normalization"
    )
    assert GeoRunResultCitationRow.__tablename__ == "geo_run_result_citation"
    assert (
        "normalizer_version" in GeoRunResultCitationNormalizationRow.__table__.columns
    )
    assert (
        "skipped_reference_count"
        in GeoRunResultCitationNormalizationRow.__table__.columns
    )
    assert "reference_id" in GeoRunResultCitationRow.__table__.columns
    assert "ownership" in GeoRunResultCitationRow.__table__.columns
    assert "source_type" in GeoRunResultCitationRow.__table__.columns


class _CapturedScalarResult:
    def all(self):
        return []


class _CapturedSession:
    def __init__(self) -> None:
        self.scalar_statements = []
        self.scalars_statements = []

    async def scalar(self, statement):
        self.scalar_statements.append(statement)
        return None

    async def scalars(self, statement):
        self.scalars_statements.append(statement)
        return _CapturedScalarResult()


def _compiled_params(statement) -> dict:
    compiled = statement.compile(dialect=postgresql.dialect())
    return compiled.params


@pytest.mark.anyio
async def test_legacy_analysis_lookup_filters_answer_analysis_task_key() -> None:
    repository = PostgresGeoAnalysisRepository(session_factory=None)
    session = _CapturedSession()

    await repository._get_run_result_analysis_row(session, TENANT_ID, uuid4())

    params = _compiled_params(session.scalar_statements[-1])
    assert "geo_answer_analysis" in params.values()


@pytest.mark.anyio
async def test_run_result_record_uses_semantic_analysis_status() -> None:
    now = datetime.now(UTC).replace(microsecond=0)
    session = _CapturedSession()
    row = GeoRunResultRow(
        id=uuid4(),
        run_request_id=uuid4(),
        job_id=uuid4(),
        tracking_result_id="tracking-result-1",
        query_id=uuid4(),
        provider="gemini",
        surface="ai_overview",
        model="gemini-2.5-pro",
        region="TW",
        language="zh-TW",
        status="completed",
        raw_response="answer",
        run_at=now,
        created_at=now,
    )

    await _run_result_record(session, row)

    params = _compiled_params(session.scalar_statements[-1])
    assert "geo_semantic_analysis" in params.values()


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_postgres_repository_query_planning_crud_with_real_database() -> None:
    database_url = os.getenv("GEO_ANALYSIS_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip(POSTGRES_INTEGRATION_SKIP_MESSAGE)

    engine = create_async_engine(database_url, pool_pre_ping=True)
    session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=True,
    )
    repository = PostgresGeoAnalysisRepository(session_factory)
    now = datetime.now(UTC).replace(microsecond=0)

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


@pytest.mark.anyio
async def test_postgres_repository_lists_project_setup_resources() -> None:
    database_url = os.getenv("GEO_ANALYSIS_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip(POSTGRES_INTEGRATION_SKIP_MESSAGE)

    engine = create_async_engine(database_url, pool_pre_ping=True)
    session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=True,
    )
    repository = PostgresGeoAnalysisRepository(session_factory)
    now = datetime.now(UTC).replace(microsecond=0)
    platform_id = uuid4()

    async with engine.begin() as connection:
        await connection.run_sync(SQLModel.metadata.create_all)

    try:
        async with session_factory() as session:
            async with session.begin():
                session.add(
                    GeoAiPlatformRow(
                        id=platform_id,
                        code=f"bulk-list-{uuid4()}",
                        display_name="Bulk List Platform",
                        provider_type="test",
                        default_model="gemini-3.1-flash-lite",
                        status="active",
                        created_at=now,
                        updated_at=now,
                    )
                )

        project = await repository.create_project(
            GeoProjectCommand(tenant_id=TENANT_ID, name=f"Bulk List {uuid4()}")
        )
        other_project = await repository.create_project(
            GeoProjectCommand(tenant_id=TENANT_ID, name=f"Other Bulk List {uuid4()}")
        )
        entity = await repository.create_entity(
            TENANT_ID,
            project.id,
            GeoEntityCommand(entity_type="own_brand", name="Bulk List Entity"),
        )
        other_entity = await repository.create_entity(
            TENANT_ID,
            other_project.id,
            GeoEntityCommand(entity_type="own_brand", name="Other Bulk List Entity"),
        )
        assert entity is not None
        assert other_entity is not None
        created_aliases = await repository.replace_aliases(
            TENANT_ID,
            entity.id,
            [GeoEntityAliasCommand(alias="Bulk List Alias")],
        )
        await repository.replace_aliases(
            TENANT_ID,
            other_entity.id,
            [GeoEntityAliasCommand(alias="Other Bulk List Alias")],
        )
        query = await repository.create_query(
            TENANT_ID,
            project.id,
            GeoQueryCommand(
                query_text="Bulk list query", region="TW", language="zh-TW"
            ),
        )
        other_query = await repository.create_query(
            TENANT_ID,
            other_project.id,
            GeoQueryCommand(
                query_text="Other bulk list query", region="TW", language="zh-TW"
            ),
        )
        assert created_aliases is not None
        assert query is not None
        assert other_query is not None
        query_platforms = await repository.replace_query_platforms(
            TENANT_ID,
            query.id,
            [GeoQueryPlatformCommand(platform_id=platform_id)],
        )
        await repository.replace_query_platforms(
            TENANT_ID,
            other_query.id,
            [GeoQueryPlatformCommand(platform_id=platform_id)],
        )
        schedule = await repository.create_schedule(
            TENANT_ID,
            query.id,
            GeoQueryScheduleCommand(platform_id=platform_id, frequency="daily"),
        )
        await repository.create_schedule(
            TENANT_ID,
            other_query.id,
            GeoQueryScheduleCommand(platform_id=platform_id, frequency="daily"),
        )
        assert query_platforms is not None
        assert schedule is not None

        async with session_factory() as session:
            async with session.begin():
                legacy_assignment = await session.get(
                    GeoQueryPlatformRow,
                    query_platforms[0].id,
                )
                assert legacy_assignment is not None
                legacy_assignment.model = "gemini-2.5-pro"

        job_creation = await repository.create_job(
            TENANT_ID,
            query.id,
            CreateQueryRunJobCommand(platform_id=platform_id),
        )
        assert job_creation is not None
        job, was_created = job_creation
        assert was_created is True
        dispatch_context = await repository.get_job_dispatch_context(job.id)
        assert dispatch_context is not None
        assert dispatch_context.model == "gemini-3.1-flash-lite"

        aliases = await repository.list_project_aliases(TENANT_ID, project.id)
        platforms = await repository.list_project_query_platforms(
            TENANT_ID,
            project.id,
        )
        schedules = await repository.list_project_schedules(TENANT_ID, project.id)

        assert [item.id for item in aliases] == [created_aliases[0].id]
        assert [item.id for item in platforms] == [query_platforms[0].id]
        assert [item.id for item in schedules] == [schedule.id]
        assert await repository.list_project_aliases(uuid4(), project.id) == []
        assert await repository.list_project_query_platforms(uuid4(), project.id) == []
        assert await repository.list_project_schedules(uuid4(), project.id) == []
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_postgres_repository_replaces_aliases_atomically() -> None:
    database_url = os.getenv("GEO_ANALYSIS_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip(POSTGRES_INTEGRATION_SKIP_MESSAGE)

    engine = create_async_engine(database_url, pool_pre_ping=True)
    session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=True,
    )
    repository = PostgresGeoAnalysisRepository(session_factory)

    async with engine.begin() as connection:
        await connection.run_sync(SQLModel.metadata.create_all)

    try:
        project = await repository.create_project(
            GeoProjectCommand(tenant_id=TENANT_ID, name=f"Alias Replace {uuid4()}")
        )
        entity = await repository.create_entity(
            TENANT_ID,
            project.id,
            GeoEntityCommand(entity_type="own_brand", name="Alias Replace Entity"),
        )
        assert entity is not None
        original = await repository.replace_aliases(
            TENANT_ID,
            entity.id,
            [
                GeoEntityAliasCommand(alias="Keep", match_type="exact"),
                GeoEntityAliasCommand(alias="Remove", match_type="contains"),
            ],
        )
        assert original is not None

        repeated = await repository.replace_aliases(
            TENANT_ID,
            entity.id,
            [
                GeoEntityAliasCommand(alias="Keep", match_type="exact"),
                GeoEntityAliasCommand(alias="Remove", match_type="contains"),
            ],
        )
        assert repeated is not None
        assert [(item.id, item.created_at) for item in repeated] == [
            (item.id, item.created_at) for item in original
        ]

        with pytest.raises(DBAPIError):
            await repository.replace_aliases(
                TENANT_ID,
                entity.id,
                [
                    GeoEntityAliasCommand(alias="Keep", match_type="domain"),
                    GeoEntityAliasCommand(alias="Invalid", match_type="x" * 33),
                ],
            )
        after_failure = await repository.list_aliases(TENANT_ID, entity.id)
        assert {item.alias: item.match_type for item in after_failure} == {
            "Keep": "exact",
            "Remove": "contains",
        }

        await asyncio.gather(
            repository.replace_aliases(
                TENANT_ID,
                entity.id,
                [
                    GeoEntityAliasCommand(alias="First"),
                    GeoEntityAliasCommand(alias="First Two"),
                ],
            ),
            repository.replace_aliases(
                TENANT_ID,
                entity.id,
                [GeoEntityAliasCommand(alias="Second")],
            ),
        )
        final_values = {
            item.alias for item in await repository.list_aliases(TENANT_ID, entity.id)
        }
        assert final_values in ({"First", "First Two"}, {"Second"})
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_daily_materialization_uses_active_queries_and_active_platforms() -> None:
    database_url = os.getenv("GEO_ANALYSIS_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip(POSTGRES_INTEGRATION_SKIP_MESSAGE)

    engine = create_async_engine(database_url, pool_pre_ping=True)
    session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=True,
    )
    repository = PostgresGeoAnalysisRepository(session_factory)
    now = datetime.now(UTC).replace(microsecond=0)
    active_platform_id = uuid4()
    paused_platform_id = uuid4()

    async with engine.begin() as connection:
        await connection.run_sync(SQLModel.metadata.create_all)

    try:
        async with session_factory() as session:
            async with session.begin():
                session.add_all(
                    [
                        GeoAiPlatformRow(
                            id=active_platform_id,
                            code=f"daily-active-{uuid4()}",
                            display_name="Daily Active Platform",
                            provider_type="test",
                            default_model="active-default-model",
                            status="active",
                            created_at=now,
                            updated_at=now,
                        ),
                        GeoAiPlatformRow(
                            id=paused_platform_id,
                            code=f"daily-paused-{uuid4()}",
                            display_name="Daily Paused Platform",
                            provider_type="test",
                            default_model="paused-default-model",
                            status="paused",
                            created_at=now,
                            updated_at=now,
                        ),
                    ]
                )

        platform_records = {
            platform.id: platform for platform in await repository.list_ai_platforms()
        }
        assert platform_records[active_platform_id].status == "active"
        assert platform_records[paused_platform_id].status == "paused"

        project = await repository.create_project(
            GeoProjectCommand(tenant_id=TENANT_ID, name=f"Daily Runs {uuid4()}")
        )
        active_query = await repository.create_query(
            TENANT_ID,
            project.id,
            GeoQueryCommand(
                query_text="Daily active query",
                region="TW",
                language="zh-TW",
            ),
        )
        paused_query = await repository.create_query(
            TENANT_ID,
            project.id,
            GeoQueryCommand(
                query_text="Daily paused query",
                region="TW",
                language="zh-TW",
                status="paused",
            ),
        )
        assert active_query is not None
        assert paused_query is not None
        assert await repository.list_query_platforms(TENANT_ID, active_query.id) == []

        await repository.materialize_daily_runs(
            business_date=date.today(),
            scheduled_for=now,
            occurred_at=now,
        )

        async with session_factory() as session:
            rows = (
                await session.scalars(
                    select(GeoQueryRunJobRow).where(
                        GeoQueryRunJobRow.project_id == project.id
                    )
                )
            ).all()

        assert any(row.platform_id == active_platform_id for row in rows)
        assert all(row.platform_id != paused_platform_id for row in rows)
        assert all(row.query_id == active_query.id for row in rows)
        active_platform_job = next(
            row for row in rows if row.platform_id == active_platform_id
        )
        assert active_platform_job.execution_snapshot["model"] == "active-default-model"

        existing_daily_job = await repository.create_job(
            TENANT_ID,
            active_query.id,
            CreateQueryRunJobCommand(
                platform_id=active_platform_id,
                scheduled_for=now,
                job_type="query_research_first_run",
            ),
        )
        assert existing_daily_job is not None
        existing_job, was_created = existing_daily_job
        assert was_created is False
        assert existing_job.id == active_platform_job.id
        assert existing_job.source == "scheduled"
        assert existing_job.job_type == "scheduled_run"

        first_run_creation = await repository.create_job(
            TENANT_ID,
            paused_query.id,
            CreateQueryRunJobCommand(
                platform_id=active_platform_id,
                scheduled_for=now,
                job_type="query_research_first_run",
            ),
        )
        promotable_manual_creation = await repository.create_job(
            TENANT_ID,
            paused_query.id,
            CreateQueryRunJobCommand(
                platform_id=paused_platform_id,
                scheduled_for=now,
                job_type="manual_run",
            ),
        )
        assert first_run_creation is not None
        assert promotable_manual_creation is not None
        promotable_manual_job, _ = promotable_manual_creation
        promoted_creation = await repository.create_job(
            TENANT_ID,
            paused_query.id,
            CreateQueryRunJobCommand(
                platform_id=paused_platform_id,
                scheduled_for=now,
                job_type="query_research_first_run",
            ),
        )
        normal_manual_creation = await repository.create_job(
            TENANT_ID,
            active_query.id,
            CreateQueryRunJobCommand(
                platform_id=paused_platform_id,
                scheduled_for=now,
                job_type="manual_run",
            ),
        )
        assert promoted_creation is not None
        assert normal_manual_creation is not None
        first_run_job, _ = first_run_creation
        promoted_job, promoted_was_created = promoted_creation
        normal_manual_job, _ = normal_manual_creation
        assert promoted_was_created is False
        assert promoted_job.id == promotable_manual_job.id
        assert promoted_job.job_type == "query_research_first_run"

        dispatchable_ids = await repository.list_dispatchable_job_ids(
            occurred_at=now,
            limit=100,
        )
        assert active_platform_job.id in dispatchable_ids
        assert first_run_job.id in dispatchable_ids
        assert promoted_job.id in dispatchable_ids
        assert normal_manual_job.id not in dispatchable_ids

        async with session_factory() as session:
            async with session.begin():
                row = await session.get(GeoQueryRunJobRow, first_run_job.id)
                assert row is not None
                row.status = "delayed"
                row.next_retry_at = now + timedelta(minutes=5)

        assert first_run_job.id not in await repository.list_dispatchable_job_ids(
            occurred_at=now,
            limit=100,
        )
        assert first_run_job.id in await repository.list_dispatchable_job_ids(
            occurred_at=now + timedelta(minutes=5),
            limit=100,
        )

        async with session_factory() as session:
            async with session.begin():
                first_run_row = await session.get(
                    GeoQueryRunJobRow,
                    first_run_job.id,
                )
                normal_manual_row = await session.get(
                    GeoQueryRunJobRow,
                    normal_manual_job.id,
                )
                assert first_run_row is not None
                assert normal_manual_row is not None
                first_run_row.status = "publishing"
                first_run_row.updated_at = now - timedelta(minutes=10)
                normal_manual_row.status = "publishing"
                normal_manual_row.updated_at = now - timedelta(minutes=10)

        await repository.reconcile_stale_jobs(
            stale_before=now - timedelta(minutes=5),
            occurred_at=now,
        )
        async with session_factory() as session:
            reconciled_first_run = await session.get(
                GeoQueryRunJobRow,
                first_run_job.id,
            )
            untouched_manual = await session.get(
                GeoQueryRunJobRow,
                normal_manual_job.id,
            )
            assert reconciled_first_run is not None
            assert untouched_manual is not None
            assert reconciled_first_run.status == "failed"
            assert reconciled_first_run.last_error_code == "publish_state_stale"
            assert untouched_manual.status == "publishing"

        manual_job_creation = await repository.create_job(
            TENANT_ID,
            active_query.id,
            CreateQueryRunJobCommand(
                platform_id=active_platform_id,
                scheduled_for=now + timedelta(days=1),
            ),
        )
        assert manual_job_creation is not None
        manual_job, was_created = manual_job_creation
        assert was_created is True

        async with session_factory() as session:
            async with session.begin():
                for job_id in (active_platform_job.id, manual_job.id):
                    row = await session.get(GeoQueryRunJobRow, job_id)
                    assert row is not None
                    row.status = "running_external"
                    row.updated_at = now - timedelta(minutes=10)

        await repository.reconcile_stale_jobs(
            stale_before=now - timedelta(minutes=5),
            occurred_at=now,
        )
        async with session_factory() as session:
            for job_id in (active_platform_job.id, manual_job.id):
                reconciled = await session.get(GeoQueryRunJobRow, job_id)
                assert reconciled is not None
                assert reconciled.status == "failed"
                assert reconciled.last_error_code == "execution_outcome_unknown"

        async with session_factory() as session:
            async with session.begin():
                row = await session.get(GeoQueryRunJobRow, active_platform_job.id)
                assert row is not None
                row.status = "succeeded"
                row.updated_at = now

        await repository.reconcile_stale_jobs(
            stale_before=now - timedelta(minutes=5),
            occurred_at=now + timedelta(minutes=1),
        )
        async with session_factory() as session:
            current = await session.get(GeoQueryRunJobRow, active_platform_job.id)
            assert current is not None
            assert current.status == "succeeded"
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_postgres_repository_semantic_analysis_round_trip() -> None:
    database_url = os.getenv("GEO_ANALYSIS_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip(POSTGRES_INTEGRATION_SKIP_MESSAGE)

    engine = create_async_engine(database_url, pool_pre_ping=True)
    session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=True,
    )
    repository = PostgresGeoAnalysisRepository(session_factory)
    now = datetime.now(UTC).replace(microsecond=0)
    project_id = uuid4()
    query_id = uuid4()
    platform_id = uuid4()
    job_id = uuid4()
    run_request_id = uuid4()
    result_id = uuid4()
    own_brand_id = uuid4()

    async with engine.begin() as connection:
        await connection.run_sync(SQLModel.metadata.create_all)

    try:
        async with session_factory() as session:
            async with session.begin():
                session.add_all(
                    [
                        GeoProjectRow(
                            id=project_id,
                            tenant_id=TENANT_ID,
                            name="Semantic Analysis",
                            status="active",
                            created_at=now,
                            updated_at=now,
                        ),
                        GeoAiPlatformRow(
                            id=platform_id,
                            code=f"gemini-{uuid4()}",
                            display_name="Gemini",
                            provider_type="llm",
                            status="active",
                            created_at=now,
                            updated_at=now,
                        ),
                        GeoQueryRow(
                            id=query_id,
                            project_id=project_id,
                            query_text="哪個 ERP 適合製造業？",
                            region="TW",
                            language="zh-TW",
                            status="active",
                            created_at=now,
                            updated_at=now,
                        ),
                        GeoQueryRunJobRow(
                            id=job_id,
                            project_id=project_id,
                            query_id=query_id,
                            platform_id=platform_id,
                            scheduled_for=now,
                            status="completed",
                            dedupe_key=f"semantic-{uuid4()}",
                            created_at=now,
                            updated_at=now,
                        ),
                        GeoRunRequestRow(
                            id=run_request_id,
                            job_id=job_id,
                            tracking_run_request_id=f"tracking-{uuid4()}",
                            seo_task_id=uuid4(),
                            provider="gemini",
                            timing="run_now",
                            status="completed",
                            request_payload={},
                            created_at=now,
                            completed_at=now,
                        ),
                        GeoRunResultRow(
                            id=result_id,
                            run_request_id=run_request_id,
                            job_id=job_id,
                            tracking_result_id=f"result-{uuid4()}",
                            query_id=query_id,
                            provider="gemini",
                            surface="ai_overview",
                            model="gemini-2.5-pro",
                            region="TW",
                            language="zh-TW",
                            status="completed",
                            raw_response="Acme ERP 適合製造業。",
                            run_at=now,
                            created_at=now,
                        ),
                    ]
                )

        legacy = await repository.save_run_result_analysis(
            TENANT_ID,
            SaveRunResultAnalysisCommand(
                run_result_id=result_id,
                status="completed",
                summary="legacy analysis",
            ),
            now,
        )
        semantic = await repository.save_semantic_run_result_analysis(
            TENANT_ID,
            SaveSemanticRunResultAnalysisCommand(
                analysis=GeoRunResultAnalysis(
                    run_result_id=result_id,
                    analyzer="semantic-v1",
                    analyzer_version="1.0.0",
                    status="completed",
                    entity_mentions=[
                        GeoEntityMentionFact(
                            entity_id=own_brand_id,
                            entity_role="own_brand",
                            entity_name="Acme",
                            mentioned=True,
                            first_mention_order=1,
                            evidence_text="Acme ERP",
                            confidence=0.9,
                        )
                    ],
                    sentiments=[
                        GeoSentimentFact(
                            entity_id=own_brand_id,
                            entity_role="own_brand",
                            entity_name="Acme",
                            sentiment="positive",
                            theme="fit",
                            statement="Acme ERP 適合製造業。",
                            evidence_text="適合製造業",
                            confidence=0.8,
                        )
                    ],
                    semantic_facts=[
                        GeoResponseSemanticFact(
                            fact_type="product",
                            value="ERP",
                            evidence_text="Acme ERP",
                            confidence=0.7,
                        )
                    ],
                )
            ),
            now,
        )

        assert legacy is not None
        assert semantic is not None
        assert (
            await repository.get_run_result_analysis(TENANT_ID, result_id)
        ).summary == ("legacy analysis")
        loaded = await repository.get_semantic_run_result_analysis(TENANT_ID, result_id)
        assert loaded is not None
        assert loaded.entity_mentions[0].entity_name == "Acme"
        assert loaded.sentiments[0].sentiment == "positive"
        assert loaded.semantic_facts[0].value == "ERP"
        source = await repository.get_metric_formula_source(
            TENANT_ID,
            project_id,
            GeoMetricFormulaQuery(
                period_start=now - timedelta(days=1),
                period_end=now + timedelta(days=1),
                provider="gemini",
                region="TW",
                language="zh-TW",
            ),
            "url_domain:v1",
        )
        assert [mention.entity_name for mention in source.entity_mentions] == ["Acme"]
        assert [sentiment.sentiment for sentiment in source.sentiments] == ["positive"]
        assert (
            await repository.get_semantic_run_result_analysis(uuid4(), result_id)
            is None
        )

        detection_command = SaveRunResultEntityDetectionCommand(
            detection=GeoRunResultEntityDetection(
                run_result_id=result_id,
                status="completed",
                items=[
                    GeoEntityMentionDetectionItem(
                        entity_id=own_brand_id,
                        entity_role="own_brand",
                        entity_name="Acme snapshot",
                        mentioned=False,
                    )
                ],
            )
        )
        detections = await asyncio.gather(
            repository.save_run_result_entity_detection(
                TENANT_ID,
                detection_command,
                now,
            ),
            repository.save_run_result_entity_detection(
                TENANT_ID,
                detection_command,
                now,
            ),
        )
        assert all(detection is not None for detection in detections)
        async with session_factory() as session:
            detection_rows = (
                await session.scalars(
                    select(GeoRunResultEntityDetectionRow).where(
                        GeoRunResultEntityDetectionRow.run_result_id == result_id
                    )
                )
            ).all()
            detection_item_rows = (
                await session.scalars(
                    select(GeoRunResultEntityDetectionItemRow).where(
                        GeoRunResultEntityDetectionItemRow.run_result_id == result_id
                    )
                )
            ).all()
        assert len(detection_rows) == 1
        assert len(detection_item_rows) == 1
        loaded_with_detection = await repository.get_semantic_run_result_analysis(
            TENANT_ID,
            result_id,
        )
        assert loaded_with_detection is not None
        assert loaded_with_detection.entity_mentions[0].entity_name == "Acme snapshot"
        source_with_detection = await repository.get_metric_formula_source(
            TENANT_ID,
            project_id,
            GeoMetricFormulaQuery(
                period_start=now - timedelta(days=1),
                period_end=now + timedelta(days=1),
            ),
            "url_domain:v1",
        )
        assert [
            mention.entity_name for mention in source_with_detection.entity_mentions
        ] == ["Acme snapshot"]
        assert [
            sentiment.sentiment for sentiment in source_with_detection.sentiments
        ] == ["positive"]

        await repository.save_semantic_run_result_analysis(
            TENANT_ID,
            SaveSemanticRunResultAnalysisCommand(
                analysis=GeoRunResultAnalysis(
                    run_result_id=result_id,
                    analyzer="semantic-v1",
                    analyzer_version="1.0.1",
                    status="completed",
                    semantic_facts=[
                        GeoResponseSemanticFact(
                            fact_type="service",
                            value="導入顧問",
                        )
                    ],
                )
            ),
            now,
        )
        rerun = await repository.get_semantic_run_result_analysis(TENANT_ID, result_id)
        assert rerun is not None
        assert rerun.entity_mentions[0].entity_name == "Acme snapshot"
        assert rerun.sentiments == []
        assert [fact.value for fact in rerun.semantic_facts] == ["導入顧問"]
        assert (
            await repository.get_run_result_analysis(TENANT_ID, result_id)
        ).summary == ("legacy analysis")
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_postgres_repository_citation_normalization_round_trip() -> None:
    database_url = os.getenv("GEO_ANALYSIS_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip(POSTGRES_INTEGRATION_SKIP_MESSAGE)

    engine = create_async_engine(database_url, pool_pre_ping=True)
    session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=True,
    )
    repository = PostgresGeoAnalysisRepository(session_factory)
    now = datetime.now(UTC).replace(microsecond=0)
    project_id = uuid4()
    query_id = uuid4()
    platform_id = uuid4()
    job_id = uuid4()
    run_request_id = uuid4()
    result_id = uuid4()
    reference_id = uuid4()

    async with engine.begin() as connection:
        await connection.run_sync(SQLModel.metadata.create_all)

    try:
        async with session_factory() as session:
            async with session.begin():
                session.add_all(
                    [
                        GeoAiPlatformRow(
                            id=platform_id,
                            code=f"citation-{uuid4()}",
                            display_name="Citation Platform",
                            provider_type="test",
                            default_model="gemini-3.1-flash-lite",
                            status="active",
                            created_at=now,
                            updated_at=now,
                        ),
                        GeoProjectRow(
                            id=project_id,
                            tenant_id=TENANT_ID,
                            name=f"Citation Persistence {uuid4()}",
                            status="active",
                            created_at=now,
                            updated_at=now,
                        ),
                        GeoQueryRow(
                            id=query_id,
                            project_id=project_id,
                            query_text="Who cites Acme?",
                            region="TW",
                            language="zh-TW",
                            market_type="b2b_procurement",
                            priority="normal",
                            status="active",
                            created_at=now,
                            updated_at=now,
                        ),
                        GeoQueryRunJobRow(
                            id=job_id,
                            project_id=project_id,
                            query_id=query_id,
                            platform_id=platform_id,
                            job_type="manual_run",
                            priority="normal",
                            scheduled_for=now,
                            status="completed",
                            dedupe_key=f"citation-{uuid4()}",
                            created_at=now,
                            updated_at=now,
                        ),
                        GeoRunRequestRow(
                            id=run_request_id,
                            job_id=job_id,
                            tracking_run_request_id=f"tracking-{uuid4()}",
                            seo_task_id=uuid4(),
                            provider="gemini",
                            timing="run_now",
                            status="completed",
                            request_payload={},
                            created_at=now,
                            completed_at=now,
                        ),
                        GeoRunResultRow(
                            id=result_id,
                            run_request_id=run_request_id,
                            job_id=job_id,
                            tracking_result_id=f"result-{uuid4()}",
                            query_id=query_id,
                            provider="gemini",
                            surface="ai_overview",
                            model="gemini-2.5-pro",
                            region="TW",
                            language="zh-TW",
                            status="completed",
                            raw_response="Raw answer",
                            run_at=now,
                            created_at=now,
                        ),
                    ]
                )
                await session.flush()
                session.add(
                    GeoRunResultReferenceRow(
                        id=reference_id,
                        run_result_id=result_id,
                        url="https://acme.com/source",
                        title="Acme Source",
                        domain="acme.com",
                        position=1,
                    )
                )

        saved = await repository.save_run_result_citation_normalization(
            TENANT_ID,
            SaveRunResultCitationNormalizationCommand(
                normalization=GeoRunResultCitationNormalization(
                    run_result_id=result_id,
                    project_id=project_id,
                    normalizer_version="url_domain:v1",
                    status="completed",
                    citations=[
                        GeoRunResultCitationFact(
                            run_result_id=result_id,
                            reference_id=reference_id,
                            url="https://acme.com/source",
                            domain="acme.com",
                            title="Acme Source",
                            position=1,
                            ownership="owned",
                            source_type="owned_site",
                        )
                    ],
                )
            ),
            now,
        )

        assert saved is not None
        assert saved.citations[0].reference_id == reference_id
        loaded = await repository.get_run_result_citation_normalization(
            TENANT_ID,
            result_id,
            "url_domain:v1",
        )
        assert loaded is not None
        assert [citation.domain for citation in loaded.citations] == ["acme.com"]
        source = await repository.get_metric_formula_source(
            TENANT_ID,
            project_id,
            GeoMetricFormulaQuery(
                period_start=now - timedelta(days=1),
                period_end=now + timedelta(days=1),
                provider="gemini",
                region="TW",
                language="zh-TW",
            ),
            "url_domain:v1",
        )
        assert [item.run_result_id for item in source.run_results] == [result_id]
        assert [citation.domain for citation in source.citations] == ["acme.com"]
        assert (
            await repository.get_run_result_citation_normalization(
                uuid4(),
                result_id,
                "url_domain:v1",
            )
            is None
        )

        rerun = await repository.save_run_result_citation_normalization(
            TENANT_ID,
            SaveRunResultCitationNormalizationCommand(
                normalization=GeoRunResultCitationNormalization(
                    run_result_id=result_id,
                    project_id=project_id,
                    normalizer_version="url_domain:v1",
                    status="completed",
                    skipped_reference_count=1,
                )
            ),
            now,
        )
        assert rerun is not None
        assert rerun.citations == []
        assert rerun.skipped_reference_count == 1
        overwritten = await repository.get_run_result_citation_normalization(
            TENANT_ID,
            result_id,
            "url_domain:v1",
        )
        assert overwritten is not None
        assert overwritten.citations == []
        assert overwritten.skipped_reference_count == 1
        with pytest.raises(ValueError, match="reference_id must belong"):
            await repository.save_run_result_citation_normalization(
                TENANT_ID,
                SaveRunResultCitationNormalizationCommand(
                    normalization=GeoRunResultCitationNormalization(
                        run_result_id=result_id,
                        project_id=project_id,
                        normalizer_version="url_domain:v2",
                        status="completed",
                        citations=[
                            GeoRunResultCitationFact(
                                run_result_id=result_id,
                                reference_id=uuid4(),
                                url="https://example.com/invalid",
                                domain="example.com",
                                position=1,
                                ownership="other",
                                source_type="unknown",
                            )
                        ],
                    )
                ),
                now,
            )
    finally:
        await engine.dispose()
