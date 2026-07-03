from dataclasses import dataclass, field
from uuid import UUID

import httpx

from younilab_seo.geo_analysis.application import (
    KMindHubExtractionCommitResult,
    KMindHubExtractionFieldValue,
    KMindHubExtractionPreviewItem,
    KMindHubExtractionPreviewResult,
    KMindHubExtractionTaskDefinition,
    KMindHubExtractionUnavailable,
    KMindHubWorkspaceProvisionUnavailable,
)


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
