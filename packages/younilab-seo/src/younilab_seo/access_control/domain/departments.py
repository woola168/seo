from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class Department:
    """可封存且保留歷史狀態的組織單位。"""

    id: UUID
    name: str
    description: str
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None = None

    def __post_init__(self) -> None:
        self.name = self.name.strip()
        self.description = self.description.strip()
        if not self.name:
            raise ValueError("department name must not be empty")

    @property
    def is_active(self) -> bool:
        return self.archived_at is None

    def update(self, *, name: str, description: str, updated_at: datetime) -> None:
        normalized_name = name.strip()
        if not normalized_name:
            raise ValueError("department name must not be empty")
        self.name = normalized_name
        self.description = description.strip()
        self.updated_at = updated_at

    def archive(self, archived_at: datetime) -> None:
        self.archived_at = archived_at
        self.updated_at = archived_at
