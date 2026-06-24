from typing import Annotated

from fastapi import Header

from younilab_seo.resource_catalog.application import AccessDenied


async def bearer_token(
    authorization: Annotated[str | None, Header()] = None,
) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise AccessDenied
    return authorization.removeprefix("Bearer ").strip()
