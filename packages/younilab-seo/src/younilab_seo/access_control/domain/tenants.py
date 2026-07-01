from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


DEFAULT_TENANT_ID = UUID("00000000-0000-4000-8000-000000000001")
DEFAULT_TENANT_CODE = "default"
DEFAULT_TENANT_NAME = "Default Tenant"


class TenantStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"


@dataclass
class Tenant:
    """Company-level boundary used to isolate users, roles, and departments."""

    id: UUID
    code: str
    name: str
    status: TenantStatus
    created_at: datetime
    updated_at: datetime
    disabled_at: datetime | None = None

    def __post_init__(self) -> None:
        self.code = self.code.strip().lower()
        self.name = self.name.strip()
        if not self.code:
            raise ValueError("tenant code must not be empty")
        if not self.name:
            raise ValueError("tenant name must not be empty")

    @property
    def is_active(self) -> bool:
        return self.status is TenantStatus.ACTIVE and self.disabled_at is None
