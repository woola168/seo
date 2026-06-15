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
    async def list_users(self) -> list[UserAccount]: ...

    async def save_user(self, user: UserAccount) -> None: ...

    async def update_password_hash(self, user_id: UUID, password_hash: str) -> None: ...


@runtime_checkable
class RoleRepository(_RoleReader, Protocol):
    async def list_roles(self) -> list[Role]: ...

    async def save_role(self, role: Role) -> None: ...


@runtime_checkable
class AccessGrantRepository(Protocol):
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
    ) -> None: ...

    async def revoke_refresh_session(
        self,
        session_id: UUID,
        revoked_at: datetime,
    ) -> None: ...

    async def revoke_session_family(
        self,
        family_id: UUID,
        revoked_at: datetime,
    ) -> None: ...

    async def revoke_user_sessions(
        self,
        user_id: UUID,
        revoked_at: datetime,
    ) -> None: ...


@runtime_checkable
class PasswordResetRepository(Protocol):
    async def save_password_reset(self, reset: PasswordReset) -> None: ...

    async def get_password_reset(self, token_digest: str) -> PasswordReset | None: ...

    async def consume_password_reset(
        self,
        reset_id: UUID,
        used_at: datetime,
    ) -> None: ...

    async def revoke_password_resets(
        self,
        user_id: UUID,
        revoked_at: datetime,
    ) -> None: ...


@runtime_checkable
class InvitationRepository(Protocol):
    async def create_invited_user(
        self,
        *,
        user: UserAccount,
        invitation: UserInvitation,
        role_ids: set[UUID],
        customer_ids: set[UUID],
        task_ids: set[UUID],
    ) -> None: ...

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
    ) -> None: ...

    async def revoke_invitation(
        self,
        invitation_id: UUID,
        revoked_at: datetime,
    ) -> None: ...


@runtime_checkable
class DepartmentRepository(Protocol):
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
    pass


@runtime_checkable
class AuthorizationRepository(_UserReader, _RoleReader, Protocol):
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
    pass


@runtime_checkable
class AccessControlRepository(
    AuthenticationRepository,
    AccessManagementRepository,
    Protocol,
):
    pass
