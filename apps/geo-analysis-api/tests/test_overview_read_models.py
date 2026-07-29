from datetime import UTC, date, datetime
from uuid import UUID, uuid4

import pytest
from younilab_geo_analysis_api.presentation.http.store import GeoApiStore
from younilab_seo.geo_analysis.application import (
    CreateQueryRunJobCommand,
    GeoEntityMentionFact,
    GeoOverviewQuery,
    GeoOverviewResponsePageQuery,
    GeoProjectCommand,
    GeoQueryCommand,
    GeoRunResultAnalysis,
    GeoRunResultRecord,
    GeoRunResultReferenceRecord,
    GeoSentimentFact,
    GeoTopicCommand,
    OverviewReportReadModel,
)

TENANT_ID = UUID("00000000-0000-4000-8000-000000000001")
OTHER_TENANT_ID = UUID("00000000-0000-4000-8000-000000000002")


@pytest.mark.anyio
async def test_in_memory_overview_report_source_filters_data_not_options() -> None:
    store = GeoApiStore()
    assert isinstance(store, OverviewReportReadModel)

    project = await store.create_project(
        GeoProjectCommand(tenantId=TENANT_ID, name="Acme")
    )
    brand_topic = await store.create_topic(
        TENANT_ID,
        project.id,
        GeoTopicCommand(name="品牌"),
    )
    fitness_topic = await store.create_topic(
        TENANT_ID,
        project.id,
        GeoTopicCommand(name="健身"),
    )
    assert brand_topic is not None
    assert fitness_topic is not None
    brand_query = await store.create_query(
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
    fitness_query = await store.create_query(
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
        store,
        TENANT_ID,
        brand_query.id,
        provider="gemini",
        region="TW",
        run_at=datetime(2026, 7, 2, tzinfo=UTC),
    )
    comparison_id = await _add_result(
        store,
        TENANT_ID,
        brand_query.id,
        provider="gemini",
        region="TW",
        run_at=datetime(2026, 6, 30, tzinfo=UTC),
    )
    await _add_result(
        store,
        TENANT_ID,
        fitness_query.id,
        provider="google_aio",
        region="US",
        run_at=datetime(2026, 7, 3, tzinfo=UTC),
    )
    await _add_other_tenant_result(store)

    report_query = GeoOverviewQuery(
        periodStart=datetime(2026, 7, 1, tzinfo=UTC),
        periodEnd=datetime(2026, 7, 8, tzinfo=UTC),
        topicIds=[brand_topic.id],
        providers=["gemini"],
        region="TW",
        metadataIndustry=["保健"],
        metadataType=["品牌提及"],
    )
    source = await store.load_overview_report_source(
        TENANT_ID,
        project.id,
        report_query,
        date(2026, 7, 2),
        "url_domain:v2",
    )
    response_page = await store.load_overview_response_page(
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
    assert {item.label for item in source.filter_options.topics} == {"品牌", "健身"}
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


@pytest.mark.anyio
async def test_in_memory_overview_report_source_returns_none_outside_tenant() -> None:
    store = GeoApiStore()
    project = await store.create_project(
        GeoProjectCommand(tenantId=TENANT_ID, name="Acme")
    )

    source = await store.load_overview_report_source(
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


@pytest.mark.anyio
async def test_in_memory_overview_response_page_preserves_status_and_counts() -> None:
    store = GeoApiStore()
    project = await store.create_project(
        GeoProjectCommand(tenantId=TENANT_ID, name="Acme")
    )
    query = await store.create_query(
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
        store,
        TENANT_ID,
        query.id,
        provider="gemini",
        region="TW",
        run_at=datetime(2026, 7, 3, tzinfo=UTC),
        reference_count=1,
    )
    not_mentioned_id = await _add_result(
        store,
        TENANT_ID,
        query.id,
        provider="gemini",
        region="TW",
        run_at=datetime(2026, 7, 2, tzinfo=UTC),
    )
    unknown_id = await _add_result(
        store,
        TENANT_ID,
        query.id,
        provider="gemini",
        region="TW",
        run_at=datetime(2026, 7, 1, tzinfo=UTC),
    )
    own_brand_id = uuid4()
    store.semantic_run_result_analyses[mentioned_id] = GeoRunResultAnalysis(
        runResultId=mentioned_id,
        analyzer="test",
        status="completed",
        entityMentions=[
            GeoEntityMentionFact(
                entityId=own_brand_id,
                entityRole="own_brand",
                entityName="Acme",
                mentioned=True,
                firstMentionOrder=1,
            )
        ],
        sentiments=[
            GeoSentimentFact(
                entityId=own_brand_id,
                entityRole="own_brand",
                entityName="Acme",
                sentiment="positive",
                theme="品牌",
                statement="Acme 值得考慮。",
            ),
            GeoSentimentFact(
                entityId=uuid4(),
                entityRole="competitor",
                entityName="Competitor",
                sentiment="negative",
                theme="品牌",
                statement="Competitor 不值得考慮。",
            ),
        ],
    )
    store.semantic_run_result_analyses[not_mentioned_id] = GeoRunResultAnalysis(
        runResultId=not_mentioned_id,
        analyzer="test",
        status="completed",
        entityMentions=[
            GeoEntityMentionFact(
                entityId=own_brand_id,
                entityRole="own_brand",
                entityName="Acme",
                mentioned=False,
            )
        ],
        sentiments=[
            GeoSentimentFact(
                entityId=own_brand_id,
                entityRole="own_brand",
                entityName="Acme",
                sentiment="negative",
                theme="品牌",
                statement="Acme 不適合。",
            )
        ],
    )
    report_query = GeoOverviewQuery(
        periodStart=datetime(2026, 7, 1, tzinfo=UTC),
        periodEnd=datetime(2026, 7, 8, tzinfo=UTC),
    )

    first_page = await store.load_overview_response_page(
        TENANT_ID,
        project.id,
        GeoOverviewResponsePageQuery(
            reportQuery=report_query,
            page=1,
            pageSize=1,
        ),
    )
    second_page = await store.load_overview_response_page(
        TENANT_ID,
        project.id,
        GeoOverviewResponsePageQuery(
            reportQuery=report_query,
            page=2,
            pageSize=1,
        ),
    )
    mentioned_page = await store.load_overview_response_page(
        TENANT_ID,
        project.id,
        GeoOverviewResponsePageQuery(
            reportQuery=report_query,
            mentionStatus="mentioned",
        ),
    )
    not_mentioned_page = await store.load_overview_response_page(
        TENANT_ID,
        project.id,
        GeoOverviewResponsePageQuery(
            reportQuery=report_query,
            mentionStatus="not_mentioned",
        ),
    )
    beyond_page = await store.load_overview_response_page(
        TENANT_ID,
        project.id,
        GeoOverviewResponsePageQuery(
            reportQuery=report_query,
            page=9,
            pageSize=1,
        ),
    )
    other_tenant_page = await store.load_overview_response_page(
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


async def _add_other_tenant_result(store: GeoApiStore) -> None:
    project = await store.create_project(
        GeoProjectCommand(tenantId=OTHER_TENANT_ID, name="Other")
    )
    query = await store.create_query(
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
        store,
        OTHER_TENANT_ID,
        query.id,
        provider="gemini",
        region="TW",
        run_at=datetime(2026, 7, 2, tzinfo=UTC),
    )


async def _add_result(
    store: GeoApiStore,
    tenant_id: UUID,
    query_id: UUID,
    *,
    provider: str,
    region: str,
    run_at: datetime,
    reference_count: int = 0,
) -> UUID:
    created = await store.create_job(
        tenant_id,
        query_id,
        CreateQueryRunJobCommand(
            platformId=uuid4(),
            scheduledFor=run_at,
        ),
    )
    assert created is not None
    job, _ = created
    result_id = uuid4()
    store.run_results[result_id] = GeoRunResultRecord(
        id=result_id,
        runRequestId=uuid4(),
        jobId=job.id,
        trackingResultId=str(uuid4()),
        queryId=query_id,
        provider=provider,
        surface="answer",
        model="test-model",
        region=region,
        language="zh-TW" if region == "TW" else "en-US",
        status="completed",
        rawResponse="answer",
        runAt=run_at,
        references=[
            GeoRunResultReferenceRecord(
                id=uuid4(),
                runResultId=result_id,
                url=f"https://example.com/{index}",
                position=index,
            )
            for index in range(1, reference_count + 1)
        ],
        createdAt=run_at,
    )
    return result_id
