from dataclasses import dataclass, field
import asyncio
import json
import logging
import re
import unicodedata
from uuid import UUID

import httpx
from pydantic import ValidationError

from younilab_seo.geo_analysis.application import (
    AnalyzeGeoRunResultCommand,
    GeoEntityMentionFact,
    GeoResponseSemanticFact,
    GeoRunResultAnalysis,
    GeoSentimentFact,
    KMindHubExtractionTaskMappingCommand,
    KMindHubExtractionCommitResult,
    KMindHubExtractionFieldValue,
    KMindHubExtractionPreviewItem,
    KMindHubExtractionPreviewResult,
    KMindHubExtractionTaskDefinition,
    KMindHubExtractionUnavailable,
    KMindHubExtractionValidationError,
    KMindHubWorkspaceClient,
    KMindHubWorkspaceProvisionUnavailable,
    KMindHubWorkspaceResolver,
    GeoAnalysisRepository,
)
from younilab_seo.geo_analysis.application.kmindhub_extraction_schema import (
    SEMANTIC_ANALYSIS_SCHEMA_VERSION,
    SEMANTIC_ANALYSIS_TASK_KEY,
    geo_semantic_analysis_task_definition,
)


SEMANTIC_ANALYZER_NAME = "kmindhub"
SEMANTIC_ANALYZER_VERSION = (
    f"{SEMANTIC_ANALYSIS_TASK_KEY}:v{SEMANTIC_ANALYSIS_SCHEMA_VERSION}"
)
logger = logging.getLogger(__name__)
SEMANTIC_PREVIEW_REPAIR_RETRY_LIMIT = 1
KMINDHUB_PREVIEW_RETRY_STATUS_CODES = frozenset({429, 500, 502, 503, 504})


@dataclass(frozen=True)
class KMindHubGeoRunResultAnalyzer:
    """透過 KMindHub extraction API 產生 GEO semantic facts。"""

    repository: GeoAnalysisRepository
    workspace_resolver: KMindHubWorkspaceResolver
    client: KMindHubWorkspaceClient
    debug_payloads: bool = False

    async def analyze(
        self,
        command: AnalyzeGeoRunResultCommand,
    ) -> GeoRunResultAnalysis:
        workspace_id = await self.workspace_resolver.resolve_workspace_id(
            command.tenant_id
        )
        task_id = await self._ensure_task(command.tenant_id, workspace_id)
        preview, facts = await self._preview_validated_facts(
            command=command,
            workspace_id=workspace_id,
            task_id=task_id,
        )
        await self.client.commit_extraction_items(
            workspace_id=workspace_id,
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
        return facts

    async def _preview_validated_facts(
        self,
        *,
        command: AnalyzeGeoRunResultCommand,
        workspace_id: UUID,
        task_id: UUID,
    ) -> tuple[KMindHubExtractionPreviewResult, GeoRunResultAnalysis]:
        extraction_text = _semantic_extraction_text(command)
        last_error: KMindHubExtractionValidationError | None = None

        for attempt in range(SEMANTIC_PREVIEW_REPAIR_RETRY_LIMIT + 1):
            request_text = (
                extraction_text
                if attempt == 0
                else _semantic_repair_extraction_text(
                    extraction_text,
                    last_error,
                )
            )
            preview = await self.client.preview_text_extraction(
                workspace_id=workspace_id,
                task_id=task_id,
                text=request_text,
            )
            try:
                facts = _facts_from_preview(
                    command,
                    preview.items,
                    workspace_id,
                    task_id,
                )
            except KMindHubExtractionValidationError as exc:
                last_error = exc
                if self.debug_payloads:
                    _log_semantic_preview_debug_payloads(
                        command=command,
                        workspace_id=workspace_id,
                        task_id=task_id,
                        attempt=attempt + 1,
                        extraction_text=request_text,
                        preview=preview,
                        error=exc,
                    )
                if attempt >= SEMANTIC_PREVIEW_REPAIR_RETRY_LIMIT:
                    raise
                logger.info(
                    "Retrying KMindHub semantic preview after validation failure",
                    extra={
                        "run_result_id": str(command.run_result_id),
                        "workspace_id": str(workspace_id),
                        "task_id": str(task_id),
                        "attempt": attempt + 1,
                        "max_attempts": SEMANTIC_PREVIEW_REPAIR_RETRY_LIMIT + 1,
                        "error": _safe_text(str(exc)),
                    },
                )
                continue
            return preview, facts

        raise last_error or KMindHubExtractionValidationError(
            "KMindHub preview validation failed"
        )

    async def _ensure_task(self, tenant_id: UUID, workspace_id: UUID) -> UUID:
        current = await self.repository.get_kmindhub_extraction_task_mapping(
            tenant_id,
            SEMANTIC_ANALYSIS_TASK_KEY,
            SEMANTIC_ANALYSIS_SCHEMA_VERSION,
        )
        if current is not None and current.status == "active":
            return current.kmindhub_task_id

        definition = geo_semantic_analysis_task_definition()
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


def _facts_from_preview(
    command: AnalyzeGeoRunResultCommand,
    items: list[KMindHubExtractionPreviewItem],
    workspace_id: UUID,
    task_id: UUID,
) -> GeoRunResultAnalysis:
    entity_mentions: list[GeoEntityMentionFact] = []
    sentiments: list[GeoSentimentFact] = []
    semantic_facts: list[GeoResponseSemanticFact] = []

    for index, item in enumerate(items):
        verification = item.verification or {}
        if verification and verification.get("passed") is False:
            logger.warning(
                "KMindHub semantic preview verification failed",
                extra={
                    "run_result_id": str(command.run_result_id),
                    "workspace_id": str(workspace_id),
                    "task_id": str(task_id),
                    "item_index": index,
                    "field_names": sorted(item.fields),
                    "entity_id_preview": _safe_text(_string_value(item.fields, "entityId")),
                    "verification": _safe_dict(verification),
                },
            )
            raise KMindHubExtractionValidationError("KMindHub preview verification failed")
        try:
            mention = _mention_from_item(item, command.raw_response)
            if mention is not None:
                entity_mentions.append(mention)
            sentiment = _sentiment_from_item(item, command.raw_response)
            if sentiment is not None:
                sentiments.append(sentiment)
            fact = _semantic_fact_from_item(item, command.raw_response)
            if fact is not None:
                semantic_facts.append(fact)
        except ValidationError as exc:
            logger.warning(
                "KMindHub semantic preview pydantic validation failed",
                extra={
                    "run_result_id": str(command.run_result_id),
                    "workspace_id": str(workspace_id),
                    "task_id": str(task_id),
                    "item_index": index,
                    "field_names": sorted(item.fields),
                    "entity_id_preview": _safe_text(_string_value(item.fields, "entityId")),
                },
            )
            raise KMindHubExtractionValidationError(
                "KMindHub preview validation failed"
            ) from exc
        except KMindHubExtractionValidationError:
            logger.warning(
                "KMindHub semantic preview field validation failed",
                extra={
                    "run_result_id": str(command.run_result_id),
                    "workspace_id": str(workspace_id),
                    "task_id": str(task_id),
                    "item_index": index,
                    "field_names": sorted(item.fields),
                    "entity_id_preview": _safe_text(_string_value(item.fields, "entityId")),
                },
            )
            raise

    return GeoRunResultAnalysis(
        run_result_id=command.run_result_id,
        analyzer=SEMANTIC_ANALYZER_NAME,
        analyzer_version=SEMANTIC_ANALYZER_VERSION,
        status="completed",
        entity_mentions=entity_mentions,
        sentiments=sentiments,
        semantic_facts=semantic_facts,
    )


def _mention_from_item(
    item: KMindHubExtractionPreviewItem,
    raw_response: str,
) -> GeoEntityMentionFact | None:
    fields = item.fields
    if not _has_fields(fields, "entityId", "entityRole", "entityName", "mentioned"):
        return None
    return GeoEntityMentionFact(
        entity_id=_uuid_value(fields, "entityId"),
        entity_role=_string_value(fields, "entityRole"),
        entity_name=_string_value(fields, "entityName"),
        mentioned=_bool_value(fields, "mentioned"),
        first_mention_order=_int_value(fields, "firstMentionOrder"),
        evidence_text=_validated_evidence(fields, raw_response),
    )


def _sentiment_from_item(
    item: KMindHubExtractionPreviewItem,
    raw_response: str,
) -> GeoSentimentFact | None:
    fields = item.fields
    if not _has_fields(
        fields,
        "entityId",
        "entityRole",
        "entityName",
        "sentiment",
        "theme",
        "statement",
    ):
        return None
    return GeoSentimentFact(
        entity_id=_uuid_value(fields, "entityId"),
        entity_role=_string_value(fields, "entityRole"),
        entity_name=_string_value(fields, "entityName"),
        sentiment=_string_value(fields, "sentiment"),
        theme=_string_value(fields, "theme"),
        statement=_string_value(fields, "statement"),
        evidence_text=_validated_evidence(fields, raw_response),
    )


def _semantic_fact_from_item(
    item: KMindHubExtractionPreviewItem,
    raw_response: str,
) -> GeoResponseSemanticFact | None:
    fields = item.fields
    if not _has_fields(fields, "factType", "value"):
        return None
    return GeoResponseSemanticFact(
        fact_type=_string_value(fields, "factType"),
        value=_string_value(fields, "value"),
        evidence_text=_validated_evidence(fields, raw_response),
    )


def _has_fields(
    fields: dict[str, KMindHubExtractionFieldValue],
    *names: str,
) -> bool:
    return all(_string_value(fields, name) is not None for name in names)


def _string_value(
    fields: dict[str, KMindHubExtractionFieldValue],
    name: str,
) -> str | None:
    value = fields.get(name)
    if value is None or value.value in (None, ""):
        return None
    text = str(value.value).strip()
    return text or None


def _uuid_value(fields: dict[str, KMindHubExtractionFieldValue], name: str) -> UUID:
    value = _string_value(fields, name)
    try:
        return UUID(str(value))
    except (TypeError, ValueError) as exc:
        raise KMindHubExtractionValidationError(
            f"{name} must be a UUID: {_safe_text(value)}"
        ) from exc


def _bool_value(fields: dict[str, KMindHubExtractionFieldValue], name: str) -> bool:
    value = _string_value(fields, name)
    if value is None:
        raise KMindHubExtractionValidationError(f"{name} must be a boolean")
    normalized = value.lower()
    if normalized in {"true", "1", "yes"}:
        return True
    if normalized in {"false", "0", "no"}:
        return False
    raise KMindHubExtractionValidationError(f"{name} must be a boolean")


def _int_value(
    fields: dict[str, KMindHubExtractionFieldValue],
    name: str,
) -> int | None:
    value = _string_value(fields, name)
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise KMindHubExtractionValidationError(f"{name} must be an integer") from exc


def _validated_evidence(
    fields: dict[str, KMindHubExtractionFieldValue],
    raw_response: str,
) -> str | None:
    field = fields.get("evidenceText")
    evidence = _string_value(fields, "evidenceText")
    if evidence is None:
        return None
    if _evidence_exists_in_raw_response(evidence, raw_response):
        return evidence

    repaired = _repair_evidence_from_excerpts(field, raw_response)
    if repaired is not None and field is not None:
        fields["evidenceText"] = field.model_copy(update={"value": repaired})
        return repaired

    raise KMindHubExtractionValidationError(
        f"evidenceText must exist in raw response: {_safe_text(evidence)}"
    )


def _repair_evidence_from_excerpts(
    field: KMindHubExtractionFieldValue | None,
    raw_response: str,
) -> str | None:
    if field is None:
        return None
    for evidence_item in field.evidence:
        if not isinstance(evidence_item, dict):
            continue
        excerpt = evidence_item.get("excerpt")
        if not isinstance(excerpt, str):
            continue
        excerpt = excerpt.strip()
        if not excerpt:
            continue
        if _evidence_exists_in_raw_response(excerpt, raw_response):
            return excerpt
    return None


def _evidence_exists_in_raw_response(evidence: str, raw_response: str) -> bool:
    if not evidence:
        return False
    return _normalize_evidence(evidence) in _normalize_evidence(raw_response)


def _normalize_evidence(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value)
    return re.sub(r"\s+", " ", normalized).strip()


def _semantic_extraction_text(command: AnalyzeGeoRunResultCommand) -> str:
    entity_lines = [
        _entity_context_line(command.entities.own_brand),
        *(_entity_context_line(entity) for entity in command.entities.competitors),
    ]
    topic_lines = []
    if command.topic_id is not None:
        topic_lines.append(f"- topicId: {command.topic_id}")
    if command.topic_name:
        topic_lines.append(f"- topicName: {command.topic_name}")
    if command.topic_description:
        topic_lines.append(f"- topicDescription: {command.topic_description}")

    topic_text = "\n".join(topic_lines) if topic_lines else "- topic: none"
    return "\n".join(
        [
            "GEO semantic analysis input",
            "",
            "Instructions:",
            "- Extract facts only from the AI answer section.",
            "- For entity mention and sentiment facts, entityId must be copied exactly from the entity context below.",
            "- Do not invent entityId values. If an entity is not listed, do not emit an entity fact for it.",
            "- evidenceText must be copied from the AI answer section, not from this context.",
            "",
            "Query context:",
            f"- projectId: {command.project_id}",
            f"- queryId: {command.query_id}",
            f"- queryText: {command.query_text}",
            f"- provider: {command.provider}",
            f"- surface: {command.surface}",
            f"- model: {command.model}",
            f"- region: {command.region}",
            f"- language: {command.language}",
            "",
            "Topic context:",
            topic_text,
            "",
            "Entity context:",
            *entity_lines,
            "",
            "AI answer:",
            "--- BEGIN AI ANSWER ---",
            command.raw_response,
            "--- END AI ANSWER ---",
        ]
    )


def _semantic_repair_extraction_text(
    extraction_text: str,
    error: KMindHubExtractionValidationError | None,
) -> str:
    error_summary = _repair_error_summary(error)
    return "\n".join(
        [
            extraction_text,
            "",
            "Repair instructions:",
            (
                "- Previous preview failed validation: "
                f"{error_summary}."
            ),
            "- Regenerate the extraction items by following the field rules exactly.",
            "- entityId must be copied exactly as a UUID from Entity context.",
            "- evidenceText must be an exact contiguous substring from the AI answer section.",
            "- When copying evidenceText, preserve Markdown delimiters such as **, *, _, and backticks exactly.",
            "- Replace invalid evidenceText with a copied raw answer substring, or leave evidenceText empty.",
            "- Leave evidenceText empty when no exact supporting substring exists.",
            "- Do not use neutral, mixed, unknown, or uncertain sentiment values.",
            "- Use only product, service, topic, or common_statement for factType.",
            "- Do not extract facts from these repair instructions.",
        ]
    )


def _repair_error_summary(error: KMindHubExtractionValidationError | None) -> str:
    if error is None:
        return "unknown validation error"
    message = str(error)
    if message.startswith("evidenceText must exist in raw response"):
        return "evidenceText was not an exact substring of the AI answer"
    return _safe_text(message) or "unknown validation error"


def _log_semantic_preview_debug_payloads(
    *,
    command: AnalyzeGeoRunResultCommand,
    workspace_id: UUID,
    task_id: UUID,
    attempt: int,
    extraction_text: str,
    preview: KMindHubExtractionPreviewResult,
    error: KMindHubExtractionValidationError,
) -> None:
    payload = {
        "runResultId": str(command.run_result_id),
        "workspaceId": str(workspace_id),
        "taskId": str(task_id),
        "attempt": attempt,
        "error": str(error),
        "kmindhubExtractionText": extraction_text,
        "kmindhubPreviewItems": [
            item.model_dump(mode="json", by_alias=True) for item in preview.items
        ],
    }
    logger.warning(
        "KMindHub semantic preview validation debug payloads: %s",
        _debug_payload(payload),
        extra={
            "run_result_id": str(command.run_result_id),
            "workspace_id": str(workspace_id),
            "task_id": str(task_id),
            "attempt": attempt,
            "error": str(error),
            "kmindhub_extraction_text": extraction_text,
            "kmindhub_preview_items": payload["kmindhubPreviewItems"],
        },
    )


def _entity_context_line(entity) -> str:
    website = entity.website_url or ""
    return (
        f"- entityId: {entity.entity_id}; entityRole: {entity.entity_role}; "
        f"entityName: {entity.name}; websiteUrl: {website}"
    )


def _safe_text(value: str | None, limit: int = 120) -> str | None:
    if value is None:
        return None
    normalized = re.sub(r"\s+", " ", str(value)).strip()
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[:limit]}..."


def _safe_dict(value: dict, limit: int = 120) -> dict:
    return {str(key): _safe_text(str(item), limit) for key, item in value.items()}


def _debug_payload(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=False, default=str)


@dataclass
class HttpKMindHubWorkspaceClient:
    """呼叫 KMindHub Insight workspace API 並產生 runtime workspace header。"""

    base_url: str
    timeout_seconds: float = 30.0
    preview_retry_attempts: int = 2
    preview_retry_delay_seconds: float = 0.5
    debug_payloads: bool = False
    _client: httpx.AsyncClient | None = field(default=None, init=False, repr=False)

    async def create_workspace(self, display_name: str) -> UUID:
        try:
            response = await self._get_client().post(
                "/workspaces",
                json={"displayName": display_name},
            )
            response.raise_for_status()
            payload = response.json()
            return UUID(str(payload["workspaceId"]))
        except (KeyError, ValueError, httpx.HTTPError) as exc:
            raise KMindHubWorkspaceProvisionUnavailable(
                "KMindHub workspace provision is unavailable"
            ) from exc

    def workspace_headers(self, workspace_id: UUID) -> dict[str, str]:
        return {"X-Workspace-Id": str(workspace_id)}

    async def create_extraction_task(
        self,
        *,
        workspace_id: UUID,
        definition: KMindHubExtractionTaskDefinition,
    ) -> UUID:
        try:
            response = await self._get_client().post(
                "/extraction-tasks",
                headers=self.workspace_headers(workspace_id),
                json={
                    "name": definition.name,
                    "task": definition.task,
                    "description": definition.description,
                    "status": definition.status,
                    "fields": [
                        field.model_dump(mode="json", by_alias=True)
                        for field in definition.fields
                    ],
                },
            )
            response.raise_for_status()
            payload = response.json()
            return UUID(str(payload.get("taskId") or payload.get("id")))
        except (KeyError, ValueError, httpx.HTTPError) as exc:
            raise KMindHubExtractionUnavailable(
                "KMindHub extraction task is unavailable"
            ) from exc

    async def preview_text_extraction(
        self,
        *,
        workspace_id: UUID,
        task_id: UUID,
        text: str,
    ) -> KMindHubExtractionPreviewResult:
        response: httpx.Response | None = None
        last_error: Exception | None = None
        max_attempts = max(1, self.preview_retry_attempts + 1)
        for attempt in range(max_attempts):
            try:
                request_data = {"taskId": str(task_id), "text": text}
                if self.debug_payloads:
                    log_payload = {
                        "workspaceId": str(workspace_id),
                        "taskId": str(task_id),
                        "attempt": attempt + 1,
                        "requestData": request_data,
                    }
                    logger.info(
                        "KMindHub extraction preview request payload: %s",
                        _debug_payload(log_payload),
                        extra={
                            "workspace_id": str(workspace_id),
                            "task_id": str(task_id),
                            "attempt": attempt + 1,
                            "kmindhub_request_data": request_data,
                        },
                    )
                response = await self._get_client().post(
                    "/extractions",
                    headers=self.workspace_headers(workspace_id),
                    data=request_data,
                )
                if self.debug_payloads:
                    log_payload = {
                        "workspaceId": str(workspace_id),
                        "taskId": str(task_id),
                        "attempt": attempt + 1,
                        "statusCode": response.status_code,
                        "responseBody": response.text,
                    }
                    logger.info(
                        "KMindHub extraction preview response payload: %s",
                        _debug_payload(log_payload),
                        extra={
                            "workspace_id": str(workspace_id),
                            "task_id": str(task_id),
                            "attempt": attempt + 1,
                            "status_code": response.status_code,
                            "kmindhub_response_body": response.text,
                        },
                    )
                response.raise_for_status()
                payload = response.json()
                return KMindHubExtractionPreviewResult(
                    task_id=UUID(str(payload.get("taskId", task_id))),
                    items=[
                        KMindHubExtractionPreviewItem(
                            fields={
                                name: KMindHubExtractionFieldValue(**value)
                                for name, value in item.get("fields", {}).items()
                            },
                            verification=item.get("verification", {}),
                            display_fields=item.get("displayFields", []),
                            candidates=item.get("candidates", []),
                        )
                        for item in payload.get("items", [])
                    ],
                )
            except (KeyError, ValueError, TypeError) as exc:
                last_error = exc
                break
            except httpx.HTTPError as exc:
                last_error = exc
                if isinstance(exc, httpx.HTTPStatusError):
                    response = exc.response
                if (
                    not _should_retry_preview(exc)
                    or attempt >= max_attempts - 1
                ):
                    break
                logger.warning(
                    "Retrying KMindHub extraction preview after transient failure",
                    extra={
                        "workspace_id": str(workspace_id),
                        "task_id": str(task_id),
                        "attempt": attempt + 1,
                        "max_attempts": max_attempts,
                        "status_code": (
                            response.status_code if response is not None else None
                        ),
                        "exception_type": exc.__class__.__name__,
                    },
                )
                await asyncio.sleep(self.preview_retry_delay_seconds * (2**attempt))

        failure_payload = {
            "workspaceId": str(workspace_id),
            "taskId": str(task_id),
            "statusCode": response.status_code if response is not None else None,
            "responseBody": _response_excerpt(response),
            "exceptionType": (
                last_error.__class__.__name__ if last_error is not None else None
            ),
        }
        logger.error(
            "KMindHub extraction preview failed: %s",
            _debug_payload(failure_payload),
            extra={
                "workspace_id": str(workspace_id),
                "task_id": str(task_id),
                "status_code": failure_payload["statusCode"],
                "response_body": failure_payload["responseBody"],
                "exception_type": failure_payload["exceptionType"],
            },
            exc_info=last_error,
        )
        raise KMindHubExtractionUnavailable(
            "KMindHub extraction preview is unavailable"
            + (
                f": {last_error.__class__.__name__}"
                if last_error is not None
                else ""
            )
        ) from last_error

    async def commit_extraction_items(
        self,
        *,
        workspace_id: UUID,
        task_id: UUID,
        items: list[dict],
    ) -> KMindHubExtractionCommitResult:
        response: httpx.Response | None = None
        try:
            logger.info(
                "Committing KMindHub extraction items",
                extra={
                    "workspace_id": str(workspace_id),
                    "task_id": str(task_id),
                    "item_count": len(items),
                    "item_field_names": _item_field_names(items),
                },
            )
            response = await self._get_client().post(
                "/extractions/commit",
                headers=self.workspace_headers(workspace_id),
                json={"taskId": str(task_id), "items": items},
            )
            response.raise_for_status()
            payload = response.json()
            logger.info(
                "Committed KMindHub extraction items",
                extra={
                    "workspace_id": str(workspace_id),
                    "task_id": str(task_id),
                    "status_code": response.status_code,
                    "payload_keys": sorted(payload) if isinstance(payload, dict) else [],
                    "has_commit_batch_id": (
                        isinstance(payload, dict)
                        and payload.get("commitBatchId") is not None
                    ),
                    "items_count": (
                        len(payload.get("items", [])) if isinstance(payload, dict) else 0
                    ),
                },
            )
            item_ids = (
                payload.get("itemIds")
                or payload.get("committedItemIds")
                or payload.get("items")
                or []
            )
            return KMindHubExtractionCommitResult(
                commit_batch_id=(
                    str(payload["commitBatchId"])
                    if payload.get("commitBatchId") is not None
                    else None
                ),
                item_ids=_commit_item_ids(item_ids),
            )
        except (KeyError, TypeError, ValueError, httpx.HTTPError) as exc:
            logger.exception(
                "KMindHub extraction commit failed",
                extra={
                    "workspace_id": str(workspace_id),
                    "task_id": str(task_id),
                    "item_count": len(items),
                    "status_code": response.status_code if response is not None else None,
                    "response_body": _response_excerpt(response),
                    "exception_type": exc.__class__.__name__,
                },
            )
            raise KMindHubExtractionUnavailable(
                f"KMindHub extraction commit is unavailable: {exc.__class__.__name__}"
            ) from exc

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url.rstrip("/"),
                timeout=self.timeout_seconds,
            )
        return self._client


def _commit_item_ids(items: list) -> list[str]:
    ids: list[str] = []
    for item in items:
        if isinstance(item, dict):
            value = item.get("itemId") or item.get("id")
            if value is not None:
                ids.append(str(value))
        elif item is not None:
            ids.append(str(item))
    return ids


def _item_field_names(items: list[dict]) -> list[list[str]]:
    names: list[list[str]] = []
    for item in items:
        fields = item.get("fields") if isinstance(item, dict) else None
        names.append(sorted(fields) if isinstance(fields, dict) else [])
    return names


def _should_retry_preview(exc: httpx.HTTPError) -> bool:
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in KMINDHUB_PREVIEW_RETRY_STATUS_CODES
    return isinstance(exc, (httpx.TimeoutException, httpx.NetworkError))


def _response_excerpt(response: httpx.Response | None, limit: int = 500) -> str | None:
    if response is None:
        return None
    try:
        text = response.text
    except Exception:
        return None
    return _safe_text(text, limit)
