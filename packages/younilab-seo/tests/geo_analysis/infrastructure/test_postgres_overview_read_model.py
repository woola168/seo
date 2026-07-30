import os
from datetime import UTC, date, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlmodel import SQLModel
from younilab_seo.geo_analysis.application import (
    CreateQueryRunJobCommand,
    GeoOverviewQuery,
    GeoOverviewResponsePageQuery,
    GeoProjectCommand,
    GeoQueryCommand,
    GeoTopicCommand,
    OverviewReportReadModel,
)
from younilab_seo.geo_analysis.infrastructure import (
    GeoAiPlatformRow,
    GeoRunRequestRow,
    GeoRunResultAnalysisRow,
    GeoRunResultEntityMentionRow,
    GeoRunResultReferenceRow,
    GeoRunResultRow,
    GeoRunResultStatementRow,
    PostgresGeoAnalysisRepository,
)

TENANT_ID = UUID("00000000-0000-4000-8000-000000000001")
OTHER_TENANT_ID = UUID("00000000-0000-4000-8000-000000000002")
POSTGRES_INTEGRATION_SKIP_MESSAGE = (
    "Set GEO_ANALYSIS_TEST_DATABASE_URL to run Postgres repository integration tests."
)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_postgres_overview_report_source_filters_data_not_options() -> None:
    database_url = os.getenv("GEO_ANALYSIS_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip(POSTGRES_INTEGRATION_SKIP_MESSAGE)

    engine = create_async_engine(database_url, pool_pre_ping=True)
    session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    repository = PostgresGeoAnalysisRepository(session_factory)
    assert isinstance(repository, OverviewReportReadModel)

    async with engine.begin() as connection:
        await connection.run_sync(SQLModel.metadata.create_all)

    try:
        platform_id = await _add_platform(session_factory)
        project = await repository.create_project(
            GeoProjectCommand(tenantId=TENANT_ID, name=f"Overview {uuid4()}")
        )
        brand_topic = await repository.create_topic(
            TENANT_ID,
            project.id,
            GeoTopicCommand(name="品牌"),
        )
        fitness_topic = await repository.create_topic(
            TENANT_ID,
            project.id,
            GeoTopicCommand(name="健身"),
        )
        assert brand_topic is not None
        assert fitness_topic is not None
        brand_query = await repository.create_query(
            TENANT_ID,
            project.id,
            GeoQueryCommand(
                topicId=brand_topic.id,
                queryText="Acme 好嗎？",
                region="TW",
                language="zh-TW",
                metadata={"industry": "保健", "type": "品牌提及"},
            ),
        )
        fitness_query = await repository.create_query(
            TENANT_ID,
            project.id,
            GeoQueryCommand(
                topicId=fitness_topic.id,
                queryText="健身房推薦？",
                region="US",
                language="en-US",
                metadata={"industry": "健身", "type": "商業"},
            ),
        )
        assert brand_query is not None
        assert fitness_query is not None

        current_id = await _add_result(
            repository,
            session_factory,
            TENANT_ID,
            brand_query.id,
            platform_id,
            provider="gemini",
            region="TW",
            run_at=datetime(2026, 7, 2, tzinfo=UTC),
        )
        comparison_id = await _add_result(
            repository,
            session_factory,
            TENANT_ID,
            brand_query.id,
            platform_id,
            provider="gemini",
            region="TW",
            run_at=datetime(2026, 6, 30, tzinfo=UTC),
        )
        await _add_result(
            repository,
            session_factory,
            TENANT_ID,
            fitness_query.id,
            platform_id,
            provider="google_aio",
            region="US",
            run_at=datetime(2026, 7, 3, tzinfo=UTC),
        )
        await _add_other_tenant_result(repository, session_factory, platform_id)

        report_query = GeoOverviewQuery(
            periodStart=datetime(2026, 7, 1, tzinfo=UTC),
            periodEnd=datetime(2026, 7, 8, tzinfo=UTC),
            topicIds=[brand_topic.id],
            providers=["gemini"],
            region="TW",
            metadataIndustry=["保健"],
            metadataType=["品牌提及"],
        )
        source = await repository.load_overview_report_source(
            TENANT_ID,
            project.id,
            report_query,
            date(2026, 7, 2),
            "url_domain:v2",
        )
        response_page = await repository.load_overview_response_page(
            TENANT_ID,
            project.id,
            GeoOverviewResponsePageQuery(
                reportQuery=report_query,
                queryId=brand_query.id,
            ),
        )

        assert source is not None
        assert {item.run_result_id for item in source.formula_source.run_results} == {
            current_id,
            comparison_id,
        }
        assert [item.id for item in source.queries] == [brand_query.id]
        assert {item.label for item in source.filter_options.topics} == {
            "品牌",
            "健身",
        }
        assert {item.label for item in source.filter_options.platforms} == {
            "Gemini",
            "Google AI Overview",
        }
        assert source.filter_options.regions == ["TW", "US"]
        assert source.filter_options.metadata_industries == ["保健", "健身"]
        assert source.filter_options.metadata_types == ["品牌提及", "商業"]
        assert source.is_preparing is True
        assert response_page is not None
        assert [item.run_result_id for item in response_page.items] == [current_id]
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_postgres_overview_report_source_returns_none_outside_tenant() -> None:
    database_url = os.getenv("GEO_ANALYSIS_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip(POSTGRES_INTEGRATION_SKIP_MESSAGE)

    engine = create_async_engine(database_url, pool_pre_ping=True)
    session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    repository = PostgresGeoAnalysisRepository(session_factory)
    try:
        project = await repository.create_project(
            GeoProjectCommand(tenantId=TENANT_ID, name=f"Overview {uuid4()}")
        )

        source = await repository.load_overview_report_source(
            OTHER_TENANT_ID,
            project.id,
            GeoOverviewQuery(
                periodStart=datetime(2026, 7, 1, tzinfo=UTC),
                periodEnd=datetime(2026, 7, 8, tzinfo=UTC),
            ),
            date(2026, 7, 2),
            "url_domain:v2",
        )

        assert source is None
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_postgres_overview_response_page_filters_before_pagination() -> None:
    database_url = os.getenv("GEO_ANALYSIS_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip(POSTGRES_INTEGRATION_SKIP_MESSAGE)

    engine = create_async_engine(database_url, pool_pre_ping=True)
    session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    repository = PostgresGeoAnalysisRepository(session_factory)
    try:
        platform_id = await _add_platform(session_factory)
        project = await repository.create_project(
            GeoProjectCommand(tenantId=TENANT_ID, name=f"Responses {uuid4()}")
        )
        query = await repository.create_query(
            TENANT_ID,
            project.id,
            GeoQueryCommand(
                queryText="Acme 好嗎？",
                region="TW",
                language="zh-TW",
            ),
        )
        assert query is not None
        mentioned_id = await _add_result(
            repository,
            session_factory,
            TENANT_ID,
            query.id,
            platform_id,
            provider="gemini",
            region="TW",
            run_at=datetime(2026, 7, 3, tzinfo=UTC),
            reference_count=1,
        )
        not_mentioned_id = await _add_result(
            repository,
            session_factory,
            TENANT_ID,
            query.id,
            platform_id,
            provider="gemini",
            region="TW",
            run_at=datetime(2026, 7, 2, tzinfo=UTC),
        )
        unknown_id = await _add_result(
            repository,
            session_factory,
            TENANT_ID,
            query.id,
            platform_id,
            provider="gemini",
            region="TW",
            run_at=datetime(2026, 7, 1, tzinfo=UTC),
        )
        await _add_semantic_analysis(
            session_factory,
            mentioned_id,
            mentioned=True,
            sentiment="positive",
            competitor_sentiment="negative",
        )
        await _add_semantic_analysis(
            session_factory,
            not_mentioned_id,
            mentioned=False,
            sentiment="negative",
        )
        report_query = GeoOverviewQuery(
            periodStart=datetime(2026, 7, 1, tzinfo=UTC),
            periodEnd=datetime(2026, 7, 8, tzinfo=UTC),
        )

        first_page = await repository.load_overview_response_page(
            TENANT_ID,
            project.id,
            GeoOverviewResponsePageQuery(
                reportQuery=report_query,
                page=1,
                pageSize=1,
            ),
        )
        second_page = await repository.load_overview_response_page(
            TENANT_ID,
            project.id,
            GeoOverviewResponsePageQuery(
                reportQuery=report_query,
                page=2,
                pageSize=1,
            ),
        )
        mentioned_page = await repository.load_overview_response_page(
            TENANT_ID,
            project.id,
            GeoOverviewResponsePageQuery(
                reportQuery=report_query,
                mentionStatus="mentioned",
            ),
        )
        not_mentioned_page = await repository.load_overview_response_page(
            TENANT_ID,
            project.id,
            GeoOverviewResponsePageQuery(
                reportQuery=report_query,
                mentionStatus="not_mentioned",
            ),
        )
        beyond_page = await repository.load_overview_response_page(
            TENANT_ID,
            project.id,
            GeoOverviewResponsePageQuery(
                reportQuery=report_query,
                page=9,
                pageSize=1,
            ),
        )
        other_tenant_page = await repository.load_overview_response_page(
            OTHER_TENANT_ID,
            project.id,
            GeoOverviewResponsePageQuery(reportQuery=report_query),
        )

        assert first_page is not None
        assert second_page is not None
        assert mentioned_page is not None
        assert not_mentioned_page is not None
        assert beyond_page is not None
        assert first_page.total == 3
        assert first_page.items[0].run_result_id == mentioned_id
        assert first_page.items[0].mentioned is True
        assert first_page.items[0].reference_count == 1
        assert first_page.items[0].positive_count == 1
        assert first_page.items[0].negative_count == 0
        assert second_page.items[0].run_result_id == not_mentioned_id
        assert [item.run_result_id for item in mentioned_page.items] == [mentioned_id]
        assert [item.run_result_id for item in not_mentioned_page.items] == [
            not_mentioned_id
        ]
        assert unknown_id not in {
            item.run_result_id
            for page in (mentioned_page, not_mentioned_page)
            for item in page.items
        }
        assert beyond_page.total == 3
        assert beyond_page.items == []
        assert other_tenant_page is None
    finally:
        await engine.dispose()


async def _add_platform(
    session_factory: async_sessionmaker[AsyncSession],
) -> UUID:
    now = datetime.now(UTC).replace(microsecond=0)
    platform_id = uuid4()
    async with session_factory() as session:
        async with session.begin():
            session.add(
                GeoAiPlatformRow(
                    id=platform_id,
                    code=f"overview-{uuid4()}",
                    display_name="Overview Test",
                    provider_type="test",
                    default_model="test-model",
                    status="active",
                    created_at=now,
                    updated_at=now,
                )
            )
    return platform_id


async def _add_other_tenant_result(
    repository: PostgresGeoAnalysisRepository,
    session_factory: async_sessionmaker[AsyncSession],
    platform_id: UUID,
) -> None:
    project = await repository.create_project(
        GeoProjectCommand(tenantId=OTHER_TENANT_ID, name=f"Other {uuid4()}")
    )
    query = await repository.create_query(
        OTHER_TENANT_ID,
        project.id,
        GeoQueryCommand(
            queryText="Other tenant query",
            region="TW",
            language="zh-TW",
        ),
    )
    assert query is not None
    await _add_result(
        repository,
        session_factory,
        OTHER_TENANT_ID,
        query.id,
        platform_id,
        provider="gemini",
        region="TW",
        run_at=datetime(2026, 7, 2, tzinfo=UTC),
    )


async def _add_result(
    repository: PostgresGeoAnalysisRepository,
    session_factory: async_sessionmaker[AsyncSession],
    tenant_id: UUID,
    query_id: UUID,
    platform_id: UUID,
    *,
    provider: str,
    region: str,
    run_at: datetime,
    reference_count: int = 0,
) -> UUID:
    created = await repository.create_job(
        tenant_id,
        query_id,
        CreateQueryRunJobCommand(
            platformId=platform_id,
            scheduledFor=run_at,
        ),
    )
    assert created is not None
    job, _ = created
    run_request_id = uuid4()
    result_id = uuid4()
    async with session_factory() as session:
        async with session.begin():
            session.add(
                GeoRunRequestRow(
                    id=run_request_id,
                    job_id=job.id,
                    tracking_run_request_id=str(uuid4()),
                    provider=provider,
                    timing="immediate",
                    status="completed",
                    created_at=run_at,
                    completed_at=run_at,
                )
            )
            result_row = GeoRunResultRow(
                id=result_id,
                run_request_id=run_request_id,
                job_id=job.id,
                tracking_result_id=str(uuid4()),
                query_id=query_id,
                provider=provider,
                surface="answer",
                model="test-model",
                region=region,
                language="zh-TW" if region == "TW" else "en-US",
                status="completed",
                raw_response="answer",
                run_at=run_at,
                created_at=run_at,
            )
            session.add(result_row)
            await session.flush()
            session.add_all(
                [
                    GeoRunResultReferenceRow(
                        id=uuid4(),
                        run_result_id=result_id,
                        url=f"https://example.com/{index}",
                        domain="example.com",
                        position=index,
                    )
                    for index in range(1, reference_count + 1)
                ]
            )
    return result_id


async def _add_semantic_analysis(
    session_factory: async_sessionmaker[AsyncSession],
    result_id: UUID,
    *,
    mentioned: bool,
    sentiment: str,
    competitor_sentiment: str | None = None,
) -> None:
    now = datetime.now(UTC).replace(microsecond=0)
    analysis_id = uuid4()
    entity_id = uuid4()
    async with session_factory() as session:
        async with session.begin():
            session.add(
                GeoRunResultAnalysisRow(
                    id=analysis_id,
                    run_result_id=result_id,
                    task_key="geo_semantic_analysis",
                    schema_version=1,
                    status="completed",
                    analyzer="test",
                    validation_failures=[],
                    created_at=now,
                    updated_at=now,
                    completed_at=now,
                )
            )
            session.add(
                GeoRunResultEntityMentionRow(
                    id=uuid4(),
                    run_result_id=result_id,
                    analysis_id=analysis_id,
                    entity_id=entity_id,
                    entity_name="Acme",
                    entity_type="own_brand",
                    entity_role="own_brand",
                    mentioned=mentioned,
                    first_mention_order=1 if mentioned else None,
                    mention_count=1 if mentioned else 0,
                    sentiment="neutral",
                    created_at=now,
                )
            )
            session.add(
                GeoRunResultStatementRow(
                    id=uuid4(),
                    run_result_id=result_id,
                    analysis_id=analysis_id,
                    statement_text="Acme statement",
                    entity_id=entity_id,
                    entity_role="own_brand",
                    entity_name="Acme",
                    theme="品牌",
                    sentiment=sentiment,
                    created_at=now,
                )
            )
            if competitor_sentiment is not None:
                session.add(
                    GeoRunResultStatementRow(
                        id=uuid4(),
                        run_result_id=result_id,
                        analysis_id=analysis_id,
                        statement_text="Competitor statement",
                        entity_id=uuid4(),
                        entity_role="competitor",
                        entity_name="Competitor",
                        theme="品牌",
                        sentiment=competitor_sentiment,
                        created_at=now,
                    )
                )
