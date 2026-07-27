import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

from younilab_seo.geo_analysis.application import (
    GeoRunResultAnalysisRecord,
    GeoRunResultRecord,
    GeoRunResultReferenceRecord,
    KMindHubExtractionCommitResult,
    KMindHubExtractionFieldValue,
    KMindHubExtractionPreviewItem,
    KMindHubExtractionPreviewResult,
    KMindHubExtractionTaskMappingCommand,
    KMindHubExtractionTaskMappingRecord,
    KMindHubWorkspaceMappingRecord,
    LegacyAnalysisExtractionPersistence,
    SaveRunResultAnalysisCommand,
)
from younilab_seo.geo_analysis.application.use_cases.analysis_extraction import (
    RunKMindHubAnalysisExtraction,
)

TENANT_ID = UUID("00000000-0000-4000-8000-000000000001")


@dataclass
class FakeClock:
    current: datetime = datetime(2026, 7, 2, tzinfo=UTC)

    def now(self) -> datetime:
        return self.current


def test_legacy_analysis_fake_implements_extraction_persistence() -> None:
    repository = FakeRepository(
        result=_run_result(),
        workspace_mapping=_workspace_mapping(uuid4()),
    )

    assert isinstance(repository, LegacyAnalysisExtractionPersistence)


@dataclass
class FakeRepository:
    result: GeoRunResultRecord
    workspace_mapping: KMindHubWorkspaceMappingRecord
    task_mapping: KMindHubExtractionTaskMappingRecord | None = None
    analyses: list[SaveRunResultAnalysisCommand] = field(default_factory=list)

    async def get_run_result(self, tenant_id, result_id):
        if tenant_id == TENANT_ID and result_id == self.result.id:
            return self.result
        return None

    async def get_kmindhub_extraction_task_mapping(
        self,
        tenant_id,
        task_key,
        schema_version,
    ):
        return self.task_mapping

    async def upsert_kmindhub_extraction_task_mapping(
        self,
        tenant_id,
        command: KMindHubExtractionTaskMappingCommand,
    ):
        self.task_mapping = KMindHubExtractionTaskMappingRecord(
            **command.model_dump(),
            id=uuid4(),
            tenant_id=tenant_id,
            created_at=datetime(2026, 7, 2, tzinfo=UTC),
            updated_at=datetime(2026, 7, 2, tzinfo=UTC),
        )
        return self.task_mapping

    async def save_run_result_analysis(
        self,
        tenant_id,
        command: SaveRunResultAnalysisCommand,
        occurred_at,
    ):
        self.analyses.append(command)
        return GeoRunResultAnalysisRecord(
            id=uuid4(),
            run_result_id=command.run_result_id,
            task_key=command.task_key,
            schema_version=command.schema_version,
            status=command.status,
            summary=command.summary,
            overall_sentiment=command.overall_sentiment,
            theme=command.theme,
            kmindhub_commit_batch_id=command.kmindhub_commit_batch_id,
            kmindhub_item_id=command.kmindhub_item_id,
            error_code=command.error_code,
            error_message=command.error_message,
            created_at=occurred_at,
            updated_at=occurred_at,
            completed_at=occurred_at,
        )


@dataclass
class FakeWorkspaceResolver:
    workspace_id: UUID

    async def resolve_workspace_id(self, tenant_id):
        return self.workspace_id

    async def workspace_headers(self, tenant_id):
        return {"X-Workspace-Id": str(self.workspace_id)}


@dataclass
class FakeKMindHubClient:
    sentiment: str = "positive"
    evidence_text: str = "Acme is good"
    raw_statement_text: str = "Acme is good"
    committed: bool = False

    async def create_workspace(self, display_name: str):
        raise AssertionError("workspace provision should not be used")

    def workspace_headers(self, workspace_id):
        return {"X-Workspace-Id": str(workspace_id)}

    async def create_extraction_task(self, *, workspace_id, definition):
        return uuid4()

    async def preview_text_extraction(self, *, workspace_id, task_id, text):
        return KMindHubExtractionPreviewResult(
            task_id=task_id,
            items=[
                KMindHubExtractionPreviewItem(
                    fields={
                        "summary": KMindHubExtractionFieldValue(value="Acme is good"),
                        "overallSentiment": KMindHubExtractionFieldValue(
                            value=self.sentiment
                        ),
                        "theme": KMindHubExtractionFieldValue(value="供應商比較"),
                        "entityName": KMindHubExtractionFieldValue(value="Acme"),
                        "entityType": KMindHubExtractionFieldValue(value="own_brand"),
                        "mentionCount": KMindHubExtractionFieldValue(value=1),
                        "statementText": KMindHubExtractionFieldValue(
                            value=self.raw_statement_text
                        ),
                        "statementSentiment": KMindHubExtractionFieldValue(
                            value=self.sentiment
                        ),
                        "subjectEntityName": KMindHubExtractionFieldValue(value="Acme"),
                        "evidenceText": KMindHubExtractionFieldValue(
                            value=self.evidence_text
                        ),
                    },
                    verification={"passed": True},
                )
            ],
        )

    async def commit_extraction_items(self, *, workspace_id, task_id, items):
        self.committed = True
        return KMindHubExtractionCommitResult(
            commit_batch_id="batch-1",
            item_ids=["item-1"],
        )


def test_analysis_extraction_commits_and_saves_completed_result() -> None:
    async def run() -> None:
        workspace_id = uuid4()
        repository = FakeRepository(
            result=_run_result(),
            workspace_mapping=_workspace_mapping(workspace_id),
        )
        client = FakeKMindHubClient()

        record = await RunKMindHubAnalysisExtraction(
            repository,
            FakeWorkspaceResolver(workspace_id),
            client,
            FakeClock(),
        ).execute(TENANT_ID, repository.result.id)

        assert record.status == "completed"
        assert client.committed is True
        assert repository.analyses[-1].overall_sentiment == "positive"
        assert repository.analyses[-1].entity_mentions[0].entity_type == "own_brand"
        assert repository.analyses[-1].entity_mentions[0].kmindhub_item_id == "item-1"
        assert repository.analyses[-1].statements[0].kmindhub_item_id == "item-1"
        assert repository.analyses[-1].citation_classifications[0].classification == (
            "unknown"
        )

    asyncio.run(run())


def test_analysis_extraction_accepts_normalized_evidence_text() -> None:
    async def run() -> None:
        workspace_id = uuid4()
        repository = FakeRepository(
            result=_run_result(raw_response="Ａｃｍｅ\r\nis\tgood"),
            workspace_mapping=_workspace_mapping(workspace_id),
        )
        client = FakeKMindHubClient(evidence_text="Acme is good")

        record = await RunKMindHubAnalysisExtraction(
            repository,
            FakeWorkspaceResolver(workspace_id),
            client,
            FakeClock(),
        ).execute(TENANT_ID, repository.result.id)

        assert record.status == "completed"
        assert client.committed is True

    asyncio.run(run())


def test_analysis_extraction_rejects_missing_evidence_without_commit() -> None:
    async def run() -> None:
        workspace_id = uuid4()
        repository = FakeRepository(
            result=_run_result(),
            workspace_mapping=_workspace_mapping(workspace_id),
        )
        client = FakeKMindHubClient(evidence_text="not in answer")

        record = await RunKMindHubAnalysisExtraction(
            repository,
            FakeWorkspaceResolver(workspace_id),
            client,
            FakeClock(),
        ).execute(TENANT_ID, repository.result.id)

        assert record.status == "failed"
        assert client.committed is False
        assert repository.analyses[-1].error_code == "KMindHubExtractionValidationError"

    asyncio.run(run())


def test_analysis_extraction_rejects_invalid_sentiment_without_commit() -> None:
    async def run() -> None:
        workspace_id = uuid4()
        repository = FakeRepository(
            result=_run_result(),
            workspace_mapping=_workspace_mapping(workspace_id),
        )
        client = FakeKMindHubClient(sentiment="happy")

        record = await RunKMindHubAnalysisExtraction(
            repository,
            FakeWorkspaceResolver(workspace_id),
            client,
            FakeClock(),
        ).execute(TENANT_ID, repository.result.id)

        assert record.status == "failed"
        assert client.committed is False
        assert repository.analyses[-1].error_code == "KMindHubExtractionValidationError"

    asyncio.run(run())


def _run_result(raw_response: str = "Acme is good") -> GeoRunResultRecord:
    result_id = uuid4()
    return GeoRunResultRecord(
        id=result_id,
        run_request_id=uuid4(),
        job_id=uuid4(),
        tracking_result_id="tracking-result-1",
        query_id=uuid4(),
        provider="gemini",
        surface="Gemini",
        model="gemini-2.5-flash",
        region="TW",
        language="zh-TW",
        status="completed",
        raw_response=raw_response,
        run_at=datetime(2026, 7, 2, tzinfo=UTC),
        created_at=datetime(2026, 7, 2, tzinfo=UTC),
        references=[
            GeoRunResultReferenceRecord(
                id=uuid4(),
                run_result_id=result_id,
                url="https://example.com",
                domain="example.com",
                position=1,
            )
        ],
    )


def _workspace_mapping(workspace_id: UUID) -> KMindHubWorkspaceMappingRecord:
    return KMindHubWorkspaceMappingRecord(
        id=uuid4(),
        tenant_id=TENANT_ID,
        workspace_id=workspace_id,
        display_name="Acme Workspace",
        provisioning_mode="manual",
        status="active",
        created_at=datetime(2026, 7, 2, tzinfo=UTC),
        updated_at=datetime(2026, 7, 2, tzinfo=UTC),
    )
