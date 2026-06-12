from datetime import datetime
from typing import Self

from pydantic import EmailStr, Field

from younilab_access_control_api.presentation.dtos.base import ApiModel, ApiRequest
from younilab_access_control_application import IssuedTokens


class LoginRequest(ApiRequest):
    email: EmailStr
    password: str = Field(min_length=1)


class TokenResponse(ApiModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime

    @classmethod
    def from_tokens(cls, tokens: IssuedTokens) -> Self:
        return cls(
            access_token=tokens.access_token,
            expires_at=tokens.access_token_expires_at,
        )
