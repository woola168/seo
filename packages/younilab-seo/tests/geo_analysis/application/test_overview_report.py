import asyncio
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from uuid import UUID

from younilab_seo.geo_analysis.application import (
    GeoMetricEntityMentionInput,
    GeoMetricFormulaSource,
    GeoMetricRunResultInput,
    GeoMetricSentimentInput,
    GeoOverviewFilterOptions,
    GeoOverviewQuery,
    GeoOverviewReportSource,
    GeoQueryRecord,
    GeoRunResultCitationFact,
    GeoTopicRecord,
    GetGeoOverviewReport,
)
from younilab_seo.geo_analysis.application.overview_filters import (
    overview_filter_options,
)

TENANT_ID = UUID("00000000-0000-4000-8000-000000000001")
PROJECT_ID = UUID("00000000-0000-4000-8000-000000000002")
TOPIC_ID = UUID("00000000-0000-4000-8000-000000000003")
QUERY_ID = UUID("00000000-0000-4000-8000-000000000004")
RESULT_ID = UUID("00000000-0000-4000-8000-000000000005")
OWN_ID = UUID("00000000-0000-4000-8000-000000000006")
COMPETITOR_ID = UUID("00000000-0000-4000-8000-000000000007")
REFERENCE_ID = UUID("00000000-0000-4000-8000-000000000008")
OTHER_TOPIC_ID = UUID("00000000-0000-4000-8000-000000000011")
OTHER_QUERY_ID = UUID("00000000-0000-4000-8000-000000000012")
OTHER_RESULT_ID = UUID("00000000-0000-4000-8000-000000000013")


@dataclass
class FakeReportReadModel:
    source: GeoMetricFormulaSource
    queries: list[GeoQueryRecord]
    topics: list[GeoTopicRecord]
    filter_options: GeoOverviewFilterOptions = field(
        default_factory=GeoOverviewFilterOptions
    )
    is_preparing: bool = False
    preparation_business_date: date | None = None

    async def load_overview_report_source(
        self,
        _tenant_id,
        _project_id,
        _query,
        business_date,
        _normalizer_version,
    ):
        self.preparation_business_date = business_date
        return GeoOverviewReportSource(
            formula_source=self.source,
            queries=self.queries,
            topics=self.topics,
            filter_options=self.filter_options,
            is_preparing=self.is_preparing,
        )


@dataclass
class FakeClock:
    current: datetime

    def now(self) -> datetime:
        return self.current


def test_overview_report_composes_sections_from_existing_facts() -> None:
    async def run() -> None:
        source = _source()
        read_model = FakeReportReadModel(
            source,
            [_query_record()],
            [_topic_record()],
            is_preparing=True,
        )
        report = await GetGeoOverviewReport(
            read_model,
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
        assert read_model.preparation_business_date == date(2026, 7, 27)

    asyncio.run(run())


def test_overview_report_applies_selected_filters_to_all_sections() -> None:
    async def run() -> None:
        overview_query = GeoOverviewQuery(
            periodStart=datetime(2026, 7, 1, tzinfo=UTC),
            periodEnd=datetime(2026, 7, 8, tzinfo=UTC),
            topicIds=[TOPIC_ID],
            providers=["gemini"],
            region="TW",
            metadataIndustry=["保健"],
            metadataType=["品牌提及"],
        )
        all_queries = [_query_record(), _other_query_record()]
        all_topics = [_topic_record(), _other_topic_record()]
        read_model = FakeReportReadModel(
            _source(),
            [_query_record()],
            all_topics,
            filter_options=overview_filter_options(
                _source_with_other_result(),
                all_queries,
                all_topics,
                overview_query,
            ),
        )
        report = await GetGeoOverviewReport(
            read_model,
            FakeClock(datetime(2026, 7, 2, tzinfo=UTC)),
        ).execute(
            TENANT_ID,
            PROJECT_ID,
            overview_query,
        )

        visibility = next(
            item for item in report.overview if item.metric_name == "visibility"
        )
        assert visibility.value == 100
        assert report.citation_summary.citation_count == 1
        assert [item.topic_name for item in report.topics] == ["品牌型"]
        assert [item.query_text for item in report.topics[0].queries] == ["Acme 好嗎？"]
        assert [item.value for item in report.citation_urls] == [
            "https://example.com/acme"
        ]
        assert report.sentiment_trend[0].positive_count == 1
        assert report.sentiment_trend[0].negative_count == 0
        assert {item.label for item in report.filter_options.platforms} == {
            "Gemini",
            "Google AI Overview",
        }
        assert report.filter_options.regions == ["TW", "US"]
        assert report.filter_options.metadata_industries == ["保健", "健身"]

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


def _other_query_record() -> GeoQueryRecord:
    return GeoQueryRecord(
        id=OTHER_QUERY_ID,
        projectId=PROJECT_ID,
        topicId=OTHER_TOPIC_ID,
        queryText="健身房推薦？",
        region="US",
        language="en-US",
        metadata={"industry": "健身", "type": "商業"},
        createdAt=datetime(2026, 6, 1, tzinfo=UTC),
        updatedAt=datetime(2026, 6, 1, tzinfo=UTC),
    )


def _other_topic_record() -> GeoTopicRecord:
    return GeoTopicRecord(
        id=OTHER_TOPIC_ID,
        projectId=PROJECT_ID,
        name="健身",
        createdAt=datetime(2026, 6, 1, tzinfo=UTC),
        updatedAt=datetime(2026, 6, 1, tzinfo=UTC),
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


def _source_with_other_result() -> GeoMetricFormulaSource:
    source = _source()
    return GeoMetricFormulaSource(
        runResults=[
            *source.run_results,
            GeoMetricRunResultInput(
                runResultId=OTHER_RESULT_ID,
                queryId=OTHER_QUERY_ID,
                topicId=OTHER_TOPIC_ID,
                provider="google_aio",
                region="US",
                language="en-US",
                completedAt=datetime(2026, 7, 2, 2, tzinfo=UTC),
            ),
        ],
        entityMentions=[
            *source.entity_mentions,
            GeoMetricEntityMentionInput(
                runResultId=OTHER_RESULT_ID,
                entityId=OWN_ID,
                entityRole="own_brand",
                entityName="Acme",
                mentioned=False,
            ),
        ],
        sentiments=[
            *source.sentiments,
            GeoMetricSentimentInput(
                runResultId=OTHER_RESULT_ID,
                entityId=OWN_ID,
                entityRole="own_brand",
                entityName="Acme",
                sentiment="negative",
                theme="品牌",
                statement="Acme is not recommended.",
            ),
        ],
        citations=[
            *source.citations,
            GeoRunResultCitationFact(
                runResultId=OTHER_RESULT_ID,
                referenceId=UUID("00000000-0000-4000-8000-000000000015"),
                url="https://example.com/fitness",
                domain="example.com",
                title="Fitness",
                position=1,
                ownership="other",
                sourceType="unknown",
            ),
        ],
    )
