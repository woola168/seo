from dataclasses import replace
from datetime import datetime
from uuid import UUID

from younilab_access_control_application import (
    PasswordReset,
    RefreshSession,
    UserInvitation,
)
from younilab_access_control_domain import Department, Role, UserAccount


class MemoryAccessControlRepository:
    def __init__(
        self,
        *,
        users: list[UserAccount] | None = None,
        roles: list[Role] | None = None,
        password_hashes: dict[UUID, str] | None = None,
        departments: list[Department] | None = None,
    ) -> None:
        self.users = {user.id: user for user in users or []}
        self.roles = {role.id: role for role in roles or []}
        self.password_hashes = password_hashes or {}
        self.sessions: dict[UUID, RefreshSession] = {}
        self.password_resets: dict[UUID, PasswordReset] = {}
        self.invitations: dict[UUID, UserInvitation] = {}
        self.departments = {
            department.id: department for department in departments or []
        }

    async def list_users(self) -> list[UserAccount]:
        return [user for user in self.users.values() if not user.is_deleted]

    async def save_user(self, user: UserAccount) -> None:
        self.users[user.id] = user

    async def update_password_hash(self, user_id: UUID, password_hash: str) -> None:
        self.password_hashes[user_id] = password_hash

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

    async def delete_role(self, role_id: UUID) -> None:
        self.roles.pop(role_id, None)

    async def role_member_count(self, role_id: UUID) -> int:
        return sum(
            role_id in user.role_ids and not user.is_deleted
            for user in self.users.values()
        )

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

    async def get_refresh_session_by_id(
        self,
        session_id: UUID,
    ) -> RefreshSession | None:
        return self.sessions.get(session_id)

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

    async def save_password_reset(self, reset: PasswordReset) -> None:
        self.password_resets[reset.id] = reset

    async def get_password_reset(self, token_digest: str) -> PasswordReset | None:
        return next(
            (
                reset
                for reset in self.password_resets.values()
                if reset.token_digest == token_digest
            ),
            None,
        )

    async def consume_password_reset(
        self,
        reset_id: UUID,
        used_at: datetime,
    ) -> None:
        self.password_resets[reset_id] = replace(
            self.password_resets[reset_id],
            used_at=used_at,
        )

    async def revoke_password_resets(
        self,
        user_id: UUID,
        revoked_at: datetime,
    ) -> None:
        for reset_id, reset in tuple(self.password_resets.items()):
            if (
                reset.user_id == user_id
                and reset.used_at is None
                and reset.revoked_at is None
            ):
                self.password_resets[reset_id] = replace(
                    reset,
                    revoked_at=revoked_at,
                )

    async def save_invitation(self, invitation: UserInvitation) -> None:
        self.invitations[invitation.id] = invitation

    async def create_invited_user(
        self,
        *,
        user: UserAccount,
        invitation: UserInvitation,
        role_ids: set[UUID],
        customer_ids: set[UUID],
        task_ids: set[UUID],
    ) -> None:
        user.role_ids = set(role_ids)
        user.customer_ids = set(customer_ids)
        user.task_ids = set(task_ids)
        self.users[user.id] = user
        self.invitations[invitation.id] = invitation

    async def get_invitation(
        self,
        invitation_id: UUID,
    ) -> UserInvitation | None:
        return self.invitations.get(invitation_id)

    async def get_invitation_by_token(
        self,
        token_digest: str,
    ) -> UserInvitation | None:
        return next(
            (
                invitation
                for invitation in self.invitations.values()
                if invitation.token_digest == token_digest
            ),
            None,
        )

    async def accept_invitation(
        self,
        invitation_id: UUID,
        accepted_at: datetime,
    ) -> None:
        self.invitations[invitation_id] = replace(
            self.invitations[invitation_id],
            accepted_at=accepted_at,
        )

    async def revoke_invitation(
        self,
        invitation_id: UUID,
        revoked_at: datetime,
    ) -> None:
        self.invitations[invitation_id] = replace(
            self.invitations[invitation_id],
            revoked_at=revoked_at,
        )

    async def list_departments(self) -> list[Department]:
        return [
            department
            for department in self.departments.values()
            if department.is_active
        ]

    async def get_department(self, department_id: UUID) -> Department | None:
        return self.departments.get(department_id)

    async def save_department(self, department: Department) -> None:
        self.departments[department.id] = department

    async def department_member_count(self, department_id: UUID) -> int:
        return sum(
            user.department_id == department_id and not user.is_deleted
            for user in self.users.values()
        )
