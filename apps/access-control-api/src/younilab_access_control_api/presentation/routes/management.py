from uuid import UUID

from fastapi import APIRouter, Depends, Request, status

from younilab_access_control_api.presentation.dependencies import (
    CurrentPrincipal,
    current_principal,
    require_permission,
)
from younilab_access_control_api.presentation.dtos import (
    CreateInvitationRequest,
    CreateRoleRequest,
    DepartmentResponse,
    ReplaceCustomerGrantsRequest,
    ReplacePermissionsRequest,
    ReplaceRolesRequest,
    ReplaceTaskGrantsRequest,
    RoleResponse,
    SaveDepartmentRequest,
    UpdateUserRequest,
    UpdateUserStatusRequest,
    UserAccessResponse,
    UserInvitationResponse,
)
from younilab_seo.access_control.domain import PERMISSIONS


router = APIRouter(prefix="/api", tags=["access-management"])


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


@router.delete("/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role(
    role_id: UUID,
    request: Request,
    principal: CurrentPrincipal = Depends(current_principal),
) -> None:
    await require_permission(request, principal, "roles.manage")
    await request.app.state.management.delete_role(role_id)


@router.get("/users", response_model=list[UserAccessResponse])
async def list_users(
    request: Request,
    principal: CurrentPrincipal = Depends(current_principal),
) -> list[UserAccessResponse]:
    await require_permission(request, principal, "users.read")
    await require_permission(request, principal, "access-grants.read")
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
    await require_permission(request, principal, "access-grants.read")
    return UserAccessResponse.from_domain(
        await request.app.state.management.get_user(user_id)
    )


@router.patch("/users/{user_id}", response_model=UserAccessResponse)
async def update_user(
    user_id: UUID,
    payload: UpdateUserRequest,
    request: Request,
    principal: CurrentPrincipal = Depends(current_principal),
) -> UserAccessResponse:
    await require_permission(request, principal, "users.manage")
    user = await request.app.state.management.update_user(
        user_id=user_id,
        display_name=payload.display_name,
        department_id=payload.department_id,
    )
    return UserAccessResponse.from_domain(user)


@router.patch("/users/{user_id}/status", response_model=UserAccessResponse)
async def update_user_status(
    user_id: UUID,
    payload: UpdateUserStatusRequest,
    request: Request,
    principal: CurrentPrincipal = Depends(current_principal),
) -> UserAccessResponse:
    await require_permission(request, principal, "users.manage")
    user = await request.app.state.management.change_user_status(
        actor_user_id=principal.user.id,
        user_id=user_id,
        status=payload.status,
    )
    return UserAccessResponse.from_domain(user)


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: UUID,
    request: Request,
    principal: CurrentPrincipal = Depends(current_principal),
) -> None:
    await require_permission(request, principal, "users.manage")
    await request.app.state.management.delete_user(
        actor_user_id=principal.user.id,
        user_id=user_id,
    )


@router.post(
    "/users/{user_id}/sessions/revoke",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def revoke_user_sessions(
    user_id: UUID,
    request: Request,
    principal: CurrentPrincipal = Depends(current_principal),
) -> None:
    await require_permission(request, principal, "users.manage")
    await request.app.state.management.revoke_user_sessions(user_id)


@router.post(
    "/users/{user_id}/password-reset",
    status_code=status.HTTP_202_ACCEPTED,
)
async def request_user_password_reset(
    user_id: UUID,
    request: Request,
    principal: CurrentPrincipal = Depends(current_principal),
) -> None:
    await require_permission(request, principal, "users.manage")
    user = await request.app.state.management.get_user(user_id)
    await request.app.state.account_recovery.request_reset(user.email)


@router.post(
    "/user-invitations",
    response_model=UserInvitationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_user_invitation(
    payload: CreateInvitationRequest,
    request: Request,
    principal: CurrentPrincipal = Depends(current_principal),
) -> UserInvitationResponse:
    await require_permission(request, principal, "users.manage")
    invitation = await request.app.state.invitations.invite(
        actor_user_id=principal.user.id,
        email=payload.email,
        display_name=payload.display_name,
        department_id=payload.department_id,
        role_ids=payload.role_ids,
        customer_ids=payload.customer_ids,
        task_ids=payload.task_ids,
        send_invitation=payload.send_invitation,
    )
    return UserInvitationResponse.from_application(invitation)


@router.post(
    "/user-invitations/{invitation_id}/resend",
    response_model=UserInvitationResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def resend_user_invitation(
    invitation_id: UUID,
    request: Request,
    principal: CurrentPrincipal = Depends(current_principal),
) -> UserInvitationResponse:
    await require_permission(request, principal, "users.manage")
    invitation = await request.app.state.invitations.resend(
        invitation_id=invitation_id,
        actor_user_id=principal.user.id,
    )
    return UserInvitationResponse.from_application(invitation)


@router.delete(
    "/user-invitations/{invitation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def cancel_user_invitation(
    invitation_id: UUID,
    request: Request,
    principal: CurrentPrincipal = Depends(current_principal),
) -> None:
    await require_permission(request, principal, "users.manage")
    await request.app.state.invitations.cancel(invitation_id)


@router.get("/departments", response_model=list[DepartmentResponse])
async def list_departments(
    request: Request,
    principal: CurrentPrincipal = Depends(current_principal),
) -> list[DepartmentResponse]:
    await require_permission(request, principal, "departments.read")
    departments = await request.app.state.management.list_departments()
    return [
        DepartmentResponse.from_domain(
            department,
            await request.app.state.repository.department_member_count(department.id),
        )
        for department in departments
    ]


@router.post(
    "/departments",
    response_model=DepartmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_department(
    payload: SaveDepartmentRequest,
    request: Request,
    principal: CurrentPrincipal = Depends(current_principal),
) -> DepartmentResponse:
    await require_permission(request, principal, "departments.manage")
    department = await request.app.state.management.create_department(
        department_id=request.app.state.id_generator.new_id(),
        name=payload.name,
        description=payload.description,
    )
    return DepartmentResponse.from_domain(department, 0)


@router.patch(
    "/departments/{department_id}",
    response_model=DepartmentResponse,
)
async def update_department(
    department_id: UUID,
    payload: SaveDepartmentRequest,
    request: Request,
    principal: CurrentPrincipal = Depends(current_principal),
) -> DepartmentResponse:
    await require_permission(request, principal, "departments.manage")
    department = await request.app.state.management.update_department(
        department_id=department_id,
        name=payload.name,
        description=payload.description,
    )
    count = await request.app.state.repository.department_member_count(department.id)
    return DepartmentResponse.from_domain(department, count)


@router.delete(
    "/departments/{department_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_department(
    department_id: UUID,
    request: Request,
    principal: CurrentPrincipal = Depends(current_principal),
) -> None:
    await require_permission(request, principal, "departments.manage")
    await request.app.state.management.archive_department(department_id)


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
