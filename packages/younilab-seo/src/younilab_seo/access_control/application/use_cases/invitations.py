from datetime import timedelta
from uuid import UUID

from younilab_seo.access_control.application.errors import (
    Conflict,
    InvalidRecoveryToken,
    ResourceNotFound,
)
from younilab_seo.access_control.application.interfaces import (
    AccessManagementRepository,
    Clock,
    IdGenerator,
    NotificationPublisher,
    PasswordHasher,
    RecoveryTokenProvider,
)
from younilab_seo.access_control.application.models import Notification, UserInvitation
from younilab_seo.access_control.domain import AccountStatus, UserAccount


class InvitationService:
    """協調受邀使用者建立、invitation 寄送與接受流程。"""

    def __init__(
        self,
        *,
        repository: AccessManagementRepository,
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

    async def invite(
        self,
        *,
        actor_user_id: UUID,
        email: str,
        display_name: str,
        department_id: UUID | None,
        role_ids: set[UUID],
        customer_ids: set[UUID],
        task_ids: set[UUID],
        send_invitation: bool,
    ) -> UserInvitation:
        """建立包含 roles、grants 與選擇性寄送的受邀帳號。"""
        normalized_email = email.strip().lower()
        if await self._repository.get_user_by_email(normalized_email) is not None:
            raise Conflict("email already exists")
        if len(await self._repository.get_roles(role_ids)) != len(role_ids):
            raise ResourceNotFound
        if department_id is not None:
            department = await self._repository.get_department(department_id)
            if department is None or not department.is_active:
                raise ResourceNotFound

        now = self._clock.now()
        user = UserAccount(
            id=self._id_generator.new_id(),
            email=normalized_email,
            display_name=display_name,
            status=AccountStatus.INVITED,
            department_id=department_id,
            invited_at=now,
            created_at=now,
            updated_at=now,
        )
        invitation, raw_token = self._new_invitation(
            user=user,
            actor_user_id=actor_user_id,
            now=now,
        )
        await self._repository.create_invited_user(
            user=user,
            invitation=invitation,
            role_ids=role_ids,
            customer_ids=customer_ids,
            task_ids=task_ids,
        )
        if send_invitation:
            await self._publish(user, raw_token, now)
        return invitation

    async def resend(
        self,
        *,
        invitation_id: UUID,
        actor_user_id: UUID,
    ) -> UserInvitation:
        """撤銷目前 pending invitation 並寄送替代邀請。"""
        current = await self._repository.get_invitation(invitation_id)
        if current is None:
            raise ResourceNotFound
        user = await self._repository.get_user(current.user_id)
        if user is None or user.status is not AccountStatus.INVITED:
            raise Conflict("invitation is no longer pending")
        now = self._clock.now()
        await self._repository.revoke_invitation(current.id, now)
        invitation, raw_token = self._new_invitation(
            user=user,
            actor_user_id=actor_user_id,
            now=now,
        )
        await self._repository.save_invitation(invitation)
        await self._publish(user, raw_token, now)
        return invitation

    async def cancel(self, invitation_id: UUID) -> None:
        """撤銷 pending invitation，並刪除仍為 invited 狀態的使用者。"""
        invitation = await self._repository.get_invitation(invitation_id)
        if invitation is None:
            raise ResourceNotFound
        now = self._clock.now()
        await self._repository.revoke_invitation(invitation.id, now)
        user = await self._repository.get_user(invitation.user_id)
        if user is not None and user.status is AccountStatus.INVITED:
            user.delete(now)
            await self._repository.save_user(user)

    async def accept(self, *, token: str, new_password: str) -> UserAccount:
        """驗證 invitation token 後啟用受邀使用者。"""
        invitation = await self._repository.get_invitation_by_token(
            self._token_provider.digest(token)
        )
        now = self._clock.now()
        if invitation is None or not invitation.is_valid(now):
            raise InvalidRecoveryToken
        user = await self._repository.get_user(invitation.user_id)
        if user is None or user.status is not AccountStatus.INVITED:
            raise InvalidRecoveryToken
        password_hash = self._password_hasher.hash(new_password)
        await self._repository.update_password_hash(user.id, password_hash)
        user.change_status(AccountStatus.ACTIVE, now)
        await self._repository.save_user(user)
        await self._repository.accept_invitation(invitation.id, now)
        return user

    def _new_invitation(
        self,
        *,
        user: UserAccount,
        actor_user_id: UUID,
        now,
    ) -> tuple[UserInvitation, str]:
        raw_token = self._token_provider.new_token()
        return (
            UserInvitation(
                id=self._id_generator.new_id(),
                user_id=user.id,
                email=user.email,
                token_digest=self._token_provider.digest(raw_token),
                expires_at=now + timedelta(days=7),
                created_at=now,
                created_by=actor_user_id,
            ),
            raw_token,
        )

    async def _publish(self, user: UserAccount, raw_token: str, now) -> None:
        await self._notifications.publish(
            Notification(
                id=self._id_generator.new_id(),
                recipient=user.email,
                template="user-invitation",
                parameters={
                    "displayName": user.display_name,
                    "invitationUrl": (
                        f"{self._portal_url}/accept-invitation?token={raw_token}"
                    ),
                },
                created_at=now,
            )
        )
