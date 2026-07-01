from uuid import UUID

from younilab_seo.access_control.application.errors import ResourceNotFound
from younilab_seo.access_control.application.interfaces import AuthorizationRepository
from younilab_seo.access_control.application.models import Capabilities
from younilab_seo.access_control.domain import (
    AccessPolicy,
    ProtectedResource,
    ResourceType,
)
from younilab_seo.access_control.contracts import (
    AuthorizationDecision,
    AuthorizationRequest,
    BatchAuthorizationDecision,
    BatchAuthorizationRequest,
)


class AuthorizationService:
    """依 users、roles 與 grants 評估 access-control contracts。"""

    def __init__(
        self,
        repository: AuthorizationRepository,
        policy: AccessPolicy | None = None,
    ) -> None:
        self._repository = repository
        self._policy = policy or AccessPolicy()

    async def evaluate(
        self,
        request: AuthorizationRequest,
    ) -> AuthorizationDecision:
        """回傳指定 permission 的單筆 authorization decision。"""
        user = await self._repository.get_user(request.user_id)
        if user is None:
            raise ResourceNotFound
        roles = await self._repository.get_roles(user.role_ids, user.tenant_id)
        resource = (
            ProtectedResource(
                type=ResourceType(request.resource.type.value),
                id=request.resource.id,
                customer_id=request.resource.customer_id,
            )
            if request.resource is not None
            else None
        )
        decision = self._policy.evaluate(
            user=user,
            roles=roles,
            permission=request.permission,
            resource=resource,
        )
        return AuthorizationDecision(
            allowed=decision.allowed,
            reason_code=decision.reason_code,
        )

    async def batch_evaluate(
        self,
        request: BatchAuthorizationRequest,
    ) -> BatchAuthorizationDecision:
        """依 request 順序獨立評估每筆 authorization request。"""
        return BatchAuthorizationDecision(
            decisions=[await self.evaluate(item) for item in request.requests]
        )

    async def capabilities(self, user_id: UUID) -> Capabilities:
        """回傳使用者目前生效中的 permissions 與 resource grants。"""
        user = await self._repository.get_user(user_id)
        if user is None:
            raise ResourceNotFound
        roles = await self._repository.get_roles(user.role_ids, user.tenant_id)
        return Capabilities(
            permissions=self._policy.effective_permissions(user=user, roles=roles),
            has_global_resource_access=any(
                role.has_global_resource_access for role in roles
            ),
            customer_ids=frozenset(user.customer_ids),
            task_ids=frozenset(user.task_ids),
        )
