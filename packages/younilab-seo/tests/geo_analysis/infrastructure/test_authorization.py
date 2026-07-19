from uuid import uuid4

import httpx
import pytest

from younilab_seo.geo_analysis.application import (
    ResourceCatalogVerificationUnavailable,
)
from younilab_seo.geo_analysis.infrastructure import (
    ResourceCatalogHttpReferenceVerifier,
)


@pytest.mark.anyio
async def test_resource_catalog_reader_batches_active_and_archived_customer_names() -> None:
    active_id = uuid4()
    archived_id = uuid4()

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["pageSize"] == "100"
        customer_id = (
            active_id if request.url.params["status"] == "active" else archived_id
        )
        return httpx.Response(
            200,
            json={
                "items": [{"id": str(customer_id), "name": str(customer_id)}],
                "totalPages": 1,
            },
        )

    reader = ResourceCatalogHttpReferenceVerifier(
        "http://resource-catalog",
        transport=httpx.MockTransport(handler),
    )

    names = await reader.list_customer_names(
        access_token="token",
        customer_ids=frozenset({active_id, archived_id}),
    )

    assert names == {
        active_id: str(active_id),
        archived_id: str(archived_id),
    }


@pytest.mark.anyio
async def test_resource_catalog_reader_translates_invalid_page_to_unavailable() -> None:
    reader = ResourceCatalogHttpReferenceVerifier(
        "http://resource-catalog",
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                json={"items": [{"name": "Missing id"}], "totalPages": 1},
            )
        ),
    )

    with pytest.raises(ResourceCatalogVerificationUnavailable):
        await reader.list_customer_names(
            access_token="token",
            customer_ids=frozenset({uuid4()}),
        )


@pytest.mark.anyio
async def test_resource_catalog_reader_translates_array_response_to_unavailable() -> None:
    reader = ResourceCatalogHttpReferenceVerifier(
        "http://resource-catalog",
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json=[])
        ),
    )

    with pytest.raises(ResourceCatalogVerificationUnavailable):
        await reader.list_customer_names(
            access_token="token",
            customer_ids=frozenset({uuid4()}),
        )
