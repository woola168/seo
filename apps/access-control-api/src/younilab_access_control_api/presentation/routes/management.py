from uuid import UUID

from fastapi import APIRouter, Depends, Request, status

from younilab_access_control_api.presentation.dependencies import (
    CurrentPrincipal,
    current_principal,
    require_permission,
)
from younilab_access_control_api.presentation.dtos import (
    CreateRoleRequest,
    ReplaceCustomerGrantsRequest,
    ReplacePermissionsRequest,
    ReplaceRolesRequest,
    ReplaceTaskGrantsRequest,
    RoleResponse,
    UserAccessResponse,
)
from younilab_access_control_domain import PERMISSIONS


router = APIRouter(prefix="/api/v1", tags=["access-management"])


@router.get("/permissions", response_model=list[str])
async def list_permissions(
    request: Request,
    principal: CurrentPrincipal = Depends(current_principal),
) -> list[str]:
    await require_permission(request, principal, "permissions.read")
    return sorted(PERMISSIONS)


@router.get("/roles", response_model=list[RoleResponse])
async def list_roles(
    request: Request,
    principal: CurrentPrincipal = Depends(current_principal),
) -> list[RoleResponse]:
    await require_permission(request, principal, "roles.read")
    return [
        RoleResponse.from_domain(role)
        for role in await request.app.state.management.list_roles()
    ]


@router.post("/roles", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
async def create_role(
    payload: CreateRoleRequest,
    request: Request,
    principal: CurrentPrincipal = Depends(current_principal),
) -> RoleResponse:
    await require_permission(request, principal, "roles.manage")
    role = await request.app.state.management.create_role(
        role_id=request.app.state.id_generator.new_id(),
        name=payload.name,
        permissions=payload.permissions,
    )
    return RoleResponse.from_domain(role)


@router.put("/roles/{role_id}/permissions", response_model=RoleResponse)
async def replace_role_permissions(
    role_id: UUID,
    payload: ReplacePermissionsRequest,
    request: Request,
    principal: CurrentPrincipal = Depends(current_principal),
) -> RoleResponse:
    await require_permission(request, principal, "roles.manage")
    role = await request.app.state.management.replace_role_permissions(
        role_id=role_id,
        permissions=payload.permissions,
    )
    return RoleResponse.from_domain(role)


@router.get("/users", response_model=list[UserAccessResponse])
async def list_users(
    request: Request,
    principal: CurrentPrincipal = Depends(current_principal),
) -> list[UserAccessResponse]:
    await require_permission(request, principal, "users.read")
    return [
        UserAccessResponse.from_domain(user)
        for user in await request.app.state.management.list_users()
    ]


@router.get("/users/{user_id}", response_model=UserAccessResponse)
async def get_user(
    user_id: UUID,
    request: Request,
    principal: CurrentPrincipal = Depends(current_principal),
) -> UserAccessResponse:
    await require_permission(request, principal, "users.read")
    return UserAccessResponse.from_domain(
        await request.app.state.management.get_user(user_id)
    )


@router.put("/users/{user_id}/roles", response_model=UserAccessResponse)
async def replace_user_roles(
    user_id: UUID,
    payload: ReplaceRolesRequest,
    request: Request,
    principal: CurrentPrincipal = Depends(current_principal),
) -> UserAccessResponse:
    await require_permission(request, principal, "users.manage")
    user = await request.app.state.management.replace_user_roles(
        user_id=user_id,
        role_ids=payload.role_ids,
    )
    return UserAccessResponse.from_domain(user)


@router.put(
    "/users/{user_id}/customer-access-grants",
    response_model=UserAccessResponse,
)
async def replace_customer_grants(
    user_id: UUID,
    payload: ReplaceCustomerGrantsRequest,
    request: Request,
    principal: CurrentPrincipal = Depends(current_principal),
) -> UserAccessResponse:
    await require_permission(request, principal, "access-grants.manage")
    user = await request.app.state.management.replace_customer_grants(
        user_id=user_id,
        customer_ids=payload.customer_ids,
    )
    return UserAccessResponse.from_domain(user)


@router.put(
    "/users/{user_id}/task-access-grants",
    response_model=UserAccessResponse,
)
async def replace_task_grants(
    user_id: UUID,
    payload: ReplaceTaskGrantsRequest,
    request: Request,
    principal: CurrentPrincipal = Depends(current_principal),
) -> UserAccessResponse:
    await require_permission(request, principal, "access-grants.manage")
    user = await request.app.state.management.replace_task_grants(
        user_id=user_id,
        task_ids=payload.task_ids,
    )
    return UserAccessResponse.from_domain(user)
