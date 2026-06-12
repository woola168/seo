from younilab_access_control_application.errors import (
    AccountUnavailable,
    InvalidCredentials,
    InvalidSession,
)
from younilab_access_control_application.interfaces import (
    AuthenticationRepository,
    Clock,
    IdGenerator,
    PasswordHasher,
    TokenProvider,
)
from younilab_access_control_application.models import IssuedTokens, RefreshSession


class AuthenticationService:
    def __init__(
        self,
        *,
        repository: AuthenticationRepository,
        password_hasher: PasswordHasher,
        token_provider: TokenProvider,
        clock: Clock,
        id_generator: IdGenerator,
    ) -> None:
        self._repository = repository
        self._password_hasher = password_hasher
        self._token_provider = token_provider
        self._clock = clock
        self._id_generator = id_generator

    async def login(self, *, email: str, password: str) -> IssuedTokens:
        user = await self._repository.get_user_by_email(email.strip().lower())
        if user is None:
            raise InvalidCredentials
        password_hash = await self._repository.get_password_hash(user.id)
        if password_hash is None or not self._password_hasher.verify(
            password,
            password_hash,
        ):
            raise InvalidCredentials
        if not user.is_active:
            raise AccountUnavailable

        session_id = self._id_generator.new_id()
        family_id = self._id_generator.new_id()
        return await self._issue_tokens(
            user_id=user.id,
            session_id=session_id,
            family_id=family_id,
        )

    async def refresh(self, refresh_token: str) -> IssuedTokens:
        digest = self._token_provider.digest_refresh_token(refresh_token)
        current = await self._repository.get_refresh_session(digest)
        if current is None:
            raise InvalidSession

        now = self._clock.now()
        if not current.is_valid(now):
            await self._repository.revoke_session_family(current.family_id, now)
            raise InvalidSession

        user = await self._repository.get_user(current.user_id)
        if user is None or not user.is_active:
            await self._repository.revoke_session_family(current.family_id, now)
            raise AccountUnavailable

        replacement_id = self._id_generator.new_id()
        raw_refresh_token = self._token_provider.new_refresh_token()
        replacement = RefreshSession(
            id=replacement_id,
            user_id=user.id,
            token_digest=self._token_provider.digest_refresh_token(
                raw_refresh_token
            ),
            family_id=current.family_id,
            expires_at=self._token_provider.refresh_token_expires_at(),
        )
        access_token, access_expires_at = self._token_provider.issue_access_token(
            user_id=user.id,
            session_id=replacement_id,
        )
        await self._repository.replace_refresh_session(
            current_session_id=current.id,
            replacement=replacement,
            revoked_at=now,
        )
        return IssuedTokens(
            access_token=access_token,
            access_token_expires_at=access_expires_at,
            refresh_token=raw_refresh_token,
            refresh_token_expires_at=replacement.expires_at,
        )

    async def logout(self, access_token: str) -> None:
        claims = self._token_provider.decode_access_token(access_token)
        await self._repository.revoke_refresh_session(
            claims.session_id,
            self._clock.now(),
        )

    async def logout_all(self, access_token: str) -> None:
        claims = self._token_provider.decode_access_token(access_token)
        await self._repository.revoke_user_sessions(
            claims.user_id,
            self._clock.now(),
        )

    async def _issue_tokens(
        self,
        *,
        user_id,
        session_id,
        family_id,
    ) -> IssuedTokens:
        raw_refresh_token = self._token_provider.new_refresh_token()
        refresh_expires_at = self._token_provider.refresh_token_expires_at()
        session = RefreshSession(
            id=session_id,
            user_id=user_id,
            token_digest=self._token_provider.digest_refresh_token(
                raw_refresh_token
            ),
            family_id=family_id,
            expires_at=refresh_expires_at,
        )
        access_token, access_expires_at = self._token_provider.issue_access_token(
            user_id=user_id,
            session_id=session_id,
        )
        await self._repository.save_refresh_session(session)
        return IssuedTokens(
            access_token=access_token,
            access_token_expires_at=access_expires_at,
            refresh_token=raw_refresh_token,
            refresh_token_expires_at=refresh_expires_at,
        )
