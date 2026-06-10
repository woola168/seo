from uuid import UUID

from younilab_access_control_application.errors import ResourceNotFound
from younilab_access_control_application.interfaces import AccessControlRepository
from younilab_access_control_application.models import Capabilities
from younilab_access_control_domain import (
    AccessPolicy,
    ProtectedResource,
    ResourceType,
)
from younilab_authorization_contracts import (
    AuthorizationDecision,
    AuthorizationRequest,
    BatchAuthorizationDecision,
    BatchAuthorizationRequest,
)


class AuthorizationService:
    def __init__(
        self,
        repository: AccessControlRepository,
        policy: AccessPolicy | None = None,
    ) -> None:
        self._repository = repository
        self._policy = policy or AccessPolicy()

    async def evaluate(
        self,
        request: AuthorizationRequest,
    ) -> AuthorizationDecision:
        user = await self._repository.get_user(request.user_id)
        if user is None:
            raise ResourceNotFound
        roles = await self._repository.get_roles(user.role_ids)
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
        return BatchAuthorizationDecision(
            decisions=[
                await self.evaluate(item)
                for item in request.requests
            ]
        )

    async def capabilities(self, user_id: UUID) -> Capabilities:
        user = await self._repository.get_user(user_id)
        if user is None:
            raise ResourceNotFound
        roles = await self._repository.get_roles(user.role_ids)
        return Capabilities(
            permissions=self._policy.effective_permissions(user=user, roles=roles),
            has_global_resource_access=any(
                role.has_global_resource_access for role in roles
            ),
            customer_ids=frozenset(user.customer_ids),
            task_ids=frozenset(user.task_ids),
        )
