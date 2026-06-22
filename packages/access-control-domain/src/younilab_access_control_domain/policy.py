from dataclasses import dataclass

from younilab_access_control_domain.accounts import UserAccount
from younilab_access_control_domain.resources import ProtectedResource, ResourceType
from younilab_access_control_domain.roles import Role


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
    """transport mapping 前的 domain authorization outcome。"""

    allowed: bool
    reason_code: str


class AccessPolicy:
    """評估單一使用者的 role permissions 與 resource grants。"""

    def evaluate(
        self,
        *,
        user: UserAccount,
        roles: list[Role],
        permission: str,
        resource: ProtectedResource | None = None,
    ) -> PolicyDecision:
        """回傳 request 第一個符合的允許或拒絕原因。"""
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
        """只對 active users 回傳 role permissions 的聯集。"""
        if not user.is_active:
            return frozenset()
        return frozenset().union(*(role.permissions for role in roles))
