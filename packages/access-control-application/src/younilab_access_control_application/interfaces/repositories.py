from datetime import datetime
from typing import Protocol, runtime_checkable
from uuid import UUID

from younilab_access_control_application.models import (
    PasswordReset,
    RefreshSession,
    UserInvitation,
)
from younilab_access_control_domain import Department, Role, UserAccount


class _UserReader(Protocol):
    async def get_user(self, user_id: UUID) -> UserAccount | None: ...


class _CredentialRepository(Protocol):
    async def get_user_by_email(self, email: str) -> UserAccount | None: ...

    async def get_password_hash(self, user_id: UUID) -> str | None: ...

    async def update_password_hash(self, user_id: UUID, password_hash: str) -> None: ...


class _RoleReader(Protocol):
    async def get_roles(self, role_ids: set[UUID]) -> list[Role]: ...


@runtime_checkable
class UserRepository(_UserReader, Protocol):
    """持久化帳號基本資料、狀態與 credential 相關使用者資料。"""

    async def list_users(self) -> list[UserAccount]: ...

    async def save_user(self, user: UserAccount) -> None: ...

    async def update_password_hash(self, user_id: UUID, password_hash: str) -> None: ...


@runtime_checkable
class RoleRepository(_RoleReader, Protocol):
    """持久化 roles 與 role membership 限制。"""

    async def list_roles(self) -> list[Role]: ...

    async def save_role(self, role: Role) -> None: ...

    async def delete_role(self, role_id: UUID) -> None: ...

    async def role_member_count(self, role_id: UUID) -> int: ...


@runtime_checkable
class AccessGrantRepository(Protocol):
    """以單一使用者為單位原子替換 role 與 resource grant assignment。"""

    async def replace_user_roles(
        self,
        user_id: UUID,
        role_ids: set[UUID],
    ) -> None: ...

    async def replace_customer_grants(
        self,
        user_id: UUID,
        customer_ids: set[UUID],
    ) -> None: ...

    async def replace_task_grants(
        self,
        user_id: UUID,
        task_ids: set[UUID],
    ) -> None: ...


@runtime_checkable
class RefreshSessionRepository(Protocol):
    """儲存 refresh-token sessions 及其 rotation 或撤銷狀態。"""

    async def save_refresh_session(self, session: RefreshSession) -> None: ...

    async def get_refresh_session(
        self,
        token_digest: str,
    ) -> RefreshSession | None: ...

    async def get_refresh_session_by_id(
        self,
        session_id: UUID,
    ) -> RefreshSession | None: ...

    async def replace_refresh_session(
        self,
        *,
        current_session_id: UUID,
        replacement: RefreshSession,
        revoked_at: datetime,
    ) -> None:
        """同時撤銷目前 session 並持久化 replacement。"""
        ...

    async def revoke_refresh_session(
        self,
        session_id: UUID,
        revoked_at: datetime,
    ) -> None: ...

    async def revoke_session_family(
        self,
        family_id: UUID,
        revoked_at: datetime,
    ) -> None:
        """撤銷同一次登入衍生出的所有 refresh sessions。"""
        ...

    async def revoke_user_sessions(
        self,
        user_id: UUID,
        revoked_at: datetime,
    ) -> None: ...


@runtime_checkable
class PasswordResetRepository(Protocol):
    """以 digest 儲存單次使用的 password reset tokens。"""

    async def save_password_reset(self, reset: PasswordReset) -> None: ...

    async def get_password_reset(self, token_digest: str) -> PasswordReset | None: ...

    async def consume_password_reset(
        self,
        reset_id: UUID,
        used_at: datetime,
    ) -> None:
        """密碼成功變更後，將 reset token 標記為已使用。"""
        ...

    async def revoke_password_resets(
        self,
        user_id: UUID,
        revoked_at: datetime,
    ) -> None: ...


@runtime_checkable
class InvitationRepository(Protocol):
    """持久化受邀使用者與啟用帳號使用的 tokens。"""

    async def create_invited_user(
        self,
        *,
        user: UserAccount,
        invitation: UserInvitation,
        role_ids: set[UUID],
        customer_ids: set[UUID],
        task_ids: set[UUID],
    ) -> None:
        """一併持久化受邀使用者、invitation、roles 與 grants。"""
        ...

    async def save_invitation(self, invitation: UserInvitation) -> None: ...

    async def get_invitation(self, invitation_id: UUID) -> UserInvitation | None: ...

    async def get_invitation_by_token(
        self,
        token_digest: str,
    ) -> UserInvitation | None: ...

    async def accept_invitation(
        self,
        invitation_id: UUID,
        accepted_at: datetime,
    ) -> None:
        """帳號啟用後，將 invitation 標記為已接受。"""
        ...

    async def revoke_invitation(
        self,
        invitation_id: UUID,
        revoked_at: datetime,
    ) -> None: ...


@runtime_checkable
class DepartmentRepository(Protocol):
    """持久化組織 departments 與成員數。"""

    async def list_departments(self) -> list[Department]: ...

    async def get_department(self, department_id: UUID) -> Department | None: ...

    async def save_department(self, department: Department) -> None: ...

    async def department_member_count(self, department_id: UUID) -> int: ...


@runtime_checkable
class AuthenticationRepository(
    _UserReader,
    _CredentialRepository,
    RefreshSessionRepository,
    PasswordResetRepository,
    InvitationRepository,
    Protocol,
):
    """authentication 與 recovery workflows 所需的 repository surface。"""

    pass


@runtime_checkable
class AuthorizationRepository(_UserReader, _RoleReader, Protocol):
    """authorization decisions 使用的唯讀 repository surface。"""

    pass


@runtime_checkable
class AccessManagementRepository(
    UserRepository,
    RoleRepository,
    AccessGrantRepository,
    RefreshSessionRepository,
    InvitationRepository,
    DepartmentRepository,
    Protocol,
):
    """account、role、grant 與 department management 使用的 repository surface。"""

    pass


@runtime_checkable
class AccessControlRepository(
    AuthenticationRepository,
    AccessManagementRepository,
    Protocol,
):
    """由 infrastructure 實作的完整 access-control persistence port。"""

    pass
