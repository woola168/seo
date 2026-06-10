from dataclasses import replace
from datetime import datetime
from uuid import UUID

from younilab_access_control_application import RefreshSession
from younilab_access_control_domain import Role, UserAccount


class MemoryAccessControlRepository:
    def __init__(
        self,
        *,
        users: list[UserAccount] | None = None,
        roles: list[Role] | None = None,
        password_hashes: dict[UUID, str] | None = None,
    ) -> None:
        self.users = {user.id: user for user in users or []}
        self.roles = {role.id: role for role in roles or []}
        self.password_hashes = password_hashes or {}
        self.sessions: dict[UUID, RefreshSession] = {}

    async def list_users(self) -> list[UserAccount]:
        return list(self.users.values())

    async def get_user(self, user_id: UUID) -> UserAccount | None:
        return self.users.get(user_id)

    async def get_user_by_email(self, email: str) -> UserAccount | None:
        normalized = email.strip().lower()
        return next(
            (user for user in self.users.values() if user.email == normalized),
            None,
        )

    async def get_password_hash(self, user_id: UUID) -> str | None:
        return self.password_hashes.get(user_id)

    async def get_roles(self, role_ids: set[UUID]) -> list[Role]:
        return [self.roles[role_id] for role_id in role_ids if role_id in self.roles]

    async def list_roles(self) -> list[Role]:
        return list(self.roles.values())

    async def save_role(self, role: Role) -> None:
        self.roles[role.id] = role

    async def replace_user_roles(
        self,
        user_id: UUID,
        role_ids: set[UUID],
    ) -> None:
        self.users[user_id].role_ids = set(role_ids)

    async def replace_customer_grants(
        self,
        user_id: UUID,
        customer_ids: set[UUID],
    ) -> None:
        self.users[user_id].customer_ids = set(customer_ids)

    async def replace_task_grants(
        self,
        user_id: UUID,
        task_ids: set[UUID],
    ) -> None:
        self.users[user_id].task_ids = set(task_ids)

    async def save_refresh_session(self, session: RefreshSession) -> None:
        self.sessions[session.id] = session

    async def get_refresh_session(
        self,
        token_digest: str,
    ) -> RefreshSession | None:
        return next(
            (
                session
                for session in self.sessions.values()
                if session.token_digest == token_digest
            ),
            None,
        )

    async def replace_refresh_session(
        self,
        *,
        current_session_id: UUID,
        replacement: RefreshSession,
        revoked_at: datetime,
    ) -> None:
        current = self.sessions[current_session_id]
        self.sessions[current_session_id] = replace(
            current,
            revoked_at=revoked_at,
            replaced_by_id=replacement.id,
        )
        self.sessions[replacement.id] = replacement

    async def revoke_refresh_session(
        self,
        session_id: UUID,
        revoked_at: datetime,
    ) -> None:
        session = self.sessions.get(session_id)
        if session is not None and session.revoked_at is None:
            self.sessions[session_id] = replace(session, revoked_at=revoked_at)

    async def revoke_session_family(
        self,
        family_id: UUID,
        revoked_at: datetime,
    ) -> None:
        for session_id, session in tuple(self.sessions.items()):
            if session.family_id == family_id and session.revoked_at is None:
                self.sessions[session_id] = replace(session, revoked_at=revoked_at)

    async def revoke_user_sessions(
        self,
        user_id: UUID,
        revoked_at: datetime,
    ) -> None:
        for session_id, session in tuple(self.sessions.items()):
            if session.user_id == user_id and session.revoked_at is None:
                self.sessions[session_id] = replace(session, revoked_at=revoked_at)
