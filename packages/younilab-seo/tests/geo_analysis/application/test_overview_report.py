import asyncio
from dataclasses import dataclass
from datetime import UTC, date, datetime
from uuid import UUID

from younilab_seo.geo_analysis.application import (
    GeoMetricEntityMentionInput,
    GeoMetricFormulaSource,
    GeoMetricRunResultInput,
    GeoMetricSentimentInput,
    GeoOverviewQuery,
    GeoQueryRecord,
    GeoRunResultCitationFact,
    GeoRunResultRecord,
    GeoTopicRecord,
    GetGeoOverviewReport,
    ListGeoOverviewResponses,
)


TENANT_ID = UUID("00000000-0000-4000-8000-000000000001")
PROJECT_ID = UUID("00000000-0000-4000-8000-000000000002")
TOPIC_ID = UUID("00000000-0000-4000-8000-000000000003")
QUERY_ID = UUID("00000000-0000-4000-8000-000000000004")
RESULT_ID = UUID("00000000-0000-4000-8000-000000000005")
OWN_ID = UUID("00000000-0000-4000-8000-000000000006")
COMPETITOR_ID = UUID("00000000-0000-4000-8000-000000000007")
REFERENCE_ID = UUID("00000000-0000-4000-8000-000000000008")


@dataclass
class FakeSourceBuilder:
    source: GeoMetricFormulaSource

    async def execute(self, _tenant_id, _project_id, _query):
        return self.source


class FakeRepository:
    def __init__(self, *, is_preparing: bool = False) -> None:
        self.is_preparing = is_preparing
        self.preparation_business_date: date | None = None

    async def list_queries(self, _tenant_id, _project_id):
        return [_query_record()]

    async def list_topics(self, _tenant_id, _project_id):
        return [_topic_record()]

    async def list_project_run_results(self, _tenant_id, _project_id):
        return [_run_result()]

    async def is_project_data_preparing(
        self,
        _tenant_id,
        _project_id,
        business_date,
    ):
        self.preparation_business_date = business_date
        return self.is_preparing


@dataclass
class FakeClock:
    current: datetime

    def now(self) -> datetime:
        return self.current


def test_overview_report_composes_kinsan_sections_from_existing_facts() -> None:
    async def run() -> None:
        source = _source()
        repository = FakeRepository(is_preparing=True)
        report = await GetGeoOverviewReport(
            repository,
            FakeSourceBuilder(source),
            FakeClock(datetime(2026, 7, 26, 16, tzinfo=UTC)),
        ).execute(TENANT_ID, PROJECT_ID, _overview_query())

        kpis = {item.metric_name: item for item in report.overview}
        assert kpis["visibility"].value == 100
        assert kpis["sov"].value == 50
        assert kpis["average_position"].secondary_value == 2
        assert report.citation_summary.citation_count == 1
        assert report.citation_summary.cited_page_count == 1
        assert report.citation_summary.cited_response_percent == 100
        assert report.visibility_trend[0].points[0].date == "2026-07-01"
        assert report.sentiment_trend[0].positive_count == 1
        assert report.topics[0].queries[0].query_text == "Acme 好嗎？"
        assert report.citation_urls[0].query_count == 1
        assert report.is_preparing is True
        assert repository.preparation_business_date == date(2026, 7, 27)

    asyncio.run(run())


def test_overview_responses_preserve_completed_mention_state() -> None:
    async def run() -> None:
        page = await ListGeoOverviewResponses(
            FakeRepository(),
            FakeSourceBuilder(_source()),
        ).execute(
            TENANT_ID,
            PROJECT_ID,
            _overview_query(),
            mention_status="mentioned",
        )

        assert page.total == 1
        assert page.items[0].mentioned is True
        assert page.items[0].positive_count == 1
        assert page.items[0].reference_count == 1

    asyncio.run(run())


def _overview_query() -> GeoOverviewQuery:
    return GeoOverviewQuery(
        periodStart=datetime(2026, 7, 1, tzinfo=UTC),
        periodEnd=datetime(2026, 7, 8, tzinfo=UTC),
        metadataIndustry=["保健"],
    )


def _query_record() -> GeoQueryRecord:
    return GeoQueryRecord(
        id=QUERY_ID,
        projectId=PROJECT_ID,
        topicId=TOPIC_ID,
        queryText="Acme 好嗎？",
        region="TW",
        language="zh-TW",
        metadata={"industry": "保健", "type": "品牌提及"},
        createdAt=datetime(2026, 6, 1, tzinfo=UTC),
        updatedAt=datetime(2026, 6, 1, tzinfo=UTC),
    )


def _topic_record() -> GeoTopicRecord:
    return GeoTopicRecord(
        id=TOPIC_ID,
        projectId=PROJECT_ID,
        name="品牌型",
        createdAt=datetime(2026, 6, 1, tzinfo=UTC),
        updatedAt=datetime(2026, 6, 1, tzinfo=UTC),
    )


def _run_result() -> GeoRunResultRecord:
    from younilab_seo.geo_analysis.application import GeoRunResultReferenceRecord

    return GeoRunResultRecord(
        id=RESULT_ID,
        runRequestId=UUID("00000000-0000-4000-8000-000000000009"),
        jobId=UUID("00000000-0000-4000-8000-000000000010"),
        trackingResultId="tracking-1",
        queryId=QUERY_ID,
        provider="gemini",
        surface="answer",
        model="gemini",
        region="TW",
        language="zh-TW",
        status="completed",
        rawResponse="Acme 是值得考慮的品牌。",
        runAt=datetime(2026, 7, 1, 2, tzinfo=UTC),
        references=[
            GeoRunResultReferenceRecord(
                id=REFERENCE_ID,
                runResultId=RESULT_ID,
                url="https://example.com/acme",
                domain="example.com",
                position=1,
            )
        ],
        createdAt=datetime(2026, 7, 1, 2, tzinfo=UTC),
        analysisStatus="completed",
    )


def _source() -> GeoMetricFormulaSource:
    return GeoMetricFormulaSource(
        runResults=[
            GeoMetricRunResultInput(
                runResultId=RESULT_ID,
                queryId=QUERY_ID,
                topicId=TOPIC_ID,
                provider="gemini",
                region="TW",
                language="zh-TW",
                completedAt=datetime(2026, 7, 1, 2, tzinfo=UTC),
            )
        ],
        entityMentions=[
            GeoMetricEntityMentionInput(
                runResultId=RESULT_ID,
                entityId=OWN_ID,
                entityRole="own_brand",
                entityName="Acme",
                mentioned=True,
                firstMentionOrder=1,
            ),
            GeoMetricEntityMentionInput(
                runResultId=RESULT_ID,
                entityId=COMPETITOR_ID,
                entityRole="competitor",
                entityName="Beta",
                mentioned=True,
                firstMentionOrder=2,
            ),
        ],
        sentiments=[
            GeoMetricSentimentInput(
                runResultId=RESULT_ID,
                entityId=OWN_ID,
                entityRole="own_brand",
                entityName="Acme",
                sentiment="positive",
                theme="品牌",
                statement="Acme 值得考慮。",
            )
        ],
        citations=[
            GeoRunResultCitationFact(
                runResultId=RESULT_ID,
                referenceId=REFERENCE_ID,
                url="https://example.com/acme",
                domain="example.com",
                title="Acme",
                position=1,
                ownership="other",
                sourceType="unknown",
            )
        ],
    )
