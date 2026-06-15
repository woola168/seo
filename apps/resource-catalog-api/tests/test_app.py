from fastapi.testclient import TestClient

from younilab_resource_catalog_api import create_app
from younilab_resource_catalog_infrastructure import (
    AllowAllAuthorizer,
    MemoryResourceCatalogRepository,
)


def test_customer_and_task_endpoints() -> None:
    client = TestClient(
        create_app(
            repository=MemoryResourceCatalogRepository(),
            authorizer=AllowAllAuthorizer(),
        )
    )
    headers = {"Authorization": "Bearer test"}

    customer_response = client.post(
        "/api/v1/customers",
        headers=headers,
        json={"name": "Acme"},
    )
    assert customer_response.status_code == 201
    customer_id = customer_response.json()["id"]

    task_response = client.post(
        "/api/v1/tasks",
        headers=headers,
        json={"customerId": customer_id, "name": "SEO audit"},
    )
    assert task_response.status_code == 201
    assert task_response.json()["customerName"] == "Acme"

    assert client.get("/api/v1/customers", headers=headers).json()["total"] == 1
    assert client.get("/api/v1/tasks", headers=headers).json()["total"] == 1
