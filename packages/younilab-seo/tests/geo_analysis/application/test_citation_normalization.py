import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from younilab_seo.geo_analysis.application import (
    GeoEntityRecord,
    GeoQueryRecord,
    GeoRunResultCitationFact,
    GeoRunResultCitationNormalization,
    GeoRunResultRecord,
    GeoRunResultReferenceRecord,
    NormalizeRunResultCitations,
    NormalizeRunResultCitationsCommand,
    RunResultCitationNormalizationNotFound,
    SaveRunResultCitationNormalizationCommand,
)


TENANT_ID = UUID("00000000-0000-4000-8000-000000000001")
NOW = datetime(2026, 7, 5, tzinfo=UTC)


@dataclass
class FakeClock:
    current: datetime = NOW

    def now(self) -> datetime:
        return self.current


@dataclass
class FakeRepository:
    result: GeoRunResultRecord | None = None
    query: GeoQueryRecord | None = None
    entities: list[GeoEntityRecord] = field(default_factory=list)
    citation_normalizations: dict[
        tuple[UUID, str],
        GeoRunResultCitationNormalization,
    ] = field(default_factory=dict)
    saved_commands: list[SaveRunResultCitationNormalizationCommand] = field(
        default_factory=list
    )
    save_returns_none: bool = False

    async def get_run_result(self, tenant_id, result_id):
        if (
            tenant_id == TENANT_ID
            and self.result is not None
            and result_id == self.result.id
        ):
            return self.result
        return None

    async def get_query(self, tenant_id, query_id):
        if (
            tenant_id == TENANT_ID
            and self.query is not None
            and query_id == self.query.id
        ):
            return self.query
        return None

    async def list_entities(self, tenant_id, project_id):
        return [
            entity
            for entity in self.entities
            if tenant_id == TENANT_ID and entity.project_id == project_id
        ]

    async def get_run_result_citation_normalization(
        self,
        tenant_id,
        result_id,
        normalizer_version,
    ):
        if tenant_id != TENANT_ID:
            return None
        return self.citation_normalizations.get((result_id, normalizer_version))

    async def save_run_result_citation_normalization(
        self,
        tenant_id,
        command: SaveRunResultCitationNormalizationCommand,
        occurred_at,
    ):
        if tenant_id != TENANT_ID or self.save_returns_none:
            return None
        self.saved_commands.append(command)
        normalization = command.normalization
        self.citation_normalizations[
            (normalization.run_result_id, normalization.normalizer_version)
        ] = normalization
        return normalization


def test_citation_contracts_use_camel_case_shape() -> None:
    reference_id = uuid4()
    run_result_id = uuid4()
    command = NormalizeRunResultCitationsCommand(
        tenantId=TENANT_ID,
        runResultId=run_result_id,
    )
    fact = GeoRunResultCitationFact(
        runResultId=run_result_id,
        referenceId=reference_id,
        url="https://example.com/path",
        domain="example.com",
        title="Example",
        position=1,
        ownership="other",
        sourceType="unknown",
    )
    normalization = GeoRunResultCitationNormalization(
        runResultId=run_result_id,
        status="completed",
        citations=[fact],
        skippedReferenceCount=1,
    )

    assert command.tenant_id == TENANT_ID
    assert command.run_result_id == run_result_id
    assert normalization.citations[0].reference_id == reference_id
    assert normalization.model_dump(by_alias=True)["skippedReferenceCount"] == 1
    assert (
        normalization.model_dump(by_alias=True)["citations"][0]["sourceType"]
        == "unknown"
    )


def test_citation_contracts_reject_invalid_values() -> None:
    with pytest.raises(ValidationError):
        GeoRunResultCitationFact(
            run_result_id=uuid4(),
            reference_id=uuid4(),
            url="https://example.com",
            domain="example.com",
            position=1,
            ownership="competitor",
            source_type="unknown",
        )
    with pytest.raises(ValidationError):
        GeoRunResultCitationNormalization(
            run_result_id=uuid4(),
            status="pending",
        )


def test_normalize_run_result_citations_marks_owned_domain() -> None:
    async def run() -> None:
        repository = _repository(
            references=[
                _reference(
                    "HTTPS://WWW.ACME.COM:443/products/?utm_source=test#section",
                    domain="WWW.ACME.COM",
                ),
                _reference("https://blog.acme.com/articles/"),
            ],
            own_brand_url="https://www.acme.com",
        )

        result = await NormalizeRunResultCitations(repository, FakeClock()).execute(
            TENANT_ID,
            repository.result.id,
        )

        assert result.status == "completed"
        assert [item.domain for item in result.citations] == [
            "acme.com",
            "blog.acme.com",
        ]
        assert [item.ownership for item in result.citations] == ["owned", "owned"]
        assert [item.source_type for item in result.citations] == [
            "owned_site",
            "owned_site",
        ]
        assert result.citations[0].url == "https://acme.com/products?utm_source=test"
        assert result.skipped_reference_count == 0
        assert repository.saved_commands[-1].normalization == result

    asyncio.run(run())


def test_normalize_run_result_citations_returns_existing_without_force() -> None:
    async def run() -> None:
        repository = _repository()
        existing = GeoRunResultCitationNormalization(
            run_result_id=repository.result.id,
            project_id=repository.query.project_id,
            normalizer_version="url_domain:v1",
            status="completed",
        )
        repository.citation_normalizations[
            (repository.result.id, existing.normalizer_version)
        ] = existing

        result = await NormalizeRunResultCitations(repository, FakeClock()).execute(
            TENANT_ID,
            repository.result.id,
        )

        assert result == existing
        assert repository.saved_commands == []

    asyncio.run(run())


def test_normalize_run_result_citations_force_rerun_saves_new_result() -> None:
    async def run() -> None:
        repository = _repository(references=[_reference("https://example.com/first")])
        existing = GeoRunResultCitationNormalization(
            run_result_id=repository.result.id,
            project_id=repository.query.project_id,
            normalizer_version="url_domain:v1",
            status="completed",
        )
        repository.citation_normalizations[
            (repository.result.id, existing.normalizer_version)
        ] = existing

        result = await NormalizeRunResultCitations(repository, FakeClock()).execute(
            TENANT_ID,
            repository.result.id,
            force_renormalize=True,
        )

        assert [citation.url for citation in result.citations] == [
            "https://example.com/first"
        ]
        assert repository.saved_commands[-1].normalization == result
        assert repository.citation_normalizations[
            (repository.result.id, "url_domain:v1")
        ] == result

    asyncio.run(run())


def test_normalize_run_result_citations_marks_unmatched_domain_unknown() -> None:
    async def run() -> None:
        repository = _repository(
            references=[_reference("https://publisher.example/news", title="News")],
            own_brand_url="https://acme.com",
        )

        result = await NormalizeRunResultCitations(repository, FakeClock()).execute(
            TENANT_ID,
            repository.result.id,
        )

        assert result.citations[0].url == "https://publisher.example/news"
        assert result.citations[0].domain == "publisher.example"
        assert result.citations[0].title == "News"
        assert result.citations[0].ownership == "other"
        assert result.citations[0].source_type == "unknown"

    asyncio.run(run())


def test_normalize_run_result_citations_uses_execute_version_override() -> None:
    async def run() -> None:
        repository = _repository()

        result = await NormalizeRunResultCitations(repository, FakeClock()).execute(
            TENANT_ID,
            repository.result.id,
            normalizer_version="url_domain:test",
        )

        assert result.normalizer_version == "url_domain:test"

    asyncio.run(run())


def test_normalize_run_result_citations_uses_only_active_own_brand_domains() -> None:
    async def run() -> None:
        repository = _repository(
            references=[
                _reference("https://inactive.example/page"),
                _reference("https://competitor.example/page"),
                _reference("https://acme.com/page"),
            ],
            own_brand_url="https://acme.com",
        )
        project_id = repository.query.project_id
        repository.entities.extend(
            [
                GeoEntityRecord(
                    id=uuid4(),
                    project_id=project_id,
                    entity_type="own_brand",
                    name="Inactive",
                    website_url="https://inactive.example",
                    status="inactive",
                    created_at=NOW,
                    updated_at=NOW,
                ),
                GeoEntityRecord(
                    id=uuid4(),
                    project_id=project_id,
                    entity_type="competitor",
                    name="Competitor",
                    website_url="https://competitor.example",
                    created_at=NOW,
                    updated_at=NOW,
                ),
            ]
        )

        result = await NormalizeRunResultCitations(repository, FakeClock()).execute(
            TENANT_ID,
            repository.result.id,
        )

        assert [item.ownership for item in result.citations] == [
            "other",
            "other",
            "owned",
        ]

    asyncio.run(run())


def test_normalize_run_result_citations_ignores_missing_or_invalid_own_brand_url() -> None:
    async def run() -> None:
        repository = _repository(
            references=[_reference("https://acme.com/page")],
            own_brand_url=None,
        )
        repository.entities.append(
            GeoEntityRecord(
                id=uuid4(),
                project_id=repository.query.project_id,
                entity_type="own_brand",
                name="Invalid",
                website_url="not a url",
                created_at=NOW,
                updated_at=NOW,
            )
        )

        result = await NormalizeRunResultCitations(repository, FakeClock()).execute(
            TENANT_ID,
            repository.result.id,
        )

        assert result.status == "completed"
        assert result.citations[0].ownership == "other"
        assert result.citations[0].source_type == "unknown"

    asyncio.run(run())


def test_normalize_run_result_citations_accepts_domain_without_scheme() -> None:
    async def run() -> None:
        repository = _repository(references=[_reference("example.com/path")])

        result = await NormalizeRunResultCitations(repository, FakeClock()).execute(
            TENANT_ID,
            repository.result.id,
        )

        assert result.citations[0].url == "https://example.com/path"
        assert result.citations[0].domain == "example.com"

    asyncio.run(run())


def test_normalize_run_result_citations_handles_missing_references() -> None:
    async def run() -> None:
        repository = _repository(references=[])

        result = await NormalizeRunResultCitations(repository, FakeClock()).execute(
            TENANT_ID,
            repository.result.id,
        )

        assert result.status == "completed"
        assert result.citations == []
        assert result.skipped_reference_count == 0

    asyncio.run(run())


def test_normalize_run_result_citations_skips_invalid_reference_urls() -> None:
    async def run() -> None:
        repository = _repository(
            references=[
                _reference(""),
                _reference("not a url"),
                _reference("https://example.com:bad/path"),
                _reference("https://example.com/ok"),
            ]
        )

        result = await NormalizeRunResultCitations(repository, FakeClock()).execute(
            TENANT_ID,
            repository.result.id,
        )

        assert [item.url for item in result.citations] == ["https://example.com/ok"]
        assert result.skipped_reference_count == 3

    asyncio.run(run())


def test_normalize_run_result_citations_failed_when_run_result_not_completed() -> None:
    async def run() -> None:
        repository = _repository(status="failed")

        result = await NormalizeRunResultCitations(repository, FakeClock()).execute(
            TENANT_ID,
            repository.result.id,
        )

        assert result.status == "failed"
        assert result.error_code == "run_result_not_normalizable"
        assert result.citations == []
        assert repository.saved_commands[-1].normalization == result

    asyncio.run(run())


def test_normalize_run_result_citations_failed_when_query_missing() -> None:
    async def run() -> None:
        repository = _repository()
        repository.query = None

        result = await NormalizeRunResultCitations(repository, FakeClock()).execute(
            TENANT_ID,
            repository.result.id,
        )

        assert result.status == "failed"
        assert result.project_id is None
        assert result.error_code == "query_context_missing"
        assert repository.saved_commands[-1].normalization == result

    asyncio.run(run())


def test_normalize_run_result_citations_raises_when_save_returns_none() -> None:
    async def run() -> None:
        repository = _repository()
        repository.save_returns_none = True

        with pytest.raises(RunResultCitationNormalizationNotFound):
            await NormalizeRunResultCitations(repository, FakeClock()).execute(
                TENANT_ID,
                repository.result.id,
            )

    asyncio.run(run())


def test_normalize_run_result_citations_missing_run_result_raises() -> None:
    async def run() -> None:
        with pytest.raises(RunResultCitationNormalizationNotFound):
            await NormalizeRunResultCitations(FakeRepository(), FakeClock()).execute(
                TENANT_ID,
                uuid4(),
            )

    asyncio.run(run())


def _repository(
    *,
    references: list[GeoRunResultReferenceRecord] | None = None,
    status: str = "completed",
    own_brand_url: str | None = "https://acme.com",
) -> FakeRepository:
    project_id = uuid4()
    query_id = uuid4()
    result_id = uuid4()
    return FakeRepository(
        result=GeoRunResultRecord(
            id=result_id,
            run_request_id=uuid4(),
            job_id=uuid4(),
            tracking_result_id="tracking-result-1",
            query_id=query_id,
            provider="gemini",
            surface="Gemini",
            model="gemini-2.5-flash",
            region="TW",
            language="zh-TW",
            status=status,
            raw_response="Raw answer",
            run_at=NOW,
            references=references
            if references is not None
            else [_reference("https://example.com/reference")],
            created_at=NOW,
        ),
        query=GeoQueryRecord(
            id=query_id,
            project_id=project_id,
            query_text="Who are reliable suppliers?",
            region="TW",
            language="zh-TW",
            created_at=NOW,
            updated_at=NOW,
        ),
        entities=[
            GeoEntityRecord(
                id=uuid4(),
                project_id=project_id,
                entity_type="own_brand",
                name="Acme",
                website_url=own_brand_url,
                created_at=NOW,
                updated_at=NOW,
            )
        ],
    )


def _reference(
    url: str,
    *,
    title: str | None = "Example",
    domain: str | None = None,
    position: int = 1,
) -> GeoRunResultReferenceRecord:
    return GeoRunResultReferenceRecord(
        id=uuid4(),
        run_result_id=uuid4(),
        url=url,
        title=title,
        domain=domain,
        position=position,
    )
