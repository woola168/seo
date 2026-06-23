from datetime import datetime
from typing import Protocol
from uuid import UUID

from younilab_seo.access_control.application.models import AccessClaims


class PasswordHasher(Protocol):
    """在 application boundary 雜湊與驗證密碼憑證。"""

    def hash(self, password: str) -> str:
        """回傳可安全持久化的 password hash。"""
        ...

    def verify(self, password: str, password_hash: str) -> bool:
        """回傳明文密碼是否符合已儲存 hash。"""
        ...


class TokenProvider(Protocol):
    """簽發 access tokens 並管理 refresh-token material。"""

    def issue_access_token(
        self,
        *,
        user_id: UUID,
        session_id: UUID,
    ) -> tuple[str, datetime]:
        """簽發綁定使用者與 refresh session 的 access token。"""
        ...

    def decode_access_token(self, token: str) -> AccessClaims:
        """驗證 access token 並回傳 application claims。"""
        ...

    def new_refresh_token(self) -> str:
        """建立給 client 使用的不透明 refresh-token material。"""
        ...

    def digest_refresh_token(self, token: str) -> str:
        """回傳 refresh token 可安全持久化的 digest。"""
        ...

    def refresh_token_expires_at(self) -> datetime:
        """回傳新簽發 refresh token 的過期時間。"""
        ...


class RecoveryTokenProvider(Protocol):
    """為 reset 與 invitation flows 建立並 digest recovery tokens。"""

    def new_token(self) -> str:
        """建立 recovery link 使用的不透明 token material。"""
        ...

    def digest(self, token: str) -> str:
        """回傳 recovery token 可安全持久化的 digest。"""
        ...
