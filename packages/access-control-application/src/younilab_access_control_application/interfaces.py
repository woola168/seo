from datetime import datetime
from typing import Protocol
from uuid import UUID

from younilab_access_control_application.models import (
    AccessClaims,
    RefreshSession,
)
from younilab_access_control_domain import Role, UserAccount


class AccessControlRepository(Protocol):
    async def list_users(self) -> list[UserAccount]: ...

    async def get_user(self, user_id: UUID) -> UserAccount | None: ...

    async def get_user_by_email(self, email: str) -> UserAccount | None: ...

    async def get_password_hash(self, user_id: UUID) -> str | None: ...

    async def get_roles(self, role_ids: set[UUID]) -> list[Role]: ...

    async def list_roles(self) -> list[Role]: ...

    async def save_role(self, role: Role) -> None: ...

    async def replace_user_roles(self, user_id: UUID, role_ids: set[UUID]) -> None: ...

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

    async def save_refresh_session(self, session: RefreshSession) -> None: ...

    async def get_refresh_session(self, token_digest: str) -> RefreshSession | None: ...

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


class PasswordHasher(Protocol):
    def hash(self, password: str) -> str: ...

    def verify(self, password: str, password_hash: str) -> bool: ...


class TokenProvider(Protocol):
    def issue_access_token(self, *, user_id: UUID, session_id: UUID) -> tuple[str, datetime]: ...

    def decode_access_token(self, token: str) -> AccessClaims: ...

    def new_refresh_token(self) -> str: ...

    def digest_refresh_token(self, token: str) -> str: ...

    def refresh_token_expires_at(self) -> datetime: ...


class Clock(Protocol):
    def now(self) -> datetime: ...


class IdGenerator(Protocol):
    def new_id(self) -> UUID: ...
