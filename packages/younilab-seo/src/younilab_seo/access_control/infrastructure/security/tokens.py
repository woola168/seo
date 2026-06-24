import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt

from younilab_seo.access_control.application import AccessClaims, InvalidSession


class JwtTokenProvider:
    """簽發 RS256 JWT access tokens 的 TokenProvider adapter。"""

    def __init__(
        self,
        *,
        signing_key: str,
        verification_key: str,
        issuer: str = "younilab-access-control",
        audience: str = "younilab-seo",
        access_token_minutes: int = 10,
        refresh_token_days: int = 30,
    ) -> None:
        self._signing_key = signing_key
        self._verification_key = verification_key
        self._issuer = issuer
        self._audience = audience
        self._access_token_minutes = access_token_minutes
        self._refresh_token_days = refresh_token_days

    def issue_access_token(
        self,
        *,
        user_id: UUID,
        session_id: UUID,
    ) -> tuple[str, datetime]:
        now = datetime.now(UTC)
        expires_at = now + timedelta(minutes=self._access_token_minutes)
        token = jwt.encode(
            {
                "sub": str(user_id),
                "sid": str(session_id),
                "iss": self._issuer,
                "aud": self._audience,
                "iat": now,
                "exp": expires_at,
            },
            self._signing_key,
            algorithm="RS256",
        )
        return token, expires_at

    def decode_access_token(self, token: str) -> AccessClaims:
        try:
            claims = jwt.decode(
                token,
                self._verification_key,
                algorithms=["RS256"],
                issuer=self._issuer,
                audience=self._audience,
            )
            return AccessClaims(
                user_id=UUID(claims["sub"]),
                session_id=UUID(claims["sid"]),
                expires_at=datetime.fromtimestamp(claims["exp"], UTC),
            )
        except (jwt.PyJWTError, KeyError, TypeError, ValueError) as exc:
            raise InvalidSession from exc

    def new_refresh_token(self) -> str:
        return secrets.token_urlsafe(48)

    def digest_refresh_token(self, token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def refresh_token_expires_at(self) -> datetime:
        return datetime.now(UTC) + timedelta(days=self._refresh_token_days)


class SecureRecoveryTokenProvider:
    """使用 URL-safe random tokens 的 RecoveryTokenProvider adapter。"""

    def new_token(self) -> str:
        return secrets.token_urlsafe(48)

    def digest(self, token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()
