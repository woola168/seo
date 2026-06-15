from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class AccountStatus(StrEnum):
    INVITED = "invited"
    ACTIVE = "active"
    DISABLED = "disabled"


@dataclass
class UserAccount:
    id: UUID
    email: str
    display_name: str
    status: AccountStatus
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
        normalized_name = display_name.strip()
        if not normalized_name:
            raise ValueError("display name must not be empty")
        self.display_name = normalized_name
        self.department_id = department_id
        self.updated_at = updated_at

    def change_status(self, status: AccountStatus, updated_at: datetime) -> None:
        if self.is_deleted:
            raise ValueError("deleted account cannot change status")
        self.status = status
        self.updated_at = updated_at

    def delete(self, deleted_at: datetime) -> None:
        self.status = AccountStatus.DISABLED
        self.deleted_at = deleted_at
        self.updated_at = deleted_at
