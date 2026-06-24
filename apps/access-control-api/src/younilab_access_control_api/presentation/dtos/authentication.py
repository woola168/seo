from datetime import datetime
from typing import Self

from pydantic import EmailStr, Field

from younilab_access_control_api.presentation.dtos.base import ApiModel, ApiRequest
from younilab_seo.access_control.application import IssuedTokens


class LoginRequest(ApiRequest):
    """用來建立密碼登入 session 的憑證。"""

    email: EmailStr
    password: str = Field(min_length=1)


class PasswordResetRequest(ApiRequest):
    """啟用中帳號可收到密碼重設連結的電子郵件。"""

    email: EmailStr


class ResetPasswordRequest(ApiRequest):
    """密碼重設使用的 recovery token 與新密碼。"""

    token: str = Field(min_length=1)
    new_password: str = Field(min_length=12, max_length=128)


class AcceptInvitationRequest(ApiRequest):
    """啟用受邀帳號使用的 invitation token 與初始密碼。"""

    token: str = Field(min_length=1)
    new_password: str = Field(min_length=12, max_length=128)


class TokenResponse(ApiModel):
    """登入或 refresh 後回傳的 Bearer access token。"""

    access_token: str
    token_type: str = "bearer"
    expires_at: datetime

    @classmethod
    def from_tokens(cls, tokens: IssuedTokens) -> Self:
        return cls(
            access_token=tokens.access_token,
            expires_at=tokens.access_token_expires_at,
        )
