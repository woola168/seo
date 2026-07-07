import asyncio
from dataclasses import dataclass, field
from uuid import UUID, uuid4

import pytest

from younilab_seo.geo_analysis.application import (
    AnalyzeGeoRunResultCommand,
    GeoAnalysisEntityContext,
    GeoAnalysisEntityInput,
    KMindHubExtractionFieldValue,
    KMindHubExtractionPreviewItem,
    KMindHubExtractionPreviewResult,
    KMindHubExtractionTaskMappingCommand,
    KMindHubExtractionTaskMappingRecord,
    KMindHubExtractionUnavailable,
    KMindHubExtractionValidationError,
)
from younilab_seo.geo_analysis.application.kmindhub_extraction_schema import (
    SEMANTIC_ANALYSIS_SCHEMA_VERSION,
    SEMANTIC_ANALYSIS_TASK_KEY,
)
from younilab_seo.geo_analysis.infrastructure import KMindHubGeoRunResultAnalyzer


TENANT_ID = UUID("00000000-0000-4000-8000-000000000001")
TASK_ID = UUID("00000000-0000-4000-8000-000000000002")
WORKSPACE_ID = UUID("00000000-0000-4000-8000-000000000003")
RUN_RESULT_ID = UUID("00000000-0000-4000-8000-000000000004")
OWN_BRAND_ID = UUID("00000000-0000-4000-8000-000000000005")
COMPETITOR_ID = UUID("00000000-0000-4000-8000-000000000006")


@dataclass
class FakeRepository:
    mapping: KMindHubExtractionTaskMappingRecord | None = None
    upserts: list[KMindHubExtractionTaskMappingCommand] = field(default_factory=list)

    async def get_kmindhub_extraction_task_mapping(
        self,
        tenant_id,
        task_key,
        schema_version,
    ):
        if (
            tenant_id == TENANT_ID
            and task_key == SEMANTIC_ANALYSIS_TASK_KEY
            and schema_version == SEMANTIC_ANALYSIS_SCHEMA_VERSION
        ):
            return self.mapping
        return None

    async def upsert_kmindhub_extraction_task_mapping(self, tenant_id, command):
        self.upserts.append(command)
        self.mapping = _mapping(command.kmindhub_task_id)
        return self.mapping


@dataclass
class FakeWorkspaceResolver:
    async def resolve_workspace_id(self, tenant_id):
        assert tenant_id == TENANT_ID
        return WORKSPACE_ID

    async def workspace_headers(self, tenant_id):
        return {"X-Workspace-Id": str(WORKSPACE_ID)}


@dataclass
class FakeKMindHubClient:
    preview_items: list[KMindHubExtractionPreviewItem]
    unavailable: bool = False
    created_tasks: int = 0
    committed_items: list[dict] | None = None
    preview_text: str | None = None

    async def create_workspace(self, display_name: str):
        raise AssertionError("workspace creation should not be used")

    def workspace_headers(self, workspace_id):
        return {"X-Workspace-Id": str(workspace_id)}

    async def create_extraction_task(self, *, workspace_id, definition):
        assert workspace_id == WORKSPACE_ID
        assert definition.task_key == SEMANTIC_ANALYSIS_TASK_KEY
        self.created_tasks += 1
        return TASK_ID

    async def preview_text_extraction(self, *, workspace_id, task_id, text):
        if self.unavailable:
            raise KMindHubExtractionUnavailable("preview unavailable")
        assert workspace_id == WORKSPACE_ID
        assert task_id == TASK_ID
        self.preview_text = text
        return KMindHubExtractionPreviewResult(
            task_id=task_id,
            items=self.preview_items,
        )

    async def commit_extraction_items(self, *, workspace_id, task_id, items):
        assert workspace_id == WORKSPACE_ID
        assert task_id == TASK_ID
        self.committed_items = items
        return None


def test_kmindhub_semantic_analyzer_maps_preview_to_facts() -> None:
    async def run() -> None:
        repository = FakeRepository()
        client = FakeKMindHubClient(preview_items=[_complete_item()])

        result = await KMindHubGeoRunResultAnalyzer(
            repository,
            FakeWorkspaceResolver(),
            client,
        ).analyze(_command())

        assert result.status == "completed"
        assert result.analyzer == "kmindhub"
        assert result.analyzer_version == "geo_semantic_analysis:v1"
        assert result.entity_mentions[0].entity_id == OWN_BRAND_ID
        assert result.entity_mentions[0].first_mention_order == 1
        assert result.sentiments[0].sentiment == "positive"
        assert result.semantic_facts[0].fact_type == "product"
        assert repository.upserts[0].task_key == SEMANTIC_ANALYSIS_TASK_KEY
        assert client.created_tasks == 1
        assert client.committed_items is not None

    asyncio.run(run())


def test_kmindhub_semantic_analyzer_sends_entity_context_to_preview() -> None:
    async def run() -> None:
        client = FakeKMindHubClient(preview_items=[])

        await KMindHubGeoRunResultAnalyzer(
            FakeRepository(),
            FakeWorkspaceResolver(),
            client,
        ).analyze(_command())

        assert client.preview_text is not None
        assert "Entity context:" in client.preview_text
        assert f"entityId: {OWN_BRAND_ID}" in client.preview_text
        assert "entityRole: own_brand" in client.preview_text
        assert "entityName: Acme" in client.preview_text
        assert f"entityId: {COMPETITOR_ID}" in client.preview_text
        assert "entityRole: competitor" in client.preview_text
        assert "entityName: Rival" in client.preview_text
        assert "AI answer:" in client.preview_text
        assert "Acme ERP" in client.preview_text

    asyncio.run(run())


def test_kmindhub_semantic_analyzer_reuses_active_task_mapping() -> None:
    async def run() -> None:
        repository = FakeRepository(mapping=_mapping(TASK_ID))
        client = FakeKMindHubClient(preview_items=[])

        result = await KMindHubGeoRunResultAnalyzer(
            repository,
            FakeWorkspaceResolver(),
            client,
        ).analyze(_command())

        assert result.status == "completed"
        assert result.entity_mentions == []
        assert client.created_tasks == 0
        assert repository.upserts == []

    asyncio.run(run())


def test_kmindhub_semantic_analyzer_rejects_failed_preview_verification() -> None:
    async def run() -> None:
        client = FakeKMindHubClient(
            preview_items=[
                KMindHubExtractionPreviewItem(
                    fields={},
                    verification={"passed": False},
                )
            ]
        )

        with pytest.raises(KMindHubExtractionValidationError):
            await KMindHubGeoRunResultAnalyzer(
                FakeRepository(),
                FakeWorkspaceResolver(),
                client,
            ).analyze(_command())
        assert client.committed_items is None

    asyncio.run(run())


@pytest.mark.parametrize(
    ("field_name", "field_value"),
    [
        ("entityId", "not-a-uuid"),
        ("entityRole", "other"),
        ("sentiment", "neutral"),
        ("factType", "brand"),
        ("confidence", "1.5"),
    ],
)
def test_kmindhub_semantic_analyzer_rejects_invalid_preview_values(
    field_name: str,
    field_value: str,
) -> None:
    async def run() -> None:
        item = _complete_item()
        item.fields[field_name] = KMindHubExtractionFieldValue(value=field_value)
        client = FakeKMindHubClient(preview_items=[item])

        with pytest.raises(KMindHubExtractionValidationError):
            await KMindHubGeoRunResultAnalyzer(
                FakeRepository(),
                FakeWorkspaceResolver(),
                client,
            ).analyze(_command())
        assert client.committed_items is None

    asyncio.run(run())


def test_kmindhub_semantic_analyzer_rejects_missing_evidence_text() -> None:
    async def run() -> None:
        item = _complete_item()
        item.fields["evidenceText"] = KMindHubExtractionFieldValue(
            value="not in raw response"
        )
        client = FakeKMindHubClient(preview_items=[item])

        with pytest.raises(KMindHubExtractionValidationError):
            await KMindHubGeoRunResultAnalyzer(
                FakeRepository(),
                FakeWorkspaceResolver(),
                client,
            ).analyze(_command())
        assert client.committed_items is None

    asyncio.run(run())


def test_kmindhub_semantic_analyzer_rejects_context_only_evidence_text() -> None:
    async def run() -> None:
        item = _complete_item()
        item.fields["evidenceText"] = KMindHubExtractionFieldValue(
            value=str(COMPETITOR_ID)
        )
        client = FakeKMindHubClient(preview_items=[item])

        with pytest.raises(
            KMindHubExtractionValidationError,
            match="evidenceText must exist in raw response",
        ):
            await KMindHubGeoRunResultAnalyzer(
                FakeRepository(),
                FakeWorkspaceResolver(),
                client,
            ).analyze(_command())
        assert client.preview_text is not None
        assert str(COMPETITOR_ID) in client.preview_text
        assert client.committed_items is None

    asyncio.run(run())


@pytest.mark.parametrize("field_value", [None, ""])
def test_kmindhub_semantic_analyzer_accepts_empty_evidence_text(field_value) -> None:
    async def run() -> None:
        item = _complete_item()
        item.fields["evidenceText"] = KMindHubExtractionFieldValue(value=field_value)
        client = FakeKMindHubClient(preview_items=[item])

        result = await KMindHubGeoRunResultAnalyzer(
            FakeRepository(),
            FakeWorkspaceResolver(),
            client,
        ).analyze(_command())

        assert result.entity_mentions[0].evidence_text is None
        assert result.sentiments[0].evidence_text is None
        assert result.semantic_facts[0].evidence_text is None
        assert client.committed_items is not None

    asyncio.run(run())


def test_kmindhub_semantic_analyzer_accepts_missing_evidence_text_field() -> None:
    async def run() -> None:
        item = _complete_item()
        del item.fields["evidenceText"]
        client = FakeKMindHubClient(preview_items=[item])

        result = await KMindHubGeoRunResultAnalyzer(
            FakeRepository(),
            FakeWorkspaceResolver(),
            client,
        ).analyze(_command())

        assert result.entity_mentions[0].evidence_text is None
        assert result.sentiments[0].evidence_text is None
        assert result.semantic_facts[0].evidence_text is None
        assert client.committed_items is not None

    asyncio.run(run())


def test_kmindhub_semantic_analyzer_accepts_unmentioned_entity_without_position_or_evidence() -> None:
    async def run() -> None:
        item = _complete_item()
        item.fields["mentioned"] = KMindHubExtractionFieldValue(value="false")
        del item.fields["firstMentionOrder"]
        del item.fields["evidenceText"]
        client = FakeKMindHubClient(preview_items=[item])

        result = await KMindHubGeoRunResultAnalyzer(
            FakeRepository(),
            FakeWorkspaceResolver(),
            client,
        ).analyze(_command())

        assert result.entity_mentions[0].mentioned is False
        assert result.entity_mentions[0].first_mention_order is None
        assert result.entity_mentions[0].evidence_text is None
        assert client.committed_items is not None

    asyncio.run(run())


def test_kmindhub_semantic_analyzer_skips_incomplete_fact_fields() -> None:
    async def run() -> None:
        item = KMindHubExtractionPreviewItem(
            fields={
                "entityId": KMindHubExtractionFieldValue(value=str(OWN_BRAND_ID)),
                "entityRole": KMindHubExtractionFieldValue(value="own_brand"),
                "entityName": KMindHubExtractionFieldValue(value="Acme"),
                "factType": KMindHubExtractionFieldValue(value="product"),
            },
            verification={"passed": True},
        )
        client = FakeKMindHubClient(preview_items=[item])

        result = await KMindHubGeoRunResultAnalyzer(
            FakeRepository(),
            FakeWorkspaceResolver(),
            client,
        ).analyze(_command())

        assert result.entity_mentions == []
        assert result.sentiments == []
        assert result.semantic_facts == []
        assert client.committed_items is not None

    asyncio.run(run())


def test_kmindhub_semantic_analyzer_preserves_client_unavailable_error() -> None:
    async def run() -> None:
        client = FakeKMindHubClient(preview_items=[], unavailable=True)

        with pytest.raises(KMindHubExtractionUnavailable):
            await KMindHubGeoRunResultAnalyzer(
                FakeRepository(),
                FakeWorkspaceResolver(),
                client,
            ).analyze(_command())

    asyncio.run(run())


def test_kmindhub_semantic_analyzer_reports_invalid_entity_id_value() -> None:
    async def run() -> None:
        item = _complete_item()
        item.fields["entityId"] = KMindHubExtractionFieldValue(value="Acme")
        client = FakeKMindHubClient(preview_items=[item])

        with pytest.raises(
            KMindHubExtractionValidationError,
            match="entityId must be a UUID: Acme",
        ):
            await KMindHubGeoRunResultAnalyzer(
                FakeRepository(),
                FakeWorkspaceResolver(),
                client,
            ).analyze(_command())
        assert client.committed_items is None

    asyncio.run(run())


def _command() -> AnalyzeGeoRunResultCommand:
    return AnalyzeGeoRunResultCommand(
        tenant_id=TENANT_ID,
        run_result_id=RUN_RESULT_ID,
        project_id=uuid4(),
        query_id=uuid4(),
        query_text="哪個 ERP 適合製造業？",
        provider="gemini",
        surface="ai_overview",
        model="gemini-2.5-pro",
        region="TW",
        language="zh-TW",
        raw_response="Acme ERP 適合製造業。",
        entities=GeoAnalysisEntityContext(
            own_brand=GeoAnalysisEntityInput(
                entity_id=OWN_BRAND_ID,
                entity_role="own_brand",
                name="Acme",
                website_url="https://acme.example",
            ),
            competitors=[
                GeoAnalysisEntityInput(
                    entity_id=COMPETITOR_ID,
                    entity_role="competitor",
                    name="Rival",
                    website_url="https://rival.example",
                )
            ],
        ),
    )


def _complete_item() -> KMindHubExtractionPreviewItem:
    return KMindHubExtractionPreviewItem(
        fields={
            "entityId": KMindHubExtractionFieldValue(value=str(OWN_BRAND_ID)),
            "entityRole": KMindHubExtractionFieldValue(value="own_brand"),
            "entityName": KMindHubExtractionFieldValue(value="Acme"),
            "mentioned": KMindHubExtractionFieldValue(value="true"),
            "firstMentionOrder": KMindHubExtractionFieldValue(value="1"),
            "sentiment": KMindHubExtractionFieldValue(value="positive"),
            "theme": KMindHubExtractionFieldValue(value="fit"),
            "statement": KMindHubExtractionFieldValue(value="Acme ERP 適合製造業。"),
            "factType": KMindHubExtractionFieldValue(value="product"),
            "value": KMindHubExtractionFieldValue(value="ERP"),
            "evidenceText": KMindHubExtractionFieldValue(value="Acme ERP"),
            "confidence": KMindHubExtractionFieldValue(value="0.9"),
        },
        verification={"passed": True},
    )


def _mapping(task_id: UUID) -> KMindHubExtractionTaskMappingRecord:
    return KMindHubExtractionTaskMappingRecord(
        id=uuid4(),
        tenant_id=TENANT_ID,
        workspace_id=WORKSPACE_ID,
        task_key=SEMANTIC_ANALYSIS_TASK_KEY,
        schema_version=SEMANTIC_ANALYSIS_SCHEMA_VERSION,
        kmindhub_task_id=task_id,
        status="active",
        created_at="2026-07-05T00:00:00Z",
        updated_at="2026-07-05T00:00:00Z",
    )
