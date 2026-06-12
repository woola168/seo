from datetime import datetime
from typing import Protocol
from uuid import UUID

from younilab_access_control_application.models import AccessClaims


class PasswordHasher(Protocol):
    def hash(self, password: str) -> str: ...

    def verify(self, password: str, password_hash: str) -> bool: ...


class TokenProvider(Protocol):
    def issue_access_token(
        self,
        *,
        user_id: UUID,
        session_id: UUID,
    ) -> tuple[str, datetime]: ...

    def decode_access_token(self, token: str) -> AccessClaims: ...

    def new_refresh_token(self) -> str: ...

    def digest_refresh_token(self, token: str) -> str: ...

    def refresh_token_expires_at(self) -> datetime: ...
