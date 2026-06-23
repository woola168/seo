from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID


class ResourceType(StrEnum):
    CUSTOMER = "customer"
    TASK = "task"


@dataclass(frozen=True)
class Customer:
    """可作為 authorization decision scope 的 customer resource。"""

    id: UUID
    name: str

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("customer name must not be empty")


@dataclass(frozen=True)
class SeoTask:
    """歸屬於 customer scope 的 SEO task resource。"""

    id: UUID
    customer_id: UUID
    name: str

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("task name must not be empty")


@dataclass(frozen=True)
class ProtectedResource:
    """評估 scoped permissions 所需的 resource context。"""

    type: ResourceType
    id: UUID
    customer_id: UUID | None = None

    def __post_init__(self) -> None:
        if self.type is ResourceType.TASK and self.customer_id is None:
            raise ValueError("task resource customer id is required")
