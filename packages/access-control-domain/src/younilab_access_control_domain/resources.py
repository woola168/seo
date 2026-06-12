from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID


class ResourceType(StrEnum):
    CUSTOMER = "customer"
    TASK = "task"


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
