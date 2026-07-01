from dataclasses import dataclass
from uuid import UUID

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from younilab_seo.access_control.application import InvalidSession
from younilab_access_control_api.presentation.request_parsing import (
    access_token_from_credentials,
)
from younilab_seo.access_control.contracts import AuthorizationRequest
from younilab_seo.access_control.domain import UserAccount


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
    session = await request.app.state.repository.get_refresh_session_by_id(
        claims.session_id
    )
    if session is None or not session.is_valid(request.app.state.clock.now()):
        raise InvalidSession
    user = await request.app.state.repository.get_user(claims.user_id)
    if user is None or not user.is_active:
        raise InvalidSession
    tenant = await request.app.state.repository.get_tenant(user.tenant_id)
    if tenant is None or not tenant.is_active:
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
        from younilab_seo.access_control.application import AccountUnavailable

        raise AccountUnavailable
