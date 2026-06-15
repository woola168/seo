from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class AccessClaims:
    user_id: UUID
    session_id: UUID
    expires_at: datetime


@dataclass(frozen=True)
class RefreshSession:
    id: UUID
    user_id: UUID
    token_digest: str
    family_id: UUID
    expires_at: datetime
    revoked_at: datetime | None = None
    replaced_by_id: UUID | None = None

    def is_valid(self, now: datetime) -> bool:
        return self.revoked_at is None and self.expires_at > now


@dataclass(frozen=True)
class IssuedTokens:
    access_token: str
    access_token_expires_at: datetime
    refresh_token: str
    refresh_token_expires_at: datetime


@dataclass(frozen=True)
class Capabilities:
    permissions: frozenset[str]
    has_global_resource_access: bool
    customer_ids: frozenset[UUID]
    task_ids: frozenset[UUID]


@dataclass(frozen=True)
class PasswordReset:
    id: UUID
    user_id: UUID
    token_digest: str
    expires_at: datetime
    created_at: datetime
    used_at: datetime | None = None
    revoked_at: datetime | None = None

    def is_valid(self, now: datetime) -> bool:
        return (
            self.used_at is None
            and self.revoked_at is None
            and self.expires_at > now
        )


@dataclass(frozen=True)
class UserInvitation:
    id: UUID
    user_id: UUID
    email: str
    token_digest: str
    expires_at: datetime
    created_at: datetime
    created_by: UUID
    accepted_at: datetime | None = None
    revoked_at: datetime | None = None

    def is_valid(self, now: datetime) -> bool:
        return (
            self.accepted_at is None
            and self.revoked_at is None
            and self.expires_at > now
        )


@dataclass(frozen=True)
class Notification:
    id: UUID
    recipient: str
    template: str
    parameters: dict[str, str]
    created_at: datetime
