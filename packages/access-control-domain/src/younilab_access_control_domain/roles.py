from dataclasses import dataclass, field
from uuid import UUID


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
