from fastapi.testclient import TestClient

from younilab_resource_catalog_api import create_app
from younilab_seo.resource_catalog.infrastructure import (
    AllowAllAuthorizer,
    MemoryResourceCatalogRepository,
)


def create_test_client() -> TestClient:
    return TestClient(
        create_app(
            repository=MemoryResourceCatalogRepository(),
            authorizer=AllowAllAuthorizer(),
        )
    )


def test_customer_and_task_endpoints() -> None:
    client = create_test_client()
    headers = {"Authorization": "Bearer test"}

    customer_response = client.post(
        "/api/customers",
        headers=headers,
        json={"name": "Acme"},
    )
    assert customer_response.status_code == 201
    customer_id = customer_response.json()["id"]

    task_response = client.post(
        "/api/tasks",
        headers=headers,
        json={"customerId": customer_id, "name": "SEO audit"},
    )
    assert task_response.status_code == 201
    assert task_response.json()["customerName"] == "Acme"

    assert client.get("/api/customers", headers=headers).json()["total"] == 1
    assert client.get("/api/tasks", headers=headers).json()["total"] == 1


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

