from dataclasses import dataclass, field
from uuid import UUID

import httpx

from younilab_seo.geo_analysis.application import (
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
