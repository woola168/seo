from typing import Annotated

from fastapi import Header

from younilab_seo.resource_catalog.application import AuthenticationRequired


async def bearer_token(
    authorization: Annotated[str | None, Header()] = None,
) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise AuthenticationRequired
    return authorization.removeprefix("Bearer ").strip()
