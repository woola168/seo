from dataclasses import dataclass

from younilab_access_control_domain.models import (
    ProtectedResource,
    ResourceType,
    Role,
    UserAccount,
)


class AuthorizationReason:
    ALLOWED = "ALLOWED"
    ACCOUNT_INACTIVE = "ACCOUNT_INACTIVE"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    GLOBAL_ACCESS_GRANTED = "GLOBAL_ACCESS_GRANTED"
    CUSTOMER_ACCESS_GRANTED = "CUSTOMER_ACCESS_GRANTED"
    TASK_ACCESS_GRANTED = "TASK_ACCESS_GRANTED"
    RESOURCE_ACCESS_DENIED = "RESOURCE_ACCESS_DENIED"


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    reason_code: str


class AccessPolicy:
    def evaluate(
        self,
        *,
        user: UserAccount,
        roles: list[Role],
        permission: str,
        resource: ProtectedResource | None = None,
    ) -> PolicyDecision:
        if not user.is_active:
            return PolicyDecision(False, AuthorizationReason.ACCOUNT_INACTIVE)

        effective_permissions = frozenset().union(
            *(role.permissions for role in roles)
        )
        if permission not in effective_permissions:
            return PolicyDecision(False, AuthorizationReason.PERMISSION_DENIED)

        if any(role.has_global_resource_access for role in roles):
            return PolicyDecision(True, AuthorizationReason.GLOBAL_ACCESS_GRANTED)

        if resource is None:
            return PolicyDecision(True, AuthorizationReason.ALLOWED)

        if resource.type is ResourceType.CUSTOMER:
            if resource.id in user.customer_ids:
                return PolicyDecision(
                    True,
                    AuthorizationReason.CUSTOMER_ACCESS_GRANTED,
                )
            return PolicyDecision(False, AuthorizationReason.RESOURCE_ACCESS_DENIED)

        if resource.id in user.task_ids:
            return PolicyDecision(True, AuthorizationReason.TASK_ACCESS_GRANTED)
        if resource.customer_id in user.customer_ids:
            return PolicyDecision(
                True,
                AuthorizationReason.CUSTOMER_ACCESS_GRANTED,
            )
        return PolicyDecision(False, AuthorizationReason.RESOURCE_ACCESS_DENIED)

    def effective_permissions(
        self,
        *,
        user: UserAccount,
        roles: list[Role],
    ) -> frozenset[str]:
        if not user.is_active:
            return frozenset()
        return frozenset().union(*(role.permissions for role in roles))
