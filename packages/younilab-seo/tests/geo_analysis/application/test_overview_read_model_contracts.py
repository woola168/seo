import asyncio
from dataclasses import dataclass
from datetime import UTC, date, datetime
from uuid import UUID

import pytest
from younilab_seo.geo_analysis.application import (
    GeoMetricFormulaSource,
    GeoOverviewFilterOptions,
    GeoOverviewQuery,
    GeoOverviewReportSource,
    GeoOverviewResponsePage,
    GeoOverviewResponsePageQuery,
    GetGeoOverviewReport,
    ListGeoOverviewResponses,
    OverviewReportReadModel,
    OverviewResponseReadModel,
)

TENANT_ID = UUID("00000000-0000-4000-8000-000000000001")
PROJECT_ID = UUID("00000000-0000-4000-8000-000000000002")


class FakeOverviewReportReadModel:
    business_date: date | None = None

    async def load_overview_report_source(
        self,
        tenant_id,
        project_id,
        query,
        business_date,
        normalizer_version,
    ):
        self.business_date = business_date
        return GeoOverviewReportSource(
            formulaSource=GeoMetricFormulaSource(),
            queries=[],
            topics=[],
            filterOptions=GeoOverviewFilterOptions(),
            isPreparing=False,
        )


class FakeOverviewResponseReadModel:
    query: GeoOverviewResponsePageQuery | None = None

    async def load_overview_response_page(
        self,
        tenant_id,
        project_id,
        query,
    ):
        self.query = query
        return GeoOverviewResponsePage(
            items=[],
            total=0,
            page=query.page,
            pageSize=query.page_size,
        )


@dataclass(frozen=True)
class FakeClock:
    current: datetime

    def now(self) -> datetime:
        return self.current


def test_overview_report_source_is_a_structured_application_contract() -> None:
    source = GeoOverviewReportSource(
        formulaSource=GeoMetricFormulaSource(),
        queries=[],
        topics=[],
        filterOptions=GeoOverviewFilterOptions(),
        isPreparing=True,
    )

    assert source.model_dump(by_alias=True) == {
        "formulaSource": {
            "runResults": [],
            "entityMentions": [],
            "sentiments": [],
            "citations": [],
        },
        "queries": [],
        "topics": [],
        "filterOptions": {
            "topics": [],
            "platforms": [],
            "regions": [],
            "metadataIndustries": [],
            "metadataTypes": [],
        },
        "isPreparing": True,
    }


def test_overview_report_fake_implements_public_read_model_seam() -> None:
    fake = FakeOverviewReportReadModel()

    assert isinstance(fake, OverviewReportReadModel)


def test_overview_response_fake_implements_public_read_model_seam() -> None:
    assert isinstance(FakeOverviewResponseReadModel(), OverviewResponseReadModel)


def test_overview_report_use_case_reads_one_filtered_source() -> None:
    async def run() -> None:
        read_model = FakeOverviewReportReadModel()
        query = GeoOverviewQuery(
            periodStart=datetime(2026, 7, 1, tzinfo=UTC),
            periodEnd=datetime(2026, 7, 8, tzinfo=UTC),
        )

        report = await GetGeoOverviewReport(
            read_model,
            FakeClock(datetime(2026, 7, 26, 16, tzinfo=UTC)),
        ).execute(TENANT_ID, PROJECT_ID, query)

        assert report.is_preparing is False
        assert [item.metric_name for item in report.overview] == [
            "mentions",
            "average_position",
            "visibility",
            "sov",
        ]
        assert all(item.value == 0 for item in report.overview)
        assert report.filter_options == GeoOverviewFilterOptions()
        assert read_model.business_date == date(2026, 7, 27)

    asyncio.run(run())


def test_overview_response_use_case_delegates_filtered_page_query() -> None:
    async def run() -> None:
        read_model = FakeOverviewResponseReadModel()
        report_query = GeoOverviewQuery(
            periodStart=datetime(2026, 7, 1, tzinfo=UTC),
            periodEnd=datetime(2026, 7, 8, tzinfo=UTC),
            providers=["gemini"],
        )

        page = await ListGeoOverviewResponses(read_model).execute(
            TENANT_ID,
            PROJECT_ID,
            report_query,
            query_id=UUID("00000000-0000-4000-8000-000000000003"),
            mention_status="not_mentioned",
            page=2,
            page_size=10,
        )

        assert page == GeoOverviewResponsePage(
            items=[],
            total=0,
            page=2,
            pageSize=10,
        )
        assert read_model.query == GeoOverviewResponsePageQuery(
            reportQuery=report_query,
            queryId=UUID("00000000-0000-4000-8000-000000000003"),
            mentionStatus="not_mentioned",
            page=2,
            pageSize=10,
        )

    asyncio.run(run())


@pytest.mark.parametrize(
    ("arguments", "message"),
    [
        ({"mention_status": "unknown"}, "mentionStatus is invalid"),
        ({"page": 0}, "page must be at least 1"),
        ({"page_size": 0}, "pageSize must be between 1 and 100"),
        ({"page_size": 101}, "pageSize must be between 1 and 100"),
    ],
)
def test_overview_response_use_case_preserves_input_validation(
    arguments: dict,
    message: str,
) -> None:
    async def run() -> None:
        with pytest.raises(ValueError, match=message):
            await ListGeoOverviewResponses(FakeOverviewResponseReadModel()).execute(
                TENANT_ID,
                PROJECT_ID,
                GeoOverviewQuery(
                    periodStart=datetime(2026, 7, 1, tzinfo=UTC),
                    periodEnd=datetime(2026, 7, 8, tzinfo=UTC),
                ),
                **arguments,
            )

    asyncio.run(run())


async def _exercise_read_model(read_model: OverviewReportReadModel) -> None:
    source = await read_model.load_overview_report_source(
        TENANT_ID,
        PROJECT_ID,
        GeoOverviewQuery(
            periodStart=datetime(2026, 7, 1, tzinfo=UTC),
            periodEnd=datetime(2026, 7, 8, tzinfo=UTC),
        ),
        date(2026, 7, 2),
        "url_domain:v2",
    )
    assert source is not None
