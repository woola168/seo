from dataclasses import dataclass, field
from enum import StrEnum
from uuid import UUID


class AccountStatus(StrEnum):
    INVITED = "invited"
    ACTIVE = "active"
    DISABLED = "disabled"


class ResourceType(StrEnum):
    CUSTOMER = "customer"
    TASK = "task"


@dataclass(frozen=True)
class Role:
    id: UUID
    name: str
    permissions: frozenset[str] = field(default_factory=frozenset)
    is_system: bool = False
    has_global_resource_access: bool = False

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("role name must not be empty")
        if any(not permission.strip() for permission in self.permissions):
            raise ValueError("permission must not be empty")


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


@dataclass(frozen=True)
class Customer:
    id: UUID
    name: str

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("customer name must not be empty")


@dataclass(frozen=True)
class SeoTask:
    id: UUID
    customer_id: UUID
    name: str

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("task name must not be empty")


@dataclass(frozen=True)
class ProtectedResource:
    type: ResourceType
    id: UUID
    customer_id: UUID | None = None

    def __post_init__(self) -> None:
        if self.type is ResourceType.TASK and self.customer_id is None:
            raise ValueError("task resource customer id is required")
