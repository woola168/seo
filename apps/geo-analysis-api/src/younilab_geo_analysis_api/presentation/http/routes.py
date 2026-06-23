from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, status

from younilab_geo_analysis_api.presentation.http.dtos import (
    AliasRequest,
    AliasResponse,
    CreateJobRequest,
    EntityRequest,
    EntityResponse,
    ExternalCallbackRequest,
    JobResponse,
    MarketRequest,
    MarketResponse,
    PageResponse,
    ProjectRequest,
    ProjectResponse,
    QueryPlatformRequest,
    QueryPlatformResponse,
    QueryRequest,
    QueryResponse,
    ScheduleRequest,
    ScheduleResponse,
    TopicRequest,
    TopicResponse,
)
from younilab_geo_analysis_api.presentation.http.store import GeoApiStore

router = APIRouter(prefix="/api/geo", tags=["geo-analysis"])


def _store(request: Request) -> GeoApiStore:
    return request.app.state.geo_store


@router.get("/projects", response_model=PageResponse)
async def list_projects(request: Request, customer_id: UUID | None = None) -> PageResponse:
    items = list(_store(request).projects.values())
    if customer_id is not None:
        items = [item for item in items if item["customer_id"] == customer_id]
    return PageResponse(items=[ProjectResponse(**item) for item in items], total=len(items))


@router.post("/projects", response_model=ProjectResponse, status_code=201)
async def create_project(request: Request, payload: ProjectRequest) -> ProjectResponse:
    return ProjectResponse(**_store(request).create_project(payload))


@router.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(request: Request, project_id: UUID) -> ProjectResponse:
    project = _store(request).projects.get(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="project not found")
    return ProjectResponse(**project)


@router.patch("/projects/{project_id}", response_model=ProjectResponse)
async def update_project(
    request: Request,
    project_id: UUID,
    payload: ProjectRequest,
) -> ProjectResponse:
    project = _store(request).update_project(project_id, payload)
    if project is None:
        raise HTTPException(status_code=404, detail="project not found")
    return ProjectResponse(**project)


@router.delete("/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(request: Request, project_id: UUID) -> None:
    if _store(request).projects.pop(project_id, None) is None:
        raise HTTPException(status_code=404, detail="project not found")


@router.get("/projects/{project_id}/markets", response_model=PageResponse)
async def list_markets(request: Request, project_id: UUID) -> PageResponse:
    items = [
        item for item in _store(request).markets.values() if item["project_id"] == project_id
    ]
    return PageResponse(items=[MarketResponse(**item) for item in items], total=len(items))


@router.post("/projects/{project_id}/markets", response_model=MarketResponse, status_code=201)
async def create_market(
    request: Request,
    project_id: UUID,
    payload: MarketRequest,
) -> MarketResponse:
    market = _store(request).create_market(project_id, payload)
    if market is None:
        raise HTTPException(status_code=404, detail="project not found")
    return MarketResponse(**market)


@router.patch("/markets/{market_id}", response_model=MarketResponse)
async def update_market(
    request: Request,
    market_id: UUID,
    payload: MarketRequest,
) -> MarketResponse:
    market = _store(request).update_market(market_id, payload)
    if market is None:
        raise HTTPException(status_code=404, detail="market not found")
    return MarketResponse(**market)


@router.delete("/markets/{market_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_market(request: Request, market_id: UUID) -> None:
    if _store(request).markets.pop(market_id, None) is None:
        raise HTTPException(status_code=404, detail="market not found")


@router.get("/projects/{project_id}/entities", response_model=PageResponse)
async def list_entities(request: Request, project_id: UUID) -> PageResponse:
    items = [
        item for item in _store(request).entities.values() if item["project_id"] == project_id
    ]
    return PageResponse(items=[EntityResponse(**item) for item in items], total=len(items))


@router.post("/projects/{project_id}/entities", response_model=EntityResponse, status_code=201)
async def create_entity(
    request: Request,
    project_id: UUID,
    payload: EntityRequest,
) -> EntityResponse:
    entity = _store(request).create_entity(project_id, payload)
    if entity is None:
        raise HTTPException(status_code=404, detail="project not found")
    return EntityResponse(**entity)


@router.get("/entities/{entity_id}", response_model=EntityResponse)
async def get_entity(request: Request, entity_id: UUID) -> EntityResponse:
    entity = _store(request).entities.get(entity_id)
    if entity is None:
        raise HTTPException(status_code=404, detail="entity not found")
    return EntityResponse(**entity)


@router.patch("/entities/{entity_id}", response_model=EntityResponse)
async def update_entity(
    request: Request,
    entity_id: UUID,
    payload: EntityRequest,
) -> EntityResponse:
    entity = _store(request).update_entity(entity_id, payload)
    if entity is None:
        raise HTTPException(status_code=404, detail="entity not found")
    return EntityResponse(**entity)


@router.delete("/entities/{entity_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_entity(request: Request, entity_id: UUID) -> None:
    if _store(request).entities.pop(entity_id, None) is None:
        raise HTTPException(status_code=404, detail="entity not found")


@router.get("/entities/{entity_id}/aliases", response_model=PageResponse)
async def list_aliases(request: Request, entity_id: UUID) -> PageResponse:
    items = [
        item for item in _store(request).aliases.values() if item["entity_id"] == entity_id
    ]
    return PageResponse(items=[AliasResponse(**item) for item in items], total=len(items))


@router.post("/entities/{entity_id}/aliases", response_model=AliasResponse, status_code=201)
async def create_alias(
    request: Request,
    entity_id: UUID,
    payload: AliasRequest,
) -> AliasResponse:
    alias = _store(request).create_alias(entity_id, payload)
    if alias is None:
        raise HTTPException(status_code=404, detail="entity not found")
    return AliasResponse(**alias)


@router.patch("/entity-aliases/{alias_id}", response_model=AliasResponse)
async def update_alias(
    request: Request,
    alias_id: UUID,
    payload: AliasRequest,
) -> AliasResponse:
    alias = _store(request).update_alias(alias_id, payload)
    if alias is None:
        raise HTTPException(status_code=404, detail="alias not found")
    return AliasResponse(**alias)


@router.delete("/entity-aliases/{alias_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_alias(request: Request, alias_id: UUID) -> None:
    if _store(request).aliases.pop(alias_id, None) is None:
        raise HTTPException(status_code=404, detail="alias not found")


@router.get("/projects/{project_id}/topics", response_model=PageResponse)
async def list_topics(request: Request, project_id: UUID) -> PageResponse:
    items = [
        item for item in _store(request).topics.values() if item["project_id"] == project_id
    ]
    return PageResponse(items=[TopicResponse(**item) for item in items], total=len(items))


@router.post("/projects/{project_id}/topics", response_model=TopicResponse, status_code=201)
async def create_topic(
    request: Request,
    project_id: UUID,
    payload: TopicRequest,
) -> TopicResponse:
    topic = _store(request).create_topic(project_id, payload)
    if topic is None:
        raise HTTPException(status_code=404, detail="project not found")
    return TopicResponse(**topic)


@router.patch("/topics/{topic_id}", response_model=TopicResponse)
async def update_topic(
    request: Request,
    topic_id: UUID,
    payload: TopicRequest,
) -> TopicResponse:
    topic = _store(request).update_topic(topic_id, payload)
    if topic is None:
        raise HTTPException(status_code=404, detail="topic not found")
    return TopicResponse(**topic)


@router.delete("/topics/{topic_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_topic(request: Request, topic_id: UUID) -> None:
    if _store(request).topics.pop(topic_id, None) is None:
        raise HTTPException(status_code=404, detail="topic not found")


@router.get("/projects/{project_id}/queries", response_model=PageResponse)
async def list_queries(request: Request, project_id: UUID) -> PageResponse:
    items = [
        item for item in _store(request).queries.values() if item["project_id"] == project_id
    ]
    return PageResponse(items=[QueryResponse(**item) for item in items], total=len(items))


@router.post("/projects/{project_id}/queries", response_model=QueryResponse, status_code=201)
async def create_query(
    request: Request,
    project_id: UUID,
    payload: QueryRequest,
) -> QueryResponse:
    query = _store(request).create_query(project_id, payload)
    if query is None:
        raise HTTPException(status_code=404, detail="project not found")
    return QueryResponse(**query)


@router.get("/queries/{query_id}", response_model=QueryResponse)
async def get_query(request: Request, query_id: UUID) -> QueryResponse:
    query = _store(request).queries.get(query_id)
    if query is None:
        raise HTTPException(status_code=404, detail="query not found")
    return QueryResponse(**query)


@router.patch("/queries/{query_id}", response_model=QueryResponse)
async def update_query(
    request: Request,
    query_id: UUID,
    payload: QueryRequest,
) -> QueryResponse:
    query = _store(request).update_query(query_id, payload)
    if query is None:
        raise HTTPException(status_code=404, detail="query not found")
    return QueryResponse(**query)


@router.delete("/queries/{query_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_query(request: Request, query_id: UUID) -> None:
    if _store(request).queries.pop(query_id, None) is None:
        raise HTTPException(status_code=404, detail="query not found")


@router.get("/queries/{query_id}/platforms", response_model=PageResponse)
async def list_query_platforms(request: Request, query_id: UUID) -> PageResponse:
    items = [
        item
        for item in _store(request).query_platforms.values()
        if item["query_id"] == query_id
    ]
    return PageResponse(
        items=[QueryPlatformResponse(**item) for item in items],
        total=len(items),
    )


@router.put("/queries/{query_id}/platforms", response_model=PageResponse)
async def replace_query_platforms(
    request: Request,
    query_id: UUID,
    payload: list[QueryPlatformRequest],
) -> PageResponse:
    items = _store(request).replace_query_platforms(query_id, payload)
    if items is None:
        raise HTTPException(status_code=404, detail="query not found")
    return PageResponse(
        items=[QueryPlatformResponse(**item) for item in items],
        total=len(items),
    )


@router.get("/queries/{query_id}/schedules", response_model=PageResponse)
async def list_schedules(request: Request, query_id: UUID) -> PageResponse:
    items = [
        item for item in _store(request).schedules.values() if item["query_id"] == query_id
    ]
    return PageResponse(
        items=[ScheduleResponse(**item) for item in items],
        total=len(items),
    )


@router.post("/queries/{query_id}/schedules", response_model=ScheduleResponse, status_code=201)
async def create_schedule(
    request: Request,
    query_id: UUID,
    payload: ScheduleRequest,
) -> ScheduleResponse:
    schedule = _store(request).create_schedule(query_id, payload)
    if schedule is None:
        raise HTTPException(status_code=404, detail="query not found")
    return ScheduleResponse(**schedule)


@router.patch("/schedules/{schedule_id}", response_model=ScheduleResponse)
async def update_schedule(
    request: Request,
    schedule_id: UUID,
    payload: ScheduleRequest,
) -> ScheduleResponse:
    schedule = _store(request).update_schedule(schedule_id, payload)
    if schedule is None:
        raise HTTPException(status_code=404, detail="schedule not found")
    return ScheduleResponse(**schedule)


@router.delete("/schedules/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_schedule(request: Request, schedule_id: UUID) -> None:
    if _store(request).schedules.pop(schedule_id, None) is None:
        raise HTTPException(status_code=404, detail="schedule not found")


@router.post("/queries/{query_id}/jobs", response_model=JobResponse, status_code=201)
async def create_job(
    request: Request,
    query_id: UUID,
    payload: CreateJobRequest,
) -> JobResponse:
    job = _store(request).create_job(query_id, payload)
    if job is None:
        raise HTTPException(status_code=404, detail="query not found")
    return JobResponse(**_store(request).job_dict(job))


@router.get("/projects/{project_id}/jobs", response_model=PageResponse)
async def list_jobs(request: Request, project_id: UUID) -> PageResponse:
    store = _store(request)
    jobs = [job for job in store.jobs.values() if job.project_id == project_id]
    return PageResponse(
        items=[JobResponse(**store.job_dict(job)) for job in jobs],
        total=len(jobs),
    )


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job(request: Request, job_id: UUID) -> JobResponse:
    job = _store(request).jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    return JobResponse(**_store(request).job_dict(job))


@router.post("/jobs/{job_id}/dispatch", response_model=JobResponse)
async def dispatch_job(request: Request, job_id: UUID) -> JobResponse:
    job = _store(request).jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="message publisher adapter is not configured",
    )


@router.post("/jobs/{job_id}/cancel", response_model=JobResponse)
async def cancel_job(request: Request, job_id: UUID) -> JobResponse:
    store = _store(request)
    job = store.jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    job.cancel(now=datetime.now(UTC))
    return JobResponse(**store.job_dict(job))


@router.post("/jobs/{job_id}/external-callbacks", response_model=JobResponse)
async def receive_external_callback(
    request: Request,
    job_id: UUID,
    payload: ExternalCallbackRequest,
) -> JobResponse:
    store = _store(request)
    job = store.jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    job.mark_external_status(
        external_run_id=payload.external_run_id,
        external_status=payload.status,
        error_code=payload.error_code,
        error_message=payload.error_message,
        now=datetime.now(UTC),
    )
    return JobResponse(**store.job_dict(job))
