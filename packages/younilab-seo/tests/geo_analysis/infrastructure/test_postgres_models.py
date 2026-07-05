import os
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlmodel import SQLModel
from younilab_seo.geo_analysis.application import (
    AcceptQueryDraftCommand,
    GeoEntityMentionFact,
    GeoAnalysisRepository,
    GeoResponseSemanticFact,
    GeoRunResultAnalysis,
    GeoRunResultCitationFact,
    GeoRunResultCitationNormalization,
    GeoProjectCommand,
    QueryAudience,
    QueryDraftSelectionCommand,
    QueryGenerationCommand,
    QueryResearchCommand,
    GeoQueryRunJobRepository,
    GeoSentimentFact,
    SaveRunResultCitationNormalizationCommand,
    SaveRunResultAnalysisCommand,
    SaveSemanticRunResultAnalysisCommand,
)


TENANT_ID = UUID("00000000-0000-4000-8000-000000000001")
from younilab_seo.geo_analysis.infrastructure import (
    GeoAiPlatformRow,
    GeoMessageDispatchLogRow,
    GeoProjectRow,
    GeoQueryRow,
    GeoQueryDraftRow,
    GeoQueryDraftSelectionRow,
    GeoQueryGenerationRunRow,
    GeoQueryResearchRunRow,
    GeoQueryRunJobRow,
    GeoResponseSemanticFactRow,
    GeoRunResultAnalysisRow,
    GeoRunResultEntityMentionRow,
    GeoRunResultCitationNormalizationRow,
    GeoRunResultCitationRow,
    GeoRunRequestRow,
    GeoRunResultReferenceRow,
    GeoRunResultRow,
    GeoRunResultStatementRow,
    PostgresGeoAnalysisRepository,
    TenantKMindHubWorkspaceMappingRow,
    build_postgres_session_factory,
)
from younilab_seo.geo_analysis.infrastructure.persistence.postgres.repository import (
    _run_result_record,
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
        GeoResponseSemanticFactRow.__tablename__,
        GeoRunResultCitationNormalizationRow.__tablename__,
        GeoRunResultCitationRow.__tablename__,
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
    assert "geo_response_semantic_fact" in defined_tables
    assert "geo_run_result_citation_normalization" in defined_tables
    assert "geo_run_result_citation" in defined_tables
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
    analysis_metrics_patch_path = (
        postgres_dir / "012_geo_analysis_analysis_metrics_patch.sql"
    )
    schema = schema_path.read_text(encoding="utf-8")
    patch = patch_path.read_text(encoding="utf-8")
    analysis_metrics_patch = analysis_metrics_patch_path.read_text(encoding="utf-8")

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
    assert "ADD COLUMN IF NOT EXISTS analyzer varchar(64)" in analysis_metrics_patch
    assert "ADD COLUMN IF NOT EXISTS mentioned boolean" in analysis_metrics_patch
    assert "CREATE TABLE IF NOT EXISTS geo_response_semantic_fact" in analysis_metrics_patch
    assert "ix_geo_response_semantic_fact_analysis" in analysis_metrics_patch
    assert "ix_geo_run_result_entity_mention_analysis" in analysis_metrics_patch
    assert "ix_geo_run_result_statement_analysis" in analysis_metrics_patch
    assert (
        "CREATE TABLE IF NOT EXISTS geo_run_result_citation_normalization"
        in analysis_metrics_patch
    )
    assert "CREATE TABLE IF NOT EXISTS geo_run_result_citation" in analysis_metrics_patch
    assert "ux_geo_run_result_citation_normalization_version" in analysis_metrics_patch
    assert "ix_geo_run_result_citation_reference" in analysis_metrics_patch


def test_semantic_analysis_rows_expose_phase_two_columns() -> None:
    assert "analyzer" in GeoRunResultAnalysisRow.__table__.columns
    assert "analyzer_version" in GeoRunResultAnalysisRow.__table__.columns
    assert "entity_role" in GeoRunResultEntityMentionRow.__table__.columns
    assert "mentioned" in GeoRunResultEntityMentionRow.__table__.columns
    assert "first_mention_order" in GeoRunResultEntityMentionRow.__table__.columns
    assert "confidence" in GeoRunResultEntityMentionRow.__table__.columns
    assert "entity_id" in GeoRunResultStatementRow.__table__.columns
    assert "entity_role" in GeoRunResultStatementRow.__table__.columns
    assert "entity_name" in GeoRunResultStatementRow.__table__.columns
    assert "confidence" in GeoRunResultStatementRow.__table__.columns
    assert GeoResponseSemanticFactRow.__tablename__ == "geo_response_semantic_fact"


def test_citation_normalization_rows_expose_phase_six_columns() -> None:
    assert (
        GeoRunResultCitationNormalizationRow.__tablename__
        == "geo_run_result_citation_normalization"
    )
    assert GeoRunResultCitationRow.__tablename__ == "geo_run_result_citation"
    assert "normalizer_version" in GeoRunResultCitationNormalizationRow.__table__.columns
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
async def test_run_result_record_uses_answer_analysis_status_only() -> None:
    now = datetime.now(timezone.utc).replace(microsecond=0)
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
    assert "geo_answer_analysis" in params.values()


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


@pytest.mark.anyio
async def test_postgres_repository_saves_and_loads_semantic_analysis_with_real_database() -> None:
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
        assert (await repository.get_run_result_analysis(TENANT_ID, result_id)).summary == (
            "legacy analysis"
        )
        loaded = await repository.get_semantic_run_result_analysis(TENANT_ID, result_id)
        assert loaded is not None
        assert loaded.entity_mentions[0].entity_name == "Acme"
        assert loaded.sentiments[0].sentiment == "positive"
        assert loaded.semantic_facts[0].value == "ERP"
        assert await repository.get_semantic_run_result_analysis(uuid4(), result_id) is None

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
        assert rerun.entity_mentions == []
        assert rerun.sentiments == []
        assert [fact.value for fact in rerun.semantic_facts] == ["導入顧問"]
        assert (await repository.get_run_result_analysis(TENANT_ID, result_id)).summary == (
            "legacy analysis"
        )
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_postgres_repository_saves_and_loads_citation_normalization_with_real_database() -> None:
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
    project_id = uuid4()
    query_id = uuid4()
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
                            platform_id=uuid4(),
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
                        GeoRunResultReferenceRow(
                            id=reference_id,
                            run_result_id=result_id,
                            url="https://acme.com/source",
                            title="Acme Source",
                            domain="acme.com",
                            position=1,
                        ),
                    ]
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
