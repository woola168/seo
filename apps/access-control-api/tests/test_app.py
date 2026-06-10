from uuid import UUID

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
)


def test_health_endpoint() -> None:
    response = TestClient(create_app()).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_me_requires_authentication() -> None:
    response = TestClient(create_app()).get("/api/v1/me")

    assert response.status_code == 401
    assert response.headers["content-type"].startswith("application/problem+json")


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
