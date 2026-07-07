from uuid import UUID

from fastapi.testclient import TestClient

from younilab_resource_catalog_api import create_app
from younilab_seo.resource_catalog.application import (
    AccessDenied,
    AuthenticationRequired,
    AuthorizedPrincipal,
)
from younilab_seo.resource_catalog.infrastructure import (
    AllowAllAuthorizer,
    MemoryResourceCatalogRepository,
)

TENANT_ID = UUID("00000000-0000-4000-8000-000000000001")
OTHER_TENANT_ID = UUID("99999999-9999-4999-8999-999999999999")


def create_test_client() -> TestClient:
    return TestClient(
        create_app(
            repository=MemoryResourceCatalogRepository(),
            authorizer=AllowAllAuthorizer(),
        )
    )


def test_local_admin_portal_preflight_is_allowed() -> None:
    response = create_test_client().options(
        "/api/customers",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert response.headers["access-control-allow-credentials"] == "true"
    assert "GET" in response.headers["access-control-allow-methods"]
    assert "Authorization" in response.headers["access-control-allow-headers"]


def test_missing_bearer_token_returns_unauthorized() -> None:
    response = create_test_client().get("/api/customers")

    assert response.status_code == 401
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["detail"] == "Authentication required"


def test_expired_access_token_returns_unauthorized() -> None:
    client = TestClient(
        create_app(
            repository=MemoryResourceCatalogRepository(),
            authorizer=RaisingAuthorizer(AuthenticationRequired()),
        )
    )

    response = client.get("/api/customers", headers={"Authorization": "Bearer expired"})

    assert response.status_code == 401
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["detail"] == "Authentication required"


def test_permission_denial_returns_forbidden() -> None:
    client = TestClient(
        create_app(
            repository=MemoryResourceCatalogRepository(),
            authorizer=RaisingAuthorizer(AccessDenied()),
        )
    )

    response = client.get("/api/customers", headers={"Authorization": "Bearer denied"})

    assert response.status_code == 403
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["detail"] == "Access denied"


def test_customer_and_task_endpoints() -> None:
    client = create_test_client()
    headers = {"Authorization": "Bearer test"}

    health_response = client.get("/health")
    assert float(health_response.headers["X-Process-Time-Ms"]) >= 0

    customer_response = client.post(
        "/api/customers",
        headers=headers,
        json={"name": "Acme"},
    )
    assert customer_response.status_code == 201
    customer_id = customer_response.json()["id"]
    assert customer_response.json()["tenantId"] == str(TENANT_ID)

    task_response = client.post(
        "/api/tasks",
        headers=headers,
        json={"customerId": customer_id, "name": "SEO audit"},
    )
    assert task_response.status_code == 201
    assert task_response.json()["customerName"] == "Acme"
    assert task_response.json()["tenantId"] == str(TENANT_ID)

    assert client.get("/api/customers", headers=headers).json()["total"] == 1
    assert client.get("/api/tasks", headers=headers).json()["total"] == 1


def test_resource_catalog_routes_are_tenant_scoped() -> None:
    client = TestClient(
        create_app(
            repository=MemoryResourceCatalogRepository(),
            authorizer=TokenTenantAuthorizer(
                {
                    "tenant-a": AuthorizedPrincipal(
                        tenant_id=TENANT_ID,
                        permissions=frozenset(),
                        has_global_resource_access=True,
                        customer_ids=frozenset(),
                        task_ids=frozenset(),
                    ),
                    "tenant-b": AuthorizedPrincipal(
                        tenant_id=OTHER_TENANT_ID,
                        permissions=frozenset(),
                        has_global_resource_access=True,
                        customer_ids=frozenset(),
                        task_ids=frozenset(),
                    ),
                }
            ),
        )
    )

    response_a = client.post(
        "/api/customers",
        headers={"Authorization": "Bearer tenant-a"},
        json={"name": "Acme"},
    )
    response_b = client.post(
        "/api/customers",
        headers={"Authorization": "Bearer tenant-b"},
        json={"name": "Acme"},
    )

    assert response_a.status_code == 201
    assert response_b.status_code == 201
    assert client.get(
        "/api/customers",
        headers={"Authorization": "Bearer tenant-a"},
    ).json()["items"] == [response_a.json()]
    assert client.get(
        f"/api/customers/{response_a.json()['id']}",
        headers={"Authorization": "Bearer tenant-b"},
    ).status_code == 404


def test_resource_catalog_routes_apply_resource_grants() -> None:
    repository = MemoryResourceCatalogRepository()
    authorizer = TokenTenantAuthorizer({})
    client = TestClient(create_app(repository=repository, authorizer=authorizer))
    global_headers = {"Authorization": "Bearer global"}

    authorizer.principals_by_token["global"] = AuthorizedPrincipal(
        tenant_id=TENANT_ID,
        permissions=frozenset(),
        has_global_resource_access=True,
        customer_ids=frozenset(),
        task_ids=frozenset(),
    )
    customer_a = client.post(
        "/api/customers",
        headers=global_headers,
        json={"name": "Acme"},
    ).json()
    customer_b = client.post(
        "/api/customers",
        headers=global_headers,
        json={"name": "Beta"},
    ).json()
    task_a = client.post(
        "/api/tasks",
        headers=global_headers,
        json={"customerId": customer_a["id"], "name": "Audit"},
    ).json()
    task_b = client.post(
        "/api/tasks",
        headers=global_headers,
        json={"customerId": customer_b["id"], "name": "Tracking"},
    ).json()
    authorizer.principals_by_token["scoped"] = AuthorizedPrincipal(
        tenant_id=TENANT_ID,
        permissions=frozenset(),
        has_global_resource_access=False,
        customer_ids=frozenset({UUID(customer_a["id"])}),
        task_ids=frozenset({UUID(task_b["id"])}),
    )
    scoped_headers = {"Authorization": "Bearer scoped"}

    assert client.get("/api/customers", headers=scoped_headers).json()["items"] == [
        customer_a
    ]
    assert client.get("/api/tasks", headers=scoped_headers).json()["items"] == [
        task_a,
        task_b,
    ]
    assert client.get(
        f"/api/customers/{customer_b['id']}",
        headers=scoped_headers,
    ).status_code == 404
    assert client.get(
        f"/api/tasks/{task_b['id']}",
        headers=scoped_headers,
    ).status_code == 200
    assert client.post(
        "/api/tasks",
        headers=scoped_headers,
        json={"customerId": customer_b["id"], "name": "Blocked"},
    ).status_code == 404
    assert client.patch(
        f"/api/tasks/{task_a['id']}",
        headers=scoped_headers,
        json={"customerId": customer_b["id"], "name": "Moved"},
    ).status_code == 404


def test_blank_customer_name_returns_problem_details() -> None:
    client = create_test_client()

    response = client.post(
        "/api/customers",
        headers={"Authorization": "Bearer test"},
        json={"name": "   "},
    )

    assert response.status_code == 422
    assert response.headers["content-type"] == "application/problem+json"
    body = response.json()
    assert body["detail"] == "Request validation failed"
    assert _invalid_param_names(body) == {"body.name"}


def test_blank_task_name_returns_problem_details() -> None:
    client = create_test_client()

    response = client.post(
        "/api/tasks",
        headers={"Authorization": "Bearer test"},
        json={
            "customerId": "00000000-0000-0000-0000-000000000001",
            "name": "   ",
        },
    )

    assert response.status_code == 422
    assert response.headers["content-type"] == "application/problem+json"
    body = response.json()
    assert body["detail"] == "Request validation failed"
    assert _invalid_param_names(body) == {"body.name"}


def test_validation_problem_details_lists_multiple_invalid_fields() -> None:
    client = create_test_client()

    response = client.post(
        "/api/tasks",
        headers={"Authorization": "Bearer test"},
        json={"customerId": "not-a-uuid", "name": "   "},
    )

    assert response.status_code == 422
    body = response.json()
    assert _invalid_param_names(body) == {"body.customerId", "body.name"}
    assert all("reason" in item and "type" in item for item in body["invalidParams"])


def _invalid_param_names(body: dict) -> set[str]:
    return {item["name"] for item in body["invalidParams"]}


class TokenTenantAuthorizer:
    def __init__(self, principals_by_token: dict[str, AuthorizedPrincipal]) -> None:
        self.principals_by_token = principals_by_token

    async def require(
        self,
        access_token: str,
        permission: str,
    ) -> AuthorizedPrincipal:
        return self.principals_by_token[access_token]


class RaisingAuthorizer:
    def __init__(self, exc: Exception) -> None:
        self.exc = exc

    async def require(
        self,
        access_token: str,
        permission: str,
    ) -> AuthorizedPrincipal:
        raise self.exc
