from datetime import timedelta

from younilab_access_control_application.errors import InvalidRecoveryToken
from younilab_access_control_application.interfaces import (
    AuthenticationRepository,
    Clock,
    IdGenerator,
    NotificationPublisher,
    PasswordHasher,
    RecoveryTokenProvider,
)
from younilab_access_control_application.models import Notification, PasswordReset


class AccountRecoveryService:
    """協調 password reset token 建立、通知與使用流程。"""

    def __init__(
        self,
        *,
        repository: AuthenticationRepository,
        password_hasher: PasswordHasher,
        token_provider: RecoveryTokenProvider,
        notifications: NotificationPublisher,
        clock: Clock,
        id_generator: IdGenerator,
        portal_url: str,
    ) -> None:
        self._repository = repository
        self._password_hasher = password_hasher
        self._token_provider = token_provider
        self._notifications = notifications
        self._clock = clock
        self._id_generator = id_generator
        self._portal_url = portal_url.rstrip("/")

    async def request_reset(self, email: str) -> None:
        """為 active users 建立 reset request，且不揭露帳號是否存在。"""
        user = await self._repository.get_user_by_email(email.strip().lower())
        if user is None or not user.is_active:
            return
        now = self._clock.now()
        await self._repository.revoke_password_resets(user.id, now)
        raw_token = self._token_provider.new_token()
        reset = PasswordReset(
            id=self._id_generator.new_id(),
            user_id=user.id,
            token_digest=self._token_provider.digest(raw_token),
            expires_at=now + timedelta(minutes=30),
            created_at=now,
        )
        await self._repository.save_password_reset(reset)
        await self._notifications.publish(
            Notification(
                id=self._id_generator.new_id(),
                recipient=user.email,
                template="password-reset",
                parameters={
                    "displayName": user.display_name,
                    "resetUrl": f"{self._portal_url}/reset-password?token={raw_token}",
                },
                created_at=now,
            )
        )

    async def reset_password(self, *, token: str, new_password: str) -> None:
        """使用有效 reset token 並撤銷使用者現有 sessions。"""
        reset = await self._repository.get_password_reset(
            self._token_provider.digest(token)
        )
        now = self._clock.now()
        if reset is None or not reset.is_valid(now):
            raise InvalidRecoveryToken
        password_hash = self._password_hasher.hash(new_password)
        await self._repository.update_password_hash(reset.user_id, password_hash)
        await self._repository.consume_password_reset(reset.id, now)
        await self._repository.revoke_password_resets(reset.user_id, now)
        await self._repository.revoke_user_sessions(reset.user_id, now)
