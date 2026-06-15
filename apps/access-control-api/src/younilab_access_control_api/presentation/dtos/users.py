from datetime import datetime
from typing import Self
from uuid import UUID

from younilab_access_control_api.presentation.dtos.base import ApiModel, ApiRequest
from younilab_access_control_application import UserInvitation
from younilab_access_control_domain import AccountStatus, UserAccount


class UserResponse(ApiModel):
    id: UUID
    email: str
    display_name: str
    status: str
    role_ids: list[UUID]
    department_id: UUID | None
    auth_provider: str
    last_login_at: datetime | None
    invited_at: datetime | None
    created_at: datetime | None
    updated_at: datetime | None

    @classmethod
    def from_domain(cls, user: UserAccount) -> Self:
        return cls(
            id=user.id,
            email=user.email,
            display_name=user.display_name,
            status=user.status.value,
            role_ids=sorted(user.role_ids, key=str),
            department_id=user.department_id,
            auth_provider=user.auth_provider,
            last_login_at=user.last_login_at,
            invited_at=user.invited_at,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )


class UserAccessResponse(UserResponse):
    customer_ids: list[UUID]
    task_ids: list[UUID]

    @classmethod
    def from_domain(cls, user: UserAccount) -> Self:
        return cls(
            id=user.id,
            email=user.email,
            display_name=user.display_name,
            status=user.status.value,
            role_ids=sorted(user.role_ids, key=str),
            department_id=user.department_id,
            auth_provider=user.auth_provider,
            last_login_at=user.last_login_at,
            invited_at=user.invited_at,
            created_at=user.created_at,
            updated_at=user.updated_at,
            customer_ids=sorted(user.customer_ids, key=str),
            task_ids=sorted(user.task_ids, key=str),
        )


class ReplaceRolesRequest(ApiRequest):
    role_ids: set[UUID]


class UpdateUserRequest(ApiRequest):
    display_name: str
    department_id: UUID | None = None


class UpdateUserStatusRequest(ApiRequest):
    status: AccountStatus


class CreateInvitationRequest(ApiRequest):
    email: str
    display_name: str
    department_id: UUID | None = None
    role_ids: set[UUID]
    customer_ids: set[UUID] = set()
    task_ids: set[UUID] = set()
    send_invitation: bool = True


class UserInvitationResponse(ApiModel):
    id: UUID
    user_id: UUID
    email: str
    expires_at: datetime
    created_at: datetime

    @classmethod
    def from_application(cls, invitation: UserInvitation):
        return cls(
            id=invitation.id,
            user_id=invitation.user_id,
            email=invitation.email,
            expires_at=invitation.expires_at,
            created_at=invitation.created_at,
        )
