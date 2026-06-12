from dataclasses import dataclass, field
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

    def __post_init__(self) -> None:
        normalized_email = self.email.strip().lower()
        if not normalized_email or "@" not in normalized_email:
            raise ValueError("user email has invalid format")
        if not self.display_name.strip():
            raise ValueError("display name must not be empty")
        self.email = normalized_email

    @property
    def is_active(self) -> bool:
        return self.status is AccountStatus.ACTIVE
