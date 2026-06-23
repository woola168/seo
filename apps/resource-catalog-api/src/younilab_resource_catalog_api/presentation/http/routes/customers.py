from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status

from younilab_resource_catalog_api.presentation.http.dependencies import bearer_token
from younilab_resource_catalog_api.presentation.http.dtos import (
    CustomerResponse,
    PageResponse,
    SaveCustomerRequest,
    page_response,
)
from younilab_seo.resource_catalog.domain import ResourceStatus


router = APIRouter(prefix="/api/customers", tags=["customers"])


@router.get("", response_model=PageResponse)
async def list_customers(
    request: Request,
    token: str = Depends(bearer_token),
    search: str = "",
    resource_status: ResourceStatus | None = Query(
        default=ResourceStatus.ACTIVE,
        alias="status",
    ),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, alias="pageSize", ge=1, le=100),
) -> PageResponse:
    await request.app.state.authorizer.require(token, "customers.read")
    customers = await request.app.state.catalog.list_customers(
        search=search,
        status=resource_status,
    )
    return page_response(
        [CustomerResponse.from_domain(item) for item in customers],
        page,
        page_size,
    )


@router.post(
    "",
    response_model=CustomerResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_customer(
    payload: SaveCustomerRequest,
    request: Request,
    token: str = Depends(bearer_token),
) -> CustomerResponse:
    await request.app.state.authorizer.require(token, "customers.create")
    return CustomerResponse.from_domain(
        await request.app.state.catalog.create_customer(payload.name)
    )


@router.get("/{customer_id}", response_model=CustomerResponse)
async def get_customer(
    customer_id: UUID,
    request: Request,
    token: str = Depends(bearer_token),
) -> CustomerResponse:
    await request.app.state.authorizer.require(token, "customers.read")
    return CustomerResponse.from_domain(
        await request.app.state.catalog.get_customer(customer_id)
    )


@router.patch("/{customer_id}", response_model=CustomerResponse)
async def update_customer(
    customer_id: UUID,
    payload: SaveCustomerRequest,
    request: Request,
    token: str = Depends(bearer_token),
) -> CustomerResponse:
    await request.app.state.authorizer.require(token, "customers.update")
    return CustomerResponse.from_domain(
        await request.app.state.catalog.update_customer(customer_id, payload.name)
    )


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_customer(
    customer_id: UUID,
    request: Request,
    token: str = Depends(bearer_token),
) -> None:
    await request.app.state.authorizer.require(token, "customers.delete")
    await request.app.state.catalog.archive_customer(customer_id)
