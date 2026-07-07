from uuid import UUID
from datetime import UTC, datetime
from urllib.parse import parse_qs, urlparse

from fastapi.testclient import TestClient

from younilab_access_control_api import create_app
from younilab_seo.access_control.domain import (
    PERMISSIONS,
    AccountStatus,
    Role,
    Tenant,
    TenantStatus,
    UserAccount,
)
from younilab_seo.access_control.infrastructure import (
    Argon2PasswordHasher,
    MemoryAccessControlRepository,
    MemoryNotificationPublisher,
)


def test_health_endpoint() -> None:
    response = TestClient(create_app()).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert float(response.headers["X-Process-Time-Ms"]) >= 0


def test_local_admin_portal_preflight_is_allowed() -> None:
    response = TestClient(create_app()).options(
        "/api/auth/login",
        headers={
            "Origin": "http://127.0.0.1:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type,authorization",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"
    assert response.headers["access-control-allow-credentials"] == "true"
    assert "POST" in response.headers["access-control-allow-methods"]
    assert "Authorization" in response.headers["access-control-allow-headers"]
    assert "Content-Type" in response.headers["access-control-allow-headers"]


def test_me_requires_authentication() -> None:
    response = TestClient(create_app()).get("/api/me")

    assert response.status_code == 401
    assert response.headers["content-type"].startswith("application/problem+json")


def test_login_rejects_unknown_request_fields() -> None:
    response = TestClient(create_app()).post(
        "/api/auth/login",
        json={
            "email": "admin@example.com",
            "password": "LongPassword123!",
            "unexpected": True,
        },
    )

    assert response.status_code == 422


def test_login_me_refresh_and_admin_role_management() -> None:
    user_id = UUID("11111111-1111-4111-8111-111111111111")
    role_id = UUID("22222222-2222-4222-8222-222222222222")
    hasher = Argon2PasswordHasher()
    repository = MemoryAccessControlRepository(
        users=[
            UserAccount(
                id=user_id,
                email="admin@example.com",
                display_name="SEO Admin",
                status=AccountStatus.ACTIVE,
                role_ids={role_id},
            )
        ],
        roles=[
            Role(
                id=role_id,
                name="admin",
                permissions=PERMISSIONS,
                is_system=True,
                has_global_resource_access=True,
            )
        ],
        password_hashes={user_id: hasher.hash("LongPassword123!")},
    )
    client = TestClient(
        create_app(repository=repository, password_hasher=hasher),
        base_url="https://testserver",
    )

    login_response = client.post(
        "/api/auth/login",
        json={"email": "admin@example.com", "password": "LongPassword123!"},
    )

    assert login_response.status_code == 200
    access_token = login_response.json()["accessToken"]
    headers = {"Authorization": f"Bearer {access_token}"}
    me_response = client.get("/api/me", headers=headers)
    assert me_response.status_code == 200
    assert me_response.json()["tenantId"] == "00000000-0000-4000-8000-000000000001"
    assert me_response.json()["tenantName"] == "Default Tenant"

    create_role_response = client.post(
        "/api/roles",
        headers=headers,
        json={"name": "SEO Viewer", "permissions": ["customers.read", "tasks.read"]},
    )
    assert create_role_response.status_code == 201
    assert create_role_response.json()["permissions"] == [
        "customers.read",
        "tasks.read",
    ]

    refresh_response = client.post("/api/auth/refresh")
    assert refresh_response.status_code == 200
    assert refresh_response.json()["accessToken"] != access_token


def test_login_rejects_user_when_tenant_is_disabled() -> None:
    tenant_id = UUID("99999999-9999-4999-8999-999999999999")
    user_id = UUID("11111111-1111-4111-8111-111111111111")
    hasher = Argon2PasswordHasher()
    now = datetime.now(UTC)
    repository = MemoryAccessControlRepository(
        tenants=[
            Tenant(
                id=tenant_id,
                code="disabled-company",
                name="Disabled Company",
                status=TenantStatus.DISABLED,
                created_at=now,
                updated_at=now,
                disabled_at=now,
            )
        ],
        users=[
            UserAccount(
                id=user_id,
                tenant_id=tenant_id,
                email="admin@example.com",
                display_name="SEO Admin",
                status=AccountStatus.ACTIVE,
            )
        ],
        password_hashes={user_id: hasher.hash("LongPassword123!")},
    )
    client = TestClient(create_app(repository=repository, password_hasher=hasher))

    response = client.post(
        "/api/auth/login",
        json={"email": "admin@example.com", "password": "LongPassword123!"},
    )

    assert response.status_code == 403


def test_user_management_is_scoped_to_current_tenant() -> None:
    tenant_id = UUID("99999999-9999-4999-8999-999999999999")
    admin_user_id = UUID("11111111-1111-4111-8111-111111111111")
    other_user_id = UUID("22222222-2222-4222-8222-222222222222")
    admin_role_id = UUID("33333333-3333-4333-8333-333333333333")
    other_role_id = UUID("44444444-4444-4444-8444-444444444444")
    hasher = Argon2PasswordHasher()
    now = datetime.now(UTC)
    repository = MemoryAccessControlRepository(
        tenants=[
            Tenant(
                id=tenant_id,
                code="other-company",
                name="Other Company",
                status=TenantStatus.ACTIVE,
                created_at=now,
                updated_at=now,
            )
        ],
        users=[
            UserAccount(
                id=admin_user_id,
                email="admin@example.com",
                display_name="SEO Admin",
                status=AccountStatus.ACTIVE,
                role_ids={admin_role_id},
            ),
            UserAccount(
                id=other_user_id,
                tenant_id=tenant_id,
                email="other@example.com",
                display_name="Other User",
                status=AccountStatus.ACTIVE,
                role_ids={other_role_id},
            ),
        ],
        roles=[
            Role(
                id=admin_role_id,
                name="admin",
                permissions=PERMISSIONS,
                is_system=True,
                has_global_resource_access=True,
            ),
            Role(
                id=other_role_id,
                tenant_id=tenant_id,
                name="other-admin",
                permissions=PERMISSIONS,
                is_system=True,
                has_global_resource_access=True,
            ),
        ],
        password_hashes={admin_user_id: hasher.hash("LongPassword123!")},
    )
    client = TestClient(create_app(repository=repository, password_hasher=hasher))
    login_response = client.post(
        "/api/auth/login",
        json={"email": "admin@example.com", "password": "LongPassword123!"},
    )
    headers = {"Authorization": f"Bearer {login_response.json()['accessToken']}"}

    users_response = client.get("/api/users", headers=headers)
    other_user_response = client.get(f"/api/users/{other_user_id}", headers=headers)

    assert users_response.status_code == 200
    assert [user["id"] for user in users_response.json()] == [str(admin_user_id)]
    assert other_user_response.status_code == 404


def test_invitation_rejects_duplicate_email_across_tenants_for_now() -> None:
    tenant_id = UUID("99999999-9999-4999-8999-999999999999")
    admin_user_id = UUID("11111111-1111-4111-8111-111111111111")
    other_user_id = UUID("22222222-2222-4222-8222-222222222222")
    admin_role_id = UUID("33333333-3333-4333-8333-333333333333")
    hasher = Argon2PasswordHasher()
    now = datetime.now(UTC)
    repository = MemoryAccessControlRepository(
        tenants=[
            Tenant(
                id=tenant_id,
                code="other-company",
                name="Other Company",
                status=TenantStatus.ACTIVE,
                created_at=now,
                updated_at=now,
            )
        ],
        users=[
            UserAccount(
                id=admin_user_id,
                email="admin@example.com",
                display_name="SEO Admin",
                status=AccountStatus.ACTIVE,
                role_ids={admin_role_id},
            ),
            UserAccount(
                id=other_user_id,
                tenant_id=tenant_id,
                email="shared@example.com",
                display_name="Other User",
                status=AccountStatus.ACTIVE,
            ),
        ],
        roles=[
            Role(
                id=admin_role_id,
                name="admin",
                permissions=PERMISSIONS,
                is_system=True,
                has_global_resource_access=True,
            )
        ],
        password_hashes={admin_user_id: hasher.hash("LongPassword123!")},
    )
    client = TestClient(create_app(repository=repository, password_hasher=hasher))
    login_response = client.post(
        "/api/auth/login",
        json={"email": "admin@example.com", "password": "LongPassword123!"},
    )
    headers = {"Authorization": f"Bearer {login_response.json()['accessToken']}"}

    response = client.post(
        "/api/user-invitations",
        headers=headers,
        json={
            "email": "shared@example.com",
            "displayName": "Shared User",
            "departmentId": None,
            "roleIds": [str(admin_role_id)],
            "customerIds": [],
            "taskIds": [],
            "sendInvitation": False,
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "email already exists"


def test_delete_role_removes_unused_non_system_role() -> None:
    user_id = UUID("11111111-1111-4111-8111-111111111111")
    admin_role_id = UUID("22222222-2222-4222-8222-222222222222")
    deleted_role_id = UUID("33333333-3333-4333-8333-333333333333")
    hasher = Argon2PasswordHasher()
    repository = MemoryAccessControlRepository(
        users=[
            UserAccount(
                id=user_id,
                email="admin@example.com",
                display_name="SEO Admin",
                status=AccountStatus.ACTIVE,
                role_ids={admin_role_id},
            )
        ],
        roles=[
            Role(
                id=admin_role_id,
                name="admin",
                permissions=PERMISSIONS,
                is_system=True,
                has_global_resource_access=True,
            ),
            Role(
                id=deleted_role_id,
                name="SEO Viewer",
                permissions=frozenset({"customers.read"}),
            ),
        ],
        password_hashes={user_id: hasher.hash("LongPassword123!")},
    )
    client = TestClient(
        create_app(repository=repository, password_hasher=hasher),
        base_url="https://testserver",
    )
    login_response = client.post(
        "/api/auth/login",
        json={"email": "admin@example.com", "password": "LongPassword123!"},
    )
    headers = {"Authorization": f"Bearer {login_response.json()['accessToken']}"}

    response = client.delete(f"/api/roles/{deleted_role_id}", headers=headers)

    assert response.status_code == 204
    roles_response = client.get("/api/roles", headers=headers)
    assert deleted_role_id not in {
        UUID(role["id"]) for role in roles_response.json()
    }


def test_delete_role_rejects_system_in_use_missing_and_unauthorized_roles() -> None:
    admin_user_id = UUID("11111111-1111-4111-8111-111111111111")
    viewer_user_id = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
    admin_role_id = UUID("22222222-2222-4222-8222-222222222222")
    used_role_id = UUID("33333333-3333-4333-8333-333333333333")
    viewer_role_id = UUID("44444444-4444-4444-8444-444444444444")
    missing_role_id = UUID("55555555-5555-4555-8555-555555555555")
    hasher = Argon2PasswordHasher()
    repository = MemoryAccessControlRepository(
        users=[
            UserAccount(
                id=admin_user_id,
                email="admin@example.com",
                display_name="SEO Admin",
                status=AccountStatus.ACTIVE,
                role_ids={admin_role_id},
            ),
            UserAccount(
                id=viewer_user_id,
                email="viewer@example.com",
                display_name="SEO Viewer",
                status=AccountStatus.ACTIVE,
                role_ids={viewer_role_id, used_role_id},
            ),
        ],
        roles=[
            Role(
                id=admin_role_id,
                name="admin",
                permissions=PERMISSIONS,
                is_system=True,
                has_global_resource_access=True,
            ),
            Role(
                id=used_role_id,
                name="Used Role",
                permissions=frozenset({"customers.read"}),
            ),
            Role(
                id=viewer_role_id,
                name="viewer",
                permissions=frozenset({"roles.read"}),
            ),
        ],
        password_hashes={
            admin_user_id: hasher.hash("LongPassword123!"),
            viewer_user_id: hasher.hash("LongPassword123!"),
        },
    )
    client = TestClient(
        create_app(repository=repository, password_hasher=hasher),
        base_url="https://testserver",
    )
    admin_login = client.post(
        "/api/auth/login",
        json={"email": "admin@example.com", "password": "LongPassword123!"},
    )
    viewer_login = client.post(
        "/api/auth/login",
        json={"email": "viewer@example.com", "password": "LongPassword123!"},
    )
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['accessToken']}"}
    viewer_headers = {"Authorization": f"Bearer {viewer_login.json()['accessToken']}"}

    system_response = client.delete(
        f"/api/roles/{admin_role_id}",
        headers=admin_headers,
    )
    used_response = client.delete(
        f"/api/roles/{used_role_id}",
        headers=admin_headers,
    )
    missing_response = client.delete(
        f"/api/roles/{missing_role_id}",
        headers=admin_headers,
    )
    unauthorized_response = client.delete(
        f"/api/roles/{used_role_id}",
        headers=viewer_headers,
    )

    assert system_response.status_code == 409
    assert system_response.json()["detail"] == "system role cannot be deleted"
    assert used_response.status_code == 409
    assert used_response.json()["detail"] == "role is still in use"
    assert missing_response.status_code == 404
    assert unauthorized_response.status_code == 403


def test_password_reset_creates_notification_and_replaces_password() -> None:
    user_id = UUID("11111111-1111-4111-8111-111111111111")
    hasher = Argon2PasswordHasher()
    repository = MemoryAccessControlRepository(
        users=[
            UserAccount(
                id=user_id,
                email="admin@example.com",
                display_name="SEO Admin",
                status=AccountStatus.ACTIVE,
            )
        ],
        password_hashes={user_id: hasher.hash("OldPassword123!")},
    )
    notifications = MemoryNotificationPublisher()
    client = TestClient(
        create_app(
            repository=repository,
            password_hasher=hasher,
            notifications=notifications,
        )
    )

    request_response = client.post(
        "/api/auth/password-reset-requests",
        json={"email": "admin@example.com"},
    )

    assert request_response.status_code == 202
    reset_url = notifications.notifications[0].parameters["resetUrl"]
    token = parse_qs(urlparse(reset_url).query)["token"][0]
    old_login = client.post(
        "/api/auth/login",
        json={"email": "admin@example.com", "password": "OldPassword123!"},
    )
    old_headers = {
        "Authorization": f"Bearer {old_login.json()['accessToken']}"
    }
    reset_response = client.post(
        "/api/auth/password-resets",
        json={"token": token, "newPassword": "NewPassword123!"},
    )
    assert reset_response.status_code == 204
    assert client.get("/api/me", headers=old_headers).status_code == 401
    assert client.post(
        "/api/auth/login",
        json={"email": "admin@example.com", "password": "NewPassword123!"},
    ).status_code == 200


def test_password_reset_request_does_not_reveal_unknown_email() -> None:
    response = TestClient(create_app()).post(
        "/api/auth/password-reset-requests",
        json={"email": "missing@example.com"},
    )

    assert response.status_code == 202
