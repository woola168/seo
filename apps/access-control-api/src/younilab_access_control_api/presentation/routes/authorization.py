from fastapi import APIRouter, Depends, Request

from younilab_access_control_api.presentation.dependencies import (
    CurrentPrincipal,
    current_principal,
)
from younilab_seo.access_control.contracts import (
    AuthorizationDecision,
    AuthorizationRequest,
    BatchAuthorizationDecision,
    BatchAuthorizationRequest,
)


router = APIRouter(prefix="/api/authorization", tags=["authorization"])


@router.post("/evaluate", response_model=AuthorizationDecision)
async def evaluate(
    payload: AuthorizationRequest,
    request: Request,
    principal: CurrentPrincipal = Depends(current_principal),
) -> AuthorizationDecision:
    await _ensure_can_evaluate(
        request=request,
        principal=principal,
        target_user_id=payload.user_id,
    )
    return await request.app.state.authorization.evaluate(payload)


@router.post("/batch-evaluate", response_model=BatchAuthorizationDecision)
async def batch_evaluate(
    payload: BatchAuthorizationRequest,
    request: Request,
    principal: CurrentPrincipal = Depends(current_principal),
) -> BatchAuthorizationDecision:
    for item in payload.requests:
        await _ensure_can_evaluate(
            request=request,
            principal=principal,
            target_user_id=item.user_id,
        )
    return await request.app.state.authorization.batch_evaluate(payload)


async def _ensure_can_evaluate(
    *,
    request: Request,
    principal: CurrentPrincipal,
    target_user_id,
) -> None:
    if target_user_id == principal.user.id:
        return
    capabilities = await request.app.state.authorization.capabilities(
        principal.user.id
    )
    if "authorization.evaluate" not in capabilities.permissions:
        from younilab_seo.access_control.application import AccountUnavailable

        raise AccountUnavailable
