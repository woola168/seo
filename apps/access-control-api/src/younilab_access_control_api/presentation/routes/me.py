from fastapi import APIRouter, Depends, Request

from younilab_access_control_api.presentation.dependencies import (
    CurrentPrincipal,
    current_principal,
)
from younilab_access_control_api.presentation.dtos import (
    CapabilitiesResponse,
    UserResponse,
)


router = APIRouter(prefix="/api/me", tags=["current-user"])


@router.get("", response_model=UserResponse)
async def get_me(
    principal: CurrentPrincipal = Depends(current_principal),
) -> UserResponse:
    return UserResponse.from_domain(principal.user)


@router.get("/capabilities", response_model=CapabilitiesResponse)
async def get_capabilities(
    request: Request,
    principal: CurrentPrincipal = Depends(current_principal),
) -> CapabilitiesResponse:
    capabilities = await request.app.state.authorization.capabilities(
        principal.user.id
    )
    return CapabilitiesResponse.from_domain(capabilities)
