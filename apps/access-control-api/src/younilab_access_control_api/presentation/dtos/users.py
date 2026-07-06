from datetime import datetime
from typing import Self
from uuid import UUID

from younilab_access_control_api.presentation.dtos.base import ApiModel, ApiRequest
from younilab_seo.access_control.application import UserInvitation
from younilab_seo.access_control.domain import AccountStatus, UserAccount


class UserResponse(ApiModel):
    """user endpoints 回傳的帳號基本資料與 role assignment。"""

    id: UUID
    tenant_id: UUID
    tenant_name: str | None
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
            tenant_id=user.tenant_id,
            tenant_name=user.tenant_name,
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
    """access administration 使用的使用者資料與 resource grants。"""

    customer_ids: list[UUID]
    task_ids: list[UUID]

    @classmethod
    def from_domain(cls, user: UserAccount) -> Self:
        return cls(
            id=user.id,
            tenant_id=user.tenant_id,
            tenant_name=user.tenant_name,
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
    """單一使用者的完整替換 role assignment。"""

    role_ids: set[UUID]


class UpdateUserRequest(ApiRequest):
    """既有使用者可編輯的基本資料欄位。"""

    display_name: str
    department_id: UUID | None = None


class UpdateUserStatusRequest(ApiRequest):
    """帳號要切換到的 lifecycle status。"""

    status: AccountStatus


class CreateInvitationRequest(ApiRequest):
    """帳號邀請資訊、初始 access 與寄送偏好。"""

    email: str
    display_name: str
    department_id: UUID | None = None
    role_ids: set[UUID]
    customer_ids: set[UUID] = set()
    task_ids: set[UUID] = set()
    send_invitation: bool = True


class UserInvitationResponse(ApiModel):
    """回傳給管理員的已建立 invitation 中繼資料。"""

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
