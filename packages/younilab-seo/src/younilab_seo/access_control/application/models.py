from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class AccessClaims:
    """transport authentication 後驗證完成的 access-token claims。"""

    user_id: UUID
    session_id: UUID
    expires_at: datetime


@dataclass(frozen=True)
class RefreshSession:
    """已持久化、可輪替或撤銷的 refresh-token session。"""

    id: UUID
    user_id: UUID
    token_digest: str
    family_id: UUID
    expires_at: datetime
    revoked_at: datetime | None = None
    replaced_by_id: UUID | None = None

    def is_valid(self, now: datetime) -> bool:
        """回傳 refresh session 是否仍可交換新 token。"""
        return self.revoked_at is None and self.expires_at > now


@dataclass(frozen=True)
class IssuedTokens:
    """登入或 refresh rotation 後回傳的 access token 與 refresh token。"""

    access_token: str
    access_token_expires_at: datetime
    refresh_token: str
    refresh_token_expires_at: datetime


@dataclass(frozen=True)
class Capabilities:
    """使用者目前生效中的 permissions 與 resource grants。"""

    permissions: frozenset[str]
    has_global_resource_access: bool
    customer_ids: frozenset[UUID]
    task_ids: frozenset[UUID]


@dataclass(frozen=True)
class PasswordReset:
    """以 token digest 儲存的一次性密碼重設請求。"""

    id: UUID
    user_id: UUID
    token_digest: str
    expires_at: datetime
    created_at: datetime
    used_at: datetime | None = None
    revoked_at: datetime | None = None

    def is_valid(self, now: datetime) -> bool:
        """回傳 reset token 是否仍可用來變更密碼。"""
        return (
            self.used_at is None
            and self.revoked_at is None
            and self.expires_at > now
        )


@dataclass(frozen=True)
class UserInvitation:
    """連結使用者帳號與 acceptance token 的待處理邀請。"""

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
        """回傳 invitation token 是否仍可被接受。"""
        return (
            self.accepted_at is None
            and self.revoked_at is None
            and self.expires_at > now
        )


@dataclass(frozen=True)
class Notification:
    """application workflow 發出的通知請求。"""

    id: UUID
    recipient: str
    template: str
    parameters: dict[str, str]
    created_at: datetime
