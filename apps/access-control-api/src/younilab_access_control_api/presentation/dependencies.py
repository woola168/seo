from dataclasses import dataclass
from uuid import UUID

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from younilab_access_control_application import InvalidSession
from younilab_access_control_api.presentation.request_parsing import (
    access_token_from_credentials,
)
from younilab_authorization_contracts import AuthorizationRequest
from younilab_access_control_domain import UserAccount


bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class CurrentPrincipal:
    user: UserAccount
    session_id: UUID


async def current_principal(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> CurrentPrincipal:
    access_token = access_token_from_credentials(credentials)
    claims = request.app.state.token_provider.decode_access_token(
        access_token
    )
    user = await request.app.state.repository.get_user(claims.user_id)
    if user is None or not user.is_active:
        raise InvalidSession
    return CurrentPrincipal(user=user, session_id=claims.session_id)


async def require_permission(
    request: Request,
    principal: CurrentPrincipal,
    permission: str,
) -> None:
    decision = await request.app.state.authorization.evaluate(
        AuthorizationRequest(
            user_id=principal.user.id,
            permission=permission,
        )
    )
    if not decision.allowed:
        from younilab_access_control_application import AccountUnavailable

        raise AccountUnavailable
