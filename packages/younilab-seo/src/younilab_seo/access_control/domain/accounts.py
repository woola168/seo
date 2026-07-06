from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from younilab_seo.access_control.domain.tenants import (
    DEFAULT_TENANT_ID,
    DEFAULT_TENANT_NAME,
)


class AccountStatus(StrEnum):
    INVITED = "invited"
    ACTIVE = "active"
    DISABLED = "disabled"


@dataclass
class UserAccount:
    """授權判斷使用的帳號狀態、roles 與 resource grants。"""

    id: UUID
    email: str
    display_name: str
    status: AccountStatus
    tenant_id: UUID = DEFAULT_TENANT_ID
    tenant_name: str | None = DEFAULT_TENANT_NAME
    role_ids: set[UUID] = field(default_factory=set)
    customer_ids: set[UUID] = field(default_factory=set)
    task_ids: set[UUID] = field(default_factory=set)
    department_id: UUID | None = None
    auth_provider: str = "password"
    last_login_at: datetime | None = None
    invited_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    deleted_at: datetime | None = None

    def __post_init__(self) -> None:
        normalized_email = self.email.strip().lower()
        if not normalized_email or "@" not in normalized_email:
            raise ValueError("user email has invalid format")
        if not self.display_name.strip():
            raise ValueError("display name must not be empty")
        self.email = normalized_email

    @property
    def is_active(self) -> bool:
        return self.status is AccountStatus.ACTIVE and self.deleted_at is None

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    def update_profile(
        self,
        *,
        display_name: str,
        department_id: UUID | None,
        updated_at: datetime,
    ) -> None:
        """更新可編輯基本資料欄位，同時保留 account identity。"""
        normalized_name = display_name.strip()
        if not normalized_name:
            raise ValueError("display name must not be empty")
        self.display_name = normalized_name
        self.department_id = department_id
        self.updated_at = updated_at

    def change_status(self, status: AccountStatus, updated_at: datetime) -> None:
        """在帳號未被刪除時變更 account status。"""
        if self.is_deleted:
            raise ValueError("deleted account cannot change status")
        self.status = status
        self.updated_at = updated_at

    def delete(self, deleted_at: datetime) -> None:
        """軟刪除帳號，並使其無法再通過授權。"""
        self.status = AccountStatus.DISABLED
        self.deleted_at = deleted_at
        self.updated_at = deleted_at
