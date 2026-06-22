from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status

from younilab_resource_catalog_api.presentation.http.dependencies import bearer_token
from younilab_resource_catalog_api.presentation.http.dtos import (
    PageResponse,
    SaveTaskRequest,
    TaskResponse,
    page_response,
)
from younilab_resource_catalog_domain import ResourceStatus


router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.get("", response_model=PageResponse)
async def list_tasks(
    request: Request,
    token: str = Depends(bearer_token),
    search: str = "",
    customer_id: UUID | None = Query(default=None, alias="customerId"),
    resource_status: ResourceStatus | None = Query(
        default=ResourceStatus.ACTIVE,
        alias="status",
    ),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, alias="pageSize", ge=1, le=100),
) -> PageResponse:
    await request.app.state.authorizer.require(token, "tasks.read")
    tasks = await request.app.state.catalog.list_tasks(
        search=search,
        customer_id=customer_id,
        status=resource_status,
    )
    items = [
        TaskResponse.from_domain(
            task,
            (await request.app.state.catalog.get_customer(task.customer_id)).name,
        )
        for task in tasks
    ]
    return page_response(items, page, page_size)


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    payload: SaveTaskRequest,
    request: Request,
    token: str = Depends(bearer_token),
) -> TaskResponse:
    await request.app.state.authorizer.require(token, "tasks.create")
    task = await request.app.state.catalog.create_task(
        customer_id=payload.customer_id,
        name=payload.name,
    )
    customer = await request.app.state.catalog.get_customer(task.customer_id)
    return TaskResponse.from_domain(task, customer.name)


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: UUID,
    request: Request,
    token: str = Depends(bearer_token),
) -> TaskResponse:
    await request.app.state.authorizer.require(token, "tasks.read")
    task = await request.app.state.catalog.get_task(task_id)
    customer = await request.app.state.catalog.get_customer(task.customer_id)
    return TaskResponse.from_domain(task, customer.name)


@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: UUID,
    payload: SaveTaskRequest,
    request: Request,
    token: str = Depends(bearer_token),
) -> TaskResponse:
    await request.app.state.authorizer.require(token, "tasks.update")
    task = await request.app.state.catalog.update_task(
        task_id,
        customer_id=payload.customer_id,
        name=payload.name,
    )
    customer = await request.app.state.catalog.get_customer(task.customer_id)
    return TaskResponse.from_domain(task, customer.name)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: UUID,
    request: Request,
    token: str = Depends(bearer_token),
) -> None:
    await request.app.state.authorizer.require(token, "tasks.delete")
    await request.app.state.catalog.archive_task(task_id)
