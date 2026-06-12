from datetime import UTC, datetime
from uuid import UUID

import pytest
from pydantic import ValidationError

from younilab_access_control_api.presentation.dtos import (
    CapabilitiesResponse,
    CreateRoleRequest,
    RoleResponse,
    TokenResponse,
    UserAccessResponse,
    UserResponse,
)
from younilab_access_control_application import Capabilities, IssuedTokens
from younilab_access_control_domain import AccountStatus, Role, UserAccount


USER_ID = UUID("11111111-1111-4111-8111-111111111111")
ROLE_ID = UUID("22222222-2222-4222-8222-222222222222")
CUSTOMER_ID = UUID("33333333-3333-4333-8333-333333333333")
TASK_ID = UUID("44444444-4444-4444-8444-444444444444")


def test_request_dto_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        CreateRoleRequest.model_validate(
            {
                "name": "Viewer",
                "permissions": [],
                "unexpected": True,
            }
        )


def test_token_response_maps_tokens_and_uses_camel_case() -> None:
    expires_at = datetime(2026, 6, 11, 12, tzinfo=UTC)
    response = TokenResponse.from_tokens(
        IssuedTokens(
            access_token="access-token",
            access_token_expires_at=expires_at,
            refresh_token="refresh-token",
            refresh_token_expires_at=expires_at,
        )
    )

    assert response.model_dump(by_alias=True) == {
        "accessToken": "access-token",
        "tokenType": "bearer",
        "expiresAt": expires_at,
    }


def test_response_dtos_map_domain_models() -> None:
    user = UserAccount(
        id=USER_ID,
        email="user@example.com",
        display_name="SEO User",
        status=AccountStatus.ACTIVE,
        role_ids={ROLE_ID},
        customer_ids={CUSTOMER_ID},
        task_ids={TASK_ID},
    )
    role = Role(
        id=ROLE_ID,
        name="viewer",
        permissions=frozenset({"tasks.read", "customers.read"}),
        has_global_resource_access=True,
    )
    capabilities = Capabilities(
        permissions=frozenset({"tasks.read", "customers.read"}),
        has_global_resource_access=False,
        customer_ids=frozenset({CUSTOMER_ID}),
        task_ids=frozenset({TASK_ID}),
    )

    assert UserResponse.from_domain(user).role_ids == [ROLE_ID]
    assert UserAccessResponse.from_domain(user).customer_ids == [CUSTOMER_ID]
    assert RoleResponse.from_domain(role).permissions == [
        "customers.read",
        "tasks.read",
    ]
    assert CapabilitiesResponse.from_domain(capabilities).task_ids == [TASK_ID]
