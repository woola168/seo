from dataclasses import dataclass, field
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


@dataclass(frozen=True)
class KMindHubGeoRunResultAnalyzer:
    """透過 KMindHub extraction API 產生 GEO semantic facts。"""

    repository: GeoAnalysisRepository
    workspace_resolver: KMindHubWorkspaceResolver
    client: KMindHubWorkspaceClient

    async def analyze(
        self,
        command: AnalyzeGeoRunResultCommand,
    ) -> GeoRunResultAnalysis:
        workspace_id = await self.workspace_resolver.resolve_workspace_id(
            command.tenant_id
        )
        task_id = await self._ensure_task(command.tenant_id, workspace_id)
        preview = await self.client.preview_text_extraction(
            workspace_id=workspace_id,
            task_id=task_id,
            text=command.raw_response,
        )
        facts = _facts_from_preview(command, preview.items)
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
) -> GeoRunResultAnalysis:
    entity_mentions: list[GeoEntityMentionFact] = []
    sentiments: list[GeoSentimentFact] = []
    semantic_facts: list[GeoResponseSemanticFact] = []

    for item in items:
        verification = item.verification or {}
        if verification and verification.get("passed") is False:
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
            raise KMindHubExtractionValidationError(
                "KMindHub preview validation failed"
            ) from exc

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
        confidence=_float_value(fields, "confidence"),
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
        confidence=_float_value(fields, "confidence"),
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
        confidence=_float_value(fields, "confidence"),
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
        raise KMindHubExtractionValidationError(f"{name} must be a UUID") from exc


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


def _float_value(
    fields: dict[str, KMindHubExtractionFieldValue],
    name: str,
) -> float | None:
    value = _string_value(fields, name)
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise KMindHubExtractionValidationError(f"{name} must be a number") from exc


def _validated_evidence(
    fields: dict[str, KMindHubExtractionFieldValue],
    raw_response: str,
) -> str | None:
    evidence = _string_value(fields, "evidenceText")
    if evidence is None:
        return None
    if _normalize_evidence(evidence) not in _normalize_evidence(raw_response):
        raise KMindHubExtractionValidationError(
            "evidenceText must exist in raw response"
        )
    return evidence


def _normalize_evidence(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value)
    return re.sub(r"\s+", " ", normalized).strip()


@dataclass
class HttpKMindHubWorkspaceClient:
    """呼叫 KMindHub Insight workspace API 並產生 runtime workspace header。"""

    base_url: str
    timeout_seconds: float = 30.0
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
        try:
            response = await self._get_client().post(
                "/extractions",
                headers=self.workspace_headers(workspace_id),
                data={"taskId": str(task_id), "text": text},
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
        except (KeyError, ValueError, TypeError, httpx.HTTPError) as exc:
            raise KMindHubExtractionUnavailable(
                "KMindHub extraction preview is unavailable"
            ) from exc

    async def commit_extraction_items(
        self,
        *,
        workspace_id: UUID,
        task_id: UUID,
        items: list[dict],
    ) -> KMindHubExtractionCommitResult:
        try:
            response = await self._get_client().post(
                "/extractions/commit",
                headers=self.workspace_headers(workspace_id),
                json={"taskId": str(task_id), "items": items},
            )
            response.raise_for_status()
            payload = response.json()
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
        except (KeyError, TypeError, httpx.HTTPError) as exc:
            raise KMindHubExtractionUnavailable(
                "KMindHub extraction commit is unavailable"
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
