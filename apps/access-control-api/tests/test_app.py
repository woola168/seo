from uuid import UUID
from urllib.parse import parse_qs, urlparse

from fastapi.testclient import TestClient

from younilab_access_control_api import create_app
from younilab_access_control_domain import (
    PERMISSIONS,
    AccountStatus,
    Role,
    UserAccount,
)
from younilab_access_control_infrastructure import (
    Argon2PasswordHasher,
    MemoryAccessControlRepository,
    MemoryNotificationPublisher,
)


def test_health_endpoint() -> None:
    response = TestClient(create_app()).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_me_requires_authentication() -> None:
    response = TestClient(create_app()).get("/api/v1/me")

    assert response.status_code == 401
    assert response.headers["content-type"].startswith("application/problem+json")


def test_login_rejects_unknown_request_fields() -> None:
    response = TestClient(create_app()).post(
        "/api/v1/auth/login",
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
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "LongPassword123!"},
    )

    assert login_response.status_code == 200
    access_token = login_response.json()["accessToken"]
    headers = {"Authorization": f"Bearer {access_token}"}
    assert client.get("/api/v1/me", headers=headers).status_code == 200

    create_role_response = client.post(
        "/api/v1/roles",
        headers=headers,
        json={"name": "SEO Viewer", "permissions": ["customers.read", "tasks.read"]},
    )
    assert create_role_response.status_code == 201
    assert create_role_response.json()["permissions"] == [
        "customers.read",
        "tasks.read",
    ]

    refresh_response = client.post("/api/v1/auth/refresh")
    assert refresh_response.status_code == 200
    assert refresh_response.json()["accessToken"] != access_token


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
        "/api/v1/auth/password-reset-requests",
        json={"email": "admin@example.com"},
    )

    assert request_response.status_code == 202
    reset_url = notifications.notifications[0].parameters["resetUrl"]
    token = parse_qs(urlparse(reset_url).query)["token"][0]
    old_login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "OldPassword123!"},
    )
    old_headers = {
        "Authorization": f"Bearer {old_login.json()['accessToken']}"
    }
    reset_response = client.post(
        "/api/v1/auth/password-resets",
        json={"token": token, "newPassword": "NewPassword123!"},
    )
    assert reset_response.status_code == 204
    assert client.get("/api/v1/me", headers=old_headers).status_code == 401
    assert client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "NewPassword123!"},
    ).status_code == 200


def test_password_reset_request_does_not_reveal_unknown_email() -> None:
    response = TestClient(create_app()).post(
        "/api/v1/auth/password-reset-requests",
        json={"email": "missing@example.com"},
    )

    assert response.status_code == 202
