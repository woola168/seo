import httpx

from younilab_resource_catalog_application import AccessDenied


class AccessControlAuthorizer:
    """將 decisions 委派給 Access Control 的 PermissionAuthorizer adapter。"""

    def __init__(self, access_control_url: str) -> None:
        self._access_control_url = access_control_url.rstrip("/")

    async def require(self, access_token: str, permission: str) -> None:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                headers = {"Authorization": f"Bearer {access_token}"}
                me_response = await client.get(
                    f"{self._access_control_url}/api/v1/me",
                    headers=headers,
                )
                if me_response.status_code != 200:
                    raise AccessDenied
                response = await client.post(
                    f"{self._access_control_url}/api/v1/authorization/evaluate",
                    headers=headers,
                    json={
                        "userId": me_response.json()["id"],
                        "permission": permission,
                    },
                )
        except httpx.HTTPError as exc:
            raise AccessDenied("authorization service unavailable") from exc
        if response.status_code != 200 or not response.json().get("allowed", False):
            raise AccessDenied


class AllowAllAuthorizer:
    """local development 使用且不執行 enforcement 的 PermissionAuthorizer adapter。"""

    async def require(self, access_token: str, permission: str) -> None:
        return None
