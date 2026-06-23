import httpx

from younilab_seo.resource_catalog.application import AccessDenied


class AccessControlAuthorizer:
    """將 decisions 委派給 Access Control 的 PermissionAuthorizer adapter。"""

    def __init__(
        self,
        access_control_url: str,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._access_control_url = access_control_url.rstrip("/")
        self._transport = transport

    async def require(self, access_token: str, permission: str) -> None:
        try:
            async with httpx.AsyncClient(
                timeout=5,
                transport=self._transport,
            ) as client:
                headers = {"Authorization": f"Bearer {access_token}"}
                response = await client.get(
                    f"{self._access_control_url}/api/me/capabilities",
                    headers=headers,
                )
        except httpx.HTTPError as exc:
            raise AccessDenied("authorization service unavailable") from exc
        if response.status_code != 200:
            raise AccessDenied
        if permission not in response.json().get("permissions", []):
            raise AccessDenied


class AllowAllAuthorizer:
    """local development 使用且不執行 enforcement 的 PermissionAuthorizer adapter。"""

    async def require(self, access_token: str, permission: str) -> None:
        return None
