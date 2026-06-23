from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class ResourceStatus(StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"


@dataclass
class Customer:
    """封存而非刪除的 customer master-data resource。"""

    id: UUID
    name: str
    status: ResourceStatus
    created_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        self.name = self.name.strip()
        if not self.name:
            raise ValueError("customer name must not be empty")

    def update(self, *, name: str, updated_at: datetime) -> None:
        normalized = name.strip()
        if not normalized:
            raise ValueError("customer name must not be empty")
        self.name = normalized
        self.updated_at = updated_at

    def archive(self, archived_at: datetime) -> None:
        self.status = ResourceStatus.ARCHIVED
        self.updated_at = archived_at


@dataclass
class SeoTask:
    """歸屬於單一 customer 的 SEO task master-data resource。"""

    id: UUID
    customer_id: UUID
    name: str
    status: ResourceStatus
    created_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        self.name = self.name.strip()
        if not self.name:
            raise ValueError("task name must not be empty")

    def update(
        self,
        *,
        customer_id: UUID,
        name: str,
        updated_at: datetime,
    ) -> None:
        normalized = name.strip()
        if not normalized:
            raise ValueError("task name must not be empty")
        self.customer_id = customer_id
        self.name = normalized
        self.updated_at = updated_at

    def archive(self, archived_at: datetime) -> None:
        self.status = ResourceStatus.ARCHIVED
        self.updated_at = archived_at
