from dataclasses import asdict
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
from younilab_seo.geo_analysis.application import (
    CreateQueryRunJobCommand,
    ExternalRunCallback,
    GeoEntityAliasCommand,
    GeoEntityCommand,
    GeoMarketCommand,
    GeoProjectCommand,
    GeoQueryCommand,
    GeoQueryPlatformCommand,
    GeoQueryScheduleCommand,
    GeoTopicCommand,
    ManageGeoSetup,
    ManageQueryRunJobs,
)
from younilab_seo.geo_analysis.domain import GeoQueryRunJob

router = APIRouter(prefix="/api/geo", tags=["geo-analysis"])


def _setup(request: Request) -> ManageGeoSetup:
    return request.app.state.manage_geo_setup


def _jobs(request: Request) -> ManageQueryRunJobs:
    return request.app.state.manage_query_run_jobs


def _record_data(record) -> dict:
    return record.model_dump()


def _job_data(job: GeoQueryRunJob) -> dict:
    data = asdict(job)
    data["status"] = job.status.value
    return data


@router.get("/projects", response_model=PageResponse)
async def list_projects(request: Request, customer_id: UUID | None = None) -> PageResponse:
    items = await _setup(request).list_projects(customer_id)
    return PageResponse(
        items=[ProjectResponse(**_record_data(item)) for item in items],
        total=len(items),
    )


@router.post("/projects", response_model=ProjectResponse, status_code=201)
async def create_project(request: Request, payload: ProjectRequest) -> ProjectResponse:
    project = await _setup(request).create_project(
        GeoProjectCommand(**payload.model_dump())
    )
    return ProjectResponse(**_record_data(project))


@router.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(request: Request, project_id: UUID) -> ProjectResponse:
    project = await _setup(request).get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="project not found")
    return ProjectResponse(**_record_data(project))


@router.patch("/projects/{project_id}", response_model=ProjectResponse)
async def update_project(
    request: Request,
    project_id: UUID,
    payload: ProjectRequest,
) -> ProjectResponse:
    project = await _setup(request).update_project(
        project_id,
        GeoProjectCommand(**payload.model_dump()),
    )
    if project is None:
        raise HTTPException(status_code=404, detail="project not found")
    return ProjectResponse(**_record_data(project))


@router.delete("/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(request: Request, project_id: UUID) -> None:
    if not await _setup(request).delete_project(project_id):
        raise HTTPException(status_code=404, detail="project not found")


@router.get("/projects/{project_id}/markets", response_model=PageResponse)
async def list_markets(request: Request, project_id: UUID) -> PageResponse:
    items = await _setup(request).list_markets(project_id)
    return PageResponse(
        items=[MarketResponse(**_record_data(item)) for item in items],
        total=len(items),
    )


@router.post("/projects/{project_id}/markets", response_model=MarketResponse, status_code=201)
async def create_market(
    request: Request,
    project_id: UUID,
    payload: MarketRequest,
) -> MarketResponse:
    market = await _setup(request).create_market(
        project_id,
        GeoMarketCommand(**payload.model_dump()),
    )
    if market is None:
        raise HTTPException(status_code=404, detail="project not found")
    return MarketResponse(**_record_data(market))


@router.patch("/markets/{market_id}", response_model=MarketResponse)
async def update_market(
    request: Request,
    market_id: UUID,
    payload: MarketRequest,
) -> MarketResponse:
    market = await _setup(request).update_market(
        market_id,
        GeoMarketCommand(**payload.model_dump()),
    )
    if market is None:
        raise HTTPException(status_code=404, detail="market not found")
    return MarketResponse(**_record_data(market))


@router.delete("/markets/{market_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_market(request: Request, market_id: UUID) -> None:
    if not await _setup(request).delete_market(market_id):
        raise HTTPException(status_code=404, detail="market not found")


@router.get("/projects/{project_id}/entities", response_model=PageResponse)
async def list_entities(request: Request, project_id: UUID) -> PageResponse:
    items = await _setup(request).list_entities(project_id)
    return PageResponse(
        items=[EntityResponse(**_record_data(item)) for item in items],
        total=len(items),
    )


@router.post("/projects/{project_id}/entities", response_model=EntityResponse, status_code=201)
async def create_entity(
    request: Request,
    project_id: UUID,
    payload: EntityRequest,
) -> EntityResponse:
    entity = await _setup(request).create_entity(
        project_id,
        GeoEntityCommand(**payload.model_dump()),
    )
    if entity is None:
        raise HTTPException(status_code=404, detail="project not found")
    return EntityResponse(**_record_data(entity))


@router.get("/entities/{entity_id}", response_model=EntityResponse)
async def get_entity(request: Request, entity_id: UUID) -> EntityResponse:
    entity = await _setup(request).get_entity(entity_id)
    if entity is None:
        raise HTTPException(status_code=404, detail="entity not found")
    return EntityResponse(**_record_data(entity))


@router.patch("/entities/{entity_id}", response_model=EntityResponse)
async def update_entity(
    request: Request,
    entity_id: UUID,
    payload: EntityRequest,
) -> EntityResponse:
    entity = await _setup(request).update_entity(
        entity_id,
        GeoEntityCommand(**payload.model_dump()),
    )
    if entity is None:
        raise HTTPException(status_code=404, detail="entity not found")
    return EntityResponse(**_record_data(entity))


@router.delete("/entities/{entity_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_entity(request: Request, entity_id: UUID) -> None:
    if not await _setup(request).delete_entity(entity_id):
        raise HTTPException(status_code=404, detail="entity not found")


@router.get("/entities/{entity_id}/aliases", response_model=PageResponse)
async def list_aliases(request: Request, entity_id: UUID) -> PageResponse:
    items = await _setup(request).list_aliases(entity_id)
    return PageResponse(
        items=[AliasResponse(**_record_data(item)) for item in items],
        total=len(items),
    )


@router.post("/entities/{entity_id}/aliases", response_model=AliasResponse, status_code=201)
async def create_alias(
    request: Request,
    entity_id: UUID,
    payload: AliasRequest,
) -> AliasResponse:
    alias = await _setup(request).create_alias(
        entity_id,
        GeoEntityAliasCommand(**payload.model_dump()),
    )
    if alias is None:
        raise HTTPException(status_code=404, detail="entity not found")
    return AliasResponse(**_record_data(alias))


@router.patch("/entity-aliases/{alias_id}", response_model=AliasResponse)
async def update_alias(
    request: Request,
    alias_id: UUID,
    payload: AliasRequest,
) -> AliasResponse:
    alias = await _setup(request).update_alias(
        alias_id,
        GeoEntityAliasCommand(**payload.model_dump()),
    )
    if alias is None:
        raise HTTPException(status_code=404, detail="alias not found")
    return AliasResponse(**_record_data(alias))


@router.delete("/entity-aliases/{alias_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_alias(request: Request, alias_id: UUID) -> None:
    if not await _setup(request).delete_alias(alias_id):
        raise HTTPException(status_code=404, detail="alias not found")


@router.get("/projects/{project_id}/topics", response_model=PageResponse)
async def list_topics(request: Request, project_id: UUID) -> PageResponse:
    items = await _setup(request).list_topics(project_id)
    return PageResponse(
        items=[TopicResponse(**_record_data(item)) for item in items],
        total=len(items),
    )


@router.post("/projects/{project_id}/topics", response_model=TopicResponse, status_code=201)
async def create_topic(
    request: Request,
    project_id: UUID,
    payload: TopicRequest,
) -> TopicResponse:
    topic = await _setup(request).create_topic(
        project_id,
        GeoTopicCommand(**payload.model_dump()),
    )
    if topic is None:
        raise HTTPException(status_code=404, detail="project not found")
    return TopicResponse(**_record_data(topic))


@router.patch("/topics/{topic_id}", response_model=TopicResponse)
async def update_topic(
    request: Request,
    topic_id: UUID,
    payload: TopicRequest,
) -> TopicResponse:
    topic = await _setup(request).update_topic(
        topic_id,
        GeoTopicCommand(**payload.model_dump()),
    )
    if topic is None:
        raise HTTPException(status_code=404, detail="topic not found")
    return TopicResponse(**_record_data(topic))


@router.delete("/topics/{topic_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_topic(request: Request, topic_id: UUID) -> None:
    if not await _setup(request).delete_topic(topic_id):
        raise HTTPException(status_code=404, detail="topic not found")


@router.get("/projects/{project_id}/queries", response_model=PageResponse)
async def list_queries(request: Request, project_id: UUID) -> PageResponse:
    items = await _setup(request).list_queries(project_id)
    return PageResponse(
        items=[QueryResponse(**_record_data(item)) for item in items],
        total=len(items),
    )


@router.post("/projects/{project_id}/queries", response_model=QueryResponse, status_code=201)
async def create_query(
    request: Request,
    project_id: UUID,
    payload: QueryRequest,
) -> QueryResponse:
    query = await _setup(request).create_query(
        project_id,
        GeoQueryCommand(**payload.model_dump()),
    )
    if query is None:
        raise HTTPException(status_code=404, detail="project not found")
    return QueryResponse(**_record_data(query))


@router.get("/queries/{query_id}", response_model=QueryResponse)
async def get_query(request: Request, query_id: UUID) -> QueryResponse:
    query = await _setup(request).get_query(query_id)
    if query is None:
        raise HTTPException(status_code=404, detail="query not found")
    return QueryResponse(**_record_data(query))


@router.patch("/queries/{query_id}", response_model=QueryResponse)
async def update_query(
    request: Request,
    query_id: UUID,
    payload: QueryRequest,
) -> QueryResponse:
    query = await _setup(request).update_query(
        query_id,
        GeoQueryCommand(**payload.model_dump()),
    )
    if query is None:
        raise HTTPException(status_code=404, detail="query not found")
    return QueryResponse(**_record_data(query))


@router.delete("/queries/{query_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_query(request: Request, query_id: UUID) -> None:
    if not await _setup(request).delete_query(query_id):
        raise HTTPException(status_code=404, detail="query not found")


@router.get("/queries/{query_id}/platforms", response_model=PageResponse)
async def list_query_platforms(request: Request, query_id: UUID) -> PageResponse:
    items = await _setup(request).list_query_platforms(query_id)
    return PageResponse(
        items=[QueryPlatformResponse(**_record_data(item)) for item in items],
        total=len(items),
    )


@router.put("/queries/{query_id}/platforms", response_model=PageResponse)
async def replace_query_platforms(
    request: Request,
    query_id: UUID,
    payload: list[QueryPlatformRequest],
) -> PageResponse:
    items = await _setup(request).replace_query_platforms(
        query_id,
        [GeoQueryPlatformCommand(**item.model_dump()) for item in payload],
    )
    if items is None:
        raise HTTPException(status_code=404, detail="query not found")
    return PageResponse(
        items=[QueryPlatformResponse(**_record_data(item)) for item in items],
        total=len(items),
    )


@router.get("/queries/{query_id}/schedules", response_model=PageResponse)
async def list_schedules(request: Request, query_id: UUID) -> PageResponse:
    items = await _setup(request).list_schedules(query_id)
    return PageResponse(
        items=[ScheduleResponse(**_record_data(item)) for item in items],
        total=len(items),
    )


@router.post("/queries/{query_id}/schedules", response_model=ScheduleResponse, status_code=201)
async def create_schedule(
    request: Request,
    query_id: UUID,
    payload: ScheduleRequest,
) -> ScheduleResponse:
    schedule = await _setup(request).create_schedule(
        query_id,
        GeoQueryScheduleCommand(**payload.model_dump()),
    )
    if schedule is None:
        raise HTTPException(status_code=404, detail="query not found")
    return ScheduleResponse(**_record_data(schedule))


@router.patch("/schedules/{schedule_id}", response_model=ScheduleResponse)
async def update_schedule(
    request: Request,
    schedule_id: UUID,
    payload: ScheduleRequest,
) -> ScheduleResponse:
    schedule = await _setup(request).update_schedule(
        schedule_id,
        GeoQueryScheduleCommand(**payload.model_dump()),
    )
    if schedule is None:
        raise HTTPException(status_code=404, detail="schedule not found")
    return ScheduleResponse(**_record_data(schedule))


@router.delete("/schedules/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_schedule(request: Request, schedule_id: UUID) -> None:
    if not await _setup(request).delete_schedule(schedule_id):
        raise HTTPException(status_code=404, detail="schedule not found")


@router.post("/queries/{query_id}/jobs", response_model=JobResponse, status_code=201)
async def create_job(
    request: Request,
    query_id: UUID,
    payload: CreateJobRequest,
) -> JobResponse:
    job = await _jobs(request).create_job(
        query_id,
        CreateQueryRunJobCommand(**payload.model_dump()),
    )
    if job is None:
        raise HTTPException(status_code=404, detail="query not found")
    return JobResponse(**_job_data(job))


@router.get("/projects/{project_id}/jobs", response_model=PageResponse)
async def list_jobs(request: Request, project_id: UUID) -> PageResponse:
    jobs = await _jobs(request).list_jobs(project_id)
    return PageResponse(
        items=[JobResponse(**_job_data(job)) for job in jobs],
        total=len(jobs),
    )


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job(request: Request, job_id: UUID) -> JobResponse:
    job = await _jobs(request).get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    return JobResponse(**_job_data(job))


@router.post("/jobs/{job_id}/dispatch", response_model=JobResponse)
async def dispatch_job(request: Request, job_id: UUID) -> JobResponse:
    job = await _jobs(request).get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="message publisher adapter is not configured",
    )


@router.post("/jobs/{job_id}/cancel", response_model=JobResponse)
async def cancel_job(request: Request, job_id: UUID) -> JobResponse:
    job = await _jobs(request).cancel_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    return JobResponse(**_job_data(job))


@router.post("/jobs/{job_id}/external-callbacks", response_model=JobResponse)
async def receive_external_callback(
    request: Request,
    job_id: UUID,
    payload: ExternalCallbackRequest,
) -> JobResponse:
    callback = ExternalRunCallback(job_id=job_id, **payload.model_dump())
    try:
        job = await _jobs(request).apply_external_callback(callback)
    except KeyError:
        raise HTTPException(status_code=404, detail="job not found") from None
    return JobResponse(**_job_data(job))
