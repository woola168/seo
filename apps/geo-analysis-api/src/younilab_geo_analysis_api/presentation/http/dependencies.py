from typing import Annotated

from fastapi import Header


async def bearer_token(
    authorization: Annotated[str | None, Header()] = None,
) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise PermissionError("access denied")
    return authorization.removeprefix("Bearer ").strip()
