import asyncio
from dataclasses import dataclass, field
import logging
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
    geo_semantic_analysis_task_definition,
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
    preview_item_batches: list[list[KMindHubExtractionPreviewItem]] | None = None
    unavailable: bool = False
    created_tasks: int = 0
    committed_items: list[dict] | None = None
    preview_text: str | None = None
    preview_texts: list[str] = field(default_factory=list)

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
        self.preview_texts.append(text)
        items = self.preview_items
        if self.preview_item_batches is not None:
            batch_index = len(self.preview_texts) - 1
            items = self.preview_item_batches[
                min(batch_index, len(self.preview_item_batches) - 1)
            ]
        return KMindHubExtractionPreviewResult(
            task_id=task_id,
            items=items,
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
        assert result.analyzer_version == "geo_semantic_analysis:v4"
        assert result.entity_mentions[0].entity_id == OWN_BRAND_ID
        assert result.entity_mentions[0].first_mention_order == 1
        assert result.sentiments[0].sentiment == "positive"
        assert result.semantic_facts[0].fact_type == "product"
        assert repository.upserts[0].task_key == SEMANTIC_ANALYSIS_TASK_KEY
        assert repository.upserts[0].schema_version == 4
        assert client.created_tasks == 1
        assert client.committed_items is not None

    asyncio.run(run())


def test_kmindhub_semantic_task_definition_preserves_markdown_in_evidence() -> None:
    definition = geo_semantic_analysis_task_definition()
    fields = {field.name: field for field in definition.fields}

    assert definition.schema_version == 4
    assert definition.name == "GEO semantic analysis v4"
    assert "preserve all Markdown delimiters" in definition.task
    assert "including Markdown formatting syntax" in definition.description
    assert "confidence" not in fields
    assert "Copy the exact UUID from Entity context" in fields[
        "entityId"
    ].normalization["instruction"]
    assert "exact contiguous substring copied from the AI answer" in fields[
        "evidenceText"
    ].normalization["instruction"]
    assert "Do not paraphrase" in fields["evidenceText"].normalization[
        "instruction"
    ]
    assert "Bad evidenceText" in fields["evidenceText"].normalization["instruction"]
    assert "Good evidenceText" in fields["evidenceText"].normalization["instruction"]
    assert "leave evidenceText empty" in fields["evidenceText"].normalization[
        "instruction"
    ]
    assert (
        "including all Markdown formatting delimiters"
        in fields["evidenceText"].description
    )
    assert (
        "Preserve every original character"
        in fields["evidenceText"].normalization["instruction"]
    )
    assert "**Acme**" in fields["evidenceText"].normalization["instruction"]


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
        assert "--- BEGIN AI ANSWER ---" in client.preview_text
        assert "Acme ERP" in client.preview_text
        assert "--- END AI ANSWER ---" in client.preview_text

    asyncio.run(run())


def test_kmindhub_semantic_analyzer_repairs_evidence_text_from_exact_excerpt() -> None:
    async def run() -> None:
        item = _complete_item()
        item.fields["evidenceText"] = KMindHubExtractionFieldValue(
            value="Acme is a strong ERP option.",
            evidence=[
                {
                    "excerpt": "Acme ERP",
                    "source": {"sourceId": "inline-text", "mediaType": "text"},
                }
            ],
        )
        client = FakeKMindHubClient(preview_items=[item])

        result = await KMindHubGeoRunResultAnalyzer(
            FakeRepository(),
            FakeWorkspaceResolver(),
            client,
        ).analyze(_command())

        assert result.status == "completed"
        assert len(client.preview_texts) == 1
        assert result.entity_mentions[0].evidence_text == "Acme ERP"
        assert result.sentiments[0].evidence_text == "Acme ERP"
        assert result.semantic_facts[0].evidence_text == "Acme ERP"
        assert client.committed_items is not None
        assert (
            client.committed_items[0]["fields"]["evidenceText"]["value"]
            == "Acme ERP"
        )

    asyncio.run(run())


def test_kmindhub_semantic_analyzer_preserves_markdown_evidence() -> None:
    async def run() -> None:
        item = _complete_item()
        item.fields["statement"] = KMindHubExtractionFieldValue(
            value="活粒適的膠囊形式通常被認為添加物較少。"
        )
        item.fields["evidenceText"] = KMindHubExtractionFieldValue(
            value="**活粒適**的膠囊形式通常被認為添加物較少",
            evidence=[
                {
                    "excerpt": "**活粒適**的膠囊形式通常被認為添加物較少",
                    "source": {"sourceId": "inline-text", "mediaType": "text"},
                }
            ],
        )
        command = _command().model_copy(
            update={
                "raw_response": (
                    "如果您非常在意成分單純，**活粒適**的膠囊形式通常被認為添加物較少。"
                )
            }
        )
        client = FakeKMindHubClient(preview_items=[item])

        result = await KMindHubGeoRunResultAnalyzer(
            FakeRepository(),
            FakeWorkspaceResolver(),
            client,
        ).analyze(command)

        expected = "**活粒適**的膠囊形式通常被認為添加物較少"
        assert result.status == "completed"
        assert result.entity_mentions[0].evidence_text == expected
        assert result.sentiments[0].evidence_text == expected
        assert result.semantic_facts[0].evidence_text == expected
        assert client.committed_items is not None
        assert client.committed_items[0]["fields"]["evidenceText"]["value"] == expected

    asyncio.run(run())


def test_kmindhub_semantic_analyzer_ignores_preview_confidence_field() -> None:
    async def run() -> None:
        item = _complete_item()
        item.fields["confidence"] = KMindHubExtractionFieldValue(value="missing-evidence")
        client = FakeKMindHubClient(preview_items=[item])

        result = await KMindHubGeoRunResultAnalyzer(
            FakeRepository(),
            FakeWorkspaceResolver(),
            client,
        ).analyze(_command())

        assert result.status == "completed"
        assert result.entity_mentions[0].confidence is None
        assert result.sentiments[0].confidence is None
        assert result.semantic_facts[0].confidence is None

    asyncio.run(run())


def test_kmindhub_semantic_analyzer_repairs_invalid_evidence_once() -> None:
    async def run() -> None:
        invalid_item = _complete_item()
        invalid_item.fields["evidenceText"] = KMindHubExtractionFieldValue(
            value="not in raw response"
        )
        valid_item = _complete_item()
        client = FakeKMindHubClient(
            preview_items=[],
            preview_item_batches=[[invalid_item], [valid_item]],
        )

        result = await KMindHubGeoRunResultAnalyzer(
            FakeRepository(),
            FakeWorkspaceResolver(),
            client,
        ).analyze(_command())

        assert result.status == "completed"
        assert len(client.preview_texts) == 2
        assert "Repair instructions:" in client.preview_texts[1]
        assert (
            "evidenceText was not an exact substring of the AI answer"
            in client.preview_texts[1]
        )
        assert "not in raw response" not in client.preview_texts[1]
        assert "exact contiguous substring from the AI answer" in client.preview_texts[1]
        assert "preserve Markdown delimiters" in client.preview_texts[1]
        assert "copied raw answer substring, or leave evidenceText empty" in client.preview_texts[1]
        assert "Do not extract facts from these repair instructions" in client.preview_texts[1]
        assert client.preview_texts[1].index("--- END AI ANSWER ---") < client.preview_texts[
            1
        ].index("Repair instructions:")
        assert client.committed_items is not None
        assert (
            client.committed_items[0]["fields"]["evidenceText"]["value"]
            == "Acme ERP"
        )

    asyncio.run(run())


def test_kmindhub_semantic_analyzer_repairs_invalid_entity_id_once() -> None:
    async def run() -> None:
        invalid_item = _complete_item()
        invalid_item.fields["entityId"] = KMindHubExtractionFieldValue(value="Acme")
        valid_item = _complete_item()
        client = FakeKMindHubClient(
            preview_items=[],
            preview_item_batches=[[invalid_item], [valid_item]],
        )

        result = await KMindHubGeoRunResultAnalyzer(
            FakeRepository(),
            FakeWorkspaceResolver(),
            client,
        ).analyze(_command())

        assert result.status == "completed"
        assert len(client.preview_texts) == 2
        assert "Repair instructions:" in client.preview_texts[1]
        assert "entityId must be a UUID: Acme" in client.preview_texts[1]
        assert "entityId must be copied exactly as a UUID" in client.preview_texts[1]
        assert client.committed_items is not None

    asyncio.run(run())


def test_kmindhub_semantic_analyzer_fails_after_one_repair_attempt() -> None:
    async def run() -> None:
        invalid_item = _complete_item()
        invalid_item.fields["evidenceText"] = KMindHubExtractionFieldValue(
            value="not in raw response"
        )
        client = FakeKMindHubClient(
            preview_items=[],
            preview_item_batches=[[invalid_item], [invalid_item]],
        )

        with pytest.raises(
            KMindHubExtractionValidationError,
            match="evidenceText must exist in raw response",
        ):
            await KMindHubGeoRunResultAnalyzer(
                FakeRepository(),
                FakeWorkspaceResolver(),
                client,
            ).analyze(_command())

        assert len(client.preview_texts) == 2
        assert client.committed_items is None

    asyncio.run(run())


def test_kmindhub_semantic_analyzer_logs_validation_debug_payloads(caplog) -> None:
    async def run() -> None:
        invalid_item = _complete_item()
        invalid_item.fields["evidenceText"] = KMindHubExtractionFieldValue(
            value="not in raw response"
        )
        client = FakeKMindHubClient(
            preview_items=[],
            preview_item_batches=[[invalid_item], [invalid_item]],
        )

        with caplog.at_level(logging.WARNING):
            with pytest.raises(KMindHubExtractionValidationError):
                await KMindHubGeoRunResultAnalyzer(
                    FakeRepository(),
                    FakeWorkspaceResolver(),
                    client,
                    debug_payloads=True,
                ).analyze(_command())

        record = next(
            item
            for item in caplog.records
            if item.message.startswith(
                "KMindHub semantic preview validation debug payloads: "
            )
        )

        assert record.run_result_id == str(RUN_RESULT_ID)
        assert record.error == "evidenceText must exist in raw response: not in raw response"
        assert "AI answer:" in record.kmindhub_extraction_text
        assert "Acme ERP" in record.kmindhub_extraction_text
        assert '"kmindhubExtractionText":' in record.message
        assert "AI answer:" in record.message
        assert "Acme ERP" in record.message
        assert '"kmindhubPreviewItems":' in record.message
        assert "not in raw response" in record.message
        assert (
            record.kmindhub_preview_items[0]["fields"]["evidenceText"]["value"]
            == "not in raw response"
        )

    asyncio.run(run())


def test_kmindhub_semantic_analyzer_logs_actual_retry_request_text(caplog) -> None:
    async def run() -> None:
        invalid_evidence_item = _complete_item()
        invalid_evidence_item.fields["evidenceText"] = KMindHubExtractionFieldValue(
            value="not in raw response"
        )
        invalid_entity_item = _complete_item()
        invalid_entity_item.fields["entityId"] = KMindHubExtractionFieldValue(
            value="Acme"
        )
        client = FakeKMindHubClient(
            preview_items=[],
            preview_item_batches=[[invalid_evidence_item], [invalid_entity_item]],
        )

        with caplog.at_level(logging.WARNING):
            with pytest.raises(KMindHubExtractionValidationError):
                await KMindHubGeoRunResultAnalyzer(
                    FakeRepository(),
                    FakeWorkspaceResolver(),
                    client,
                    debug_payloads=True,
                ).analyze(_command())

        retry_record = [
            item
            for item in caplog.records
            if item.message.startswith(
                "KMindHub semantic preview validation debug payloads: "
            )
        ][1]

        assert "Previous preview failed validation: evidenceText was not an exact substring of the AI answer" in (
            retry_record.kmindhub_extraction_text
        )
        assert "Previous preview failed validation: evidenceText was not an exact substring of the AI answer" in (
            retry_record.message
        )
        assert "not in raw response" not in retry_record.kmindhub_extraction_text
        assert "entityId must be a UUID: Acme" not in retry_record.kmindhub_extraction_text

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
        assert len(client.preview_texts) == 2
        assert client.committed_items is None

    asyncio.run(run())


@pytest.mark.parametrize(
    ("field_name", "field_value"),
    [
        ("entityId", "not-a-uuid"),
        ("entityRole", "other"),
        ("sentiment", "neutral"),
        ("factType", "brand"),
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
        assert len(client.preview_texts) == 2
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
        assert len(client.preview_texts) == 2
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
        assert len(client.preview_texts) == 0

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
        assert len(client.preview_texts) == 2
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
