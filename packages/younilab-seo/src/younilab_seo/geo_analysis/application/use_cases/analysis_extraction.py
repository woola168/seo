from dataclasses import dataclass
import re
import unicodedata
from uuid import UUID

from younilab_seo.geo_analysis.application.contracts import (
    GeoRunResultCitationClassificationCommand,
    GeoRunResultEntityMentionCommand,
    GeoRunResultRecord,
    GeoRunResultStatementCommand,
    KMindHubExtractionTaskMappingCommand,
    SaveRunResultAnalysisCommand,
)
from younilab_seo.geo_analysis.application.interfaces import (
    Clock,
    GeoAnalysisRepository,
    KMindHubExtractionUnavailable,
    KMindHubExtractionValidationError,
    KMindHubWorkspaceClient,
    KMindHubWorkspaceResolver,
)
from younilab_seo.geo_analysis.application.kmindhub_extraction_schema import (
    ANALYSIS_SCHEMA_VERSION,
    ANALYSIS_TASK_KEY,
    ENTITY_TYPE_VALUES,
    SENTIMENT_VALUES,
    geo_answer_analysis_task_definition,
)


class RunResultAnalysisNotFound(LookupError):
    """指定 tenant 底下找不到可分析的 GEO run result。"""


@dataclass(frozen=True)
class RunKMindHubAnalysisExtraction:
    """將已保存的 GEO raw answer 送到 KMindHub Insight，並保存報表前處理結果。"""

    repository: GeoAnalysisRepository
    workspace_resolver: KMindHubWorkspaceResolver
    client: KMindHubWorkspaceClient
    clock: Clock

    async def execute(self, tenant_id: UUID, result_id: UUID):
        result = await self.repository.get_run_result(tenant_id, result_id)
        if result is None:
            raise RunResultAnalysisNotFound("run result not found")

        if result.status != "completed" or not result.raw_response.strip():
            return await self._save_failed(
                tenant_id,
                result_id,
                "run_result_not_extractable",
                "run result is not completed or raw response is empty",
            )

        try:
            task_id = await self._ensure_task(tenant_id)
            preview = await self.client.preview_text_extraction(
                workspace_id=await self.workspace_resolver.resolve_workspace_id(tenant_id),
                task_id=task_id,
                text=result.raw_response,
            )
            extraction = _analysis_command_from_preview(result, preview.items)
            commit = await self.client.commit_extraction_items(
                workspace_id=await self.workspace_resolver.resolve_workspace_id(tenant_id),
                task_id=task_id,
                items=[
                    {
                        "itemId": None,
                        "fields": {
                            name: value.model_dump(mode="json", by_alias=True)
                            for name, value in item.fields.items()
                        },
                    }
                    for item in preview.items
                ],
            )
            return await self.repository.save_run_result_analysis(
                tenant_id,
                extraction.command_with_item_ids(commit.item_ids).model_copy(
                    update={
                        "kmindhub_commit_batch_id": commit.commit_batch_id,
                        "kmindhub_item_id": commit.item_ids[0]
                        if commit.item_ids
                        else None,
                    }
                ),
                self.clock.now(),
            )
        except (
            KMindHubExtractionUnavailable,
            KMindHubExtractionValidationError,
            LookupError,
        ) as exc:
            return await self._save_failed(
                tenant_id,
                result_id,
                exc.__class__.__name__,
                str(exc),
            )

    async def _ensure_task(self, tenant_id: UUID) -> UUID:
        workspace_id = await self.workspace_resolver.resolve_workspace_id(tenant_id)
        current = await self.repository.get_kmindhub_extraction_task_mapping(
            tenant_id,
            ANALYSIS_TASK_KEY,
            ANALYSIS_SCHEMA_VERSION,
        )
        if current is not None and current.status == "active":
            return current.kmindhub_task_id

        definition = geo_answer_analysis_task_definition()
        task_id = await self.client.create_extraction_task(
            workspace_id=workspace_id,
            definition=definition,
        )
        mapping = await self.repository.upsert_kmindhub_extraction_task_mapping(
            tenant_id,
            KMindHubExtractionTaskMappingCommand(
                workspace_id=workspace_id,
                task_key=definition.task_key,
                schema_version=definition.schema_version,
                kmindhub_task_id=task_id,
                status="active",
            ),
        )
        return mapping.kmindhub_task_id

    async def _save_failed(
        self,
        tenant_id: UUID,
        result_id: UUID,
        error_code: str,
        error_message: str,
    ):
        return await self.repository.save_run_result_analysis(
            tenant_id,
            SaveRunResultAnalysisCommand(
                run_result_id=result_id,
                status="failed",
                error_code=error_code,
                error_message=error_message,
            ),
            self.clock.now(),
        )


@dataclass(frozen=True)
class _PreviewAnalysisCommand:
    command: SaveRunResultAnalysisCommand
    mention_item_indexes: list[int]
    statement_item_indexes: list[int]

    def command_with_item_ids(
        self,
        item_ids: list[str],
    ) -> SaveRunResultAnalysisCommand:
        return self.command.model_copy(
            update={
                "entity_mentions": [
                    mention.model_copy(
                        update={
                            "kmindhub_item_id": _item_id_at(
                                item_ids,
                                self.mention_item_indexes[index],
                            )
                        }
                    )
                    for index, mention in enumerate(self.command.entity_mentions)
                ],
                "statements": [
                    statement.model_copy(
                        update={
                            "kmindhub_item_id": _item_id_at(
                                item_ids,
                                self.statement_item_indexes[index],
                            )
                        }
                    )
                    for index, statement in enumerate(self.command.statements)
                ],
            }
        )


def _analysis_command_from_preview(
    result: GeoRunResultRecord,
    items,
) -> _PreviewAnalysisCommand:
    if not items:
        raise KMindHubExtractionValidationError("KMindHub preview returned no items")
    for item in items:
        verification = item.verification or {}
        if verification and verification.get("passed") is False:
            raise KMindHubExtractionValidationError("KMindHub preview verification failed")

    fields = items[0].fields
    summary = _string_value(fields, "summary")
    sentiment = _enum_value(fields, "overallSentiment", SENTIMENT_VALUES)
    theme = _string_value(fields, "theme")
    mentions = []
    mention_item_indexes = []
    statements = []
    statement_item_indexes = []
    for index, item in enumerate(items):
        mention = _mention_from_item(item, result.raw_response)
        if mention is not None:
            mentions.append(mention)
            mention_item_indexes.append(index)
        statement = _statement_from_item(item, result.raw_response)
        if statement is not None:
            statements.append(statement)
            statement_item_indexes.append(index)
    citations = [
        GeoRunResultCitationClassificationCommand(
            run_result_reference_id=reference.id,
            classification="unknown",
            matched_domain=reference.domain,
            confidence=0,
        )
        for reference in result.references
    ]
    return _PreviewAnalysisCommand(
        command=SaveRunResultAnalysisCommand(
            run_result_id=result.id,
            task_key=ANALYSIS_TASK_KEY,
            schema_version=ANALYSIS_SCHEMA_VERSION,
            status="completed",
            summary=summary,
            overall_sentiment=sentiment,
            theme=theme,
            entity_mentions=mentions,
            statements=statements,
            citation_classifications=citations,
        ),
        mention_item_indexes=mention_item_indexes,
        statement_item_indexes=statement_item_indexes,
    )


def _mention_from_item(item, raw_response: str):
    fields = item.fields
    entity_name = _string_value(fields, "entityName")
    if not entity_name:
        return None
    evidence_text = _validated_evidence(fields, raw_response)
    return GeoRunResultEntityMentionCommand(
        entity_name=entity_name,
        entity_type=_enum_value(fields, "entityType", ENTITY_TYPE_VALUES) or "other",
        mention_count=_int_value(fields, "mentionCount"),
        sentiment=_enum_value(fields, "overallSentiment", SENTIMENT_VALUES) or "unknown",
        evidence_text=evidence_text,
    )


def _statement_from_item(item, raw_response: str):
    fields = item.fields
    statement_text = _string_value(fields, "statementText")
    if not statement_text:
        return None
    evidence_text = _validated_evidence(fields, raw_response)
    return GeoRunResultStatementCommand(
        statement_text=statement_text,
        theme=_string_value(fields, "theme") or "",
        sentiment=_enum_value(fields, "statementSentiment", SENTIMENT_VALUES) or "unknown",
        subject_entity_name=_string_value(fields, "subjectEntityName"),
        evidence_text=evidence_text,
    )


def _string_value(fields: dict, name: str) -> str | None:
    value = fields.get(name)
    if value is None or value.value is None:
        return None
    text = str(value.value).strip()
    return text or None


def _enum_value(fields: dict, name: str, allowed: frozenset[str]) -> str | None:
    value = _string_value(fields, name)
    if value is None:
        return None
    normalized = value.lower()
    if normalized not in allowed:
        raise KMindHubExtractionValidationError(
            f"{name} must be one of {', '.join(sorted(allowed))}"
        )
    return normalized


def _int_value(fields: dict, name: str) -> int:
    value = fields.get(name)
    if value is None or value.value in (None, ""):
        return 0
    try:
        count = int(value.value)
    except (TypeError, ValueError) as exc:
        raise KMindHubExtractionValidationError(f"{name} must be an integer") from exc
    if count < 0:
        raise KMindHubExtractionValidationError(f"{name} must be zero or positive")
    return count


def _validated_evidence(fields: dict, raw_response: str) -> str:
    evidence = _string_value(fields, "evidenceText") or ""
    if evidence and _normalize_evidence(evidence) not in _normalize_evidence(raw_response):
        raise KMindHubExtractionValidationError(
            "evidenceText must exist in raw response"
        )
    return evidence


def _normalize_evidence(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value)
    return re.sub(r"\s+", " ", normalized).strip()


def _item_id_at(item_ids: list[str], index: int) -> str | None:
    return item_ids[index] if index < len(item_ids) else None
