from fastapi import APIRouter, Depends, Request

from younilab_access_control_api.presentation.dependencies import (
    CurrentPrincipal,
    current_principal,
)
from younilab_access_control_api.presentation.dtos import (
    CapabilitiesResponse,
    UserResponse,
)


router = APIRouter(prefix="/api/v1/me", tags=["current-user"])


@router.get("", response_model=UserResponse)
async def get_me(
    principal: CurrentPrincipal = Depends(current_principal),
) -> UserResponse:
    user = principal.user
    return UserResponse(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        status=user.status.value,
        role_ids=sorted(user.role_ids, key=str),
    )


@router.get("/capabilities", response_model=CapabilitiesResponse)
async def get_capabilities(
    request: Request,
    principal: CurrentPrincipal = Depends(current_principal),
) -> CapabilitiesResponse:
    capabilities = await request.app.state.authorization.capabilities(
        principal.user.id
    )
    return CapabilitiesResponse(
        permissions=sorted(capabilities.permissions),
        has_global_resource_access=capabilities.has_global_resource_access,
        customer_ids=sorted(capabilities.customer_ids, key=str),
        task_ids=sorted(capabilities.task_ids, key=str),
    )
