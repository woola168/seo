from datetime import datetime
from typing import Protocol, runtime_checkable
from uuid import UUID

from younilab_access_control_application.models import RefreshSession
from younilab_access_control_domain import Role, UserAccount


class _UserReader(Protocol):
    async def get_user(self, user_id: UUID) -> UserAccount | None: ...


class _CredentialRepository(Protocol):
    async def get_user_by_email(self, email: str) -> UserAccount | None: ...

    async def get_password_hash(self, user_id: UUID) -> str | None: ...


class _RoleReader(Protocol):
    async def get_roles(self, role_ids: set[UUID]) -> list[Role]: ...


@runtime_checkable
class UserRepository(_UserReader, Protocol):
    async def list_users(self) -> list[UserAccount]: ...


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
class AuthenticationRepository(
    _UserReader,
    _CredentialRepository,
    RefreshSessionRepository,
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
