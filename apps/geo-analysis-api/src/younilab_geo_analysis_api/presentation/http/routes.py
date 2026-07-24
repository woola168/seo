from dataclasses import asdict
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request, Response, status

from younilab_geo_analysis_api.presentation.http.dependencies import bearer_token
from younilab_geo_analysis_api.presentation.http.dtos import (
    AliasCollectionRequest,
    AliasCollectionResponse,
    AliasResponse,
    AcceptQueryDraftRequest,
    AiPlatformResponse,
    CreateJobRequest,
    CreateJobResponse,
    DashboardReportResponse,
    EntityRequest,
    EntityResponse,
    ExternalCallbackRequest,
    JobResponse,
    KMindHubWorkspaceMappingRequest,
    KMindHubWorkspaceMappingResponse,
    KMindHubWorkspaceProvisionRequest,
    MarketRequest,
    MarketResponse,
    MetricFormulaResultResponse,
    OverviewReportResponse,
    OverviewResponsePageResponse,
    PageResponse,
    ProblemDetailsResponse,
    ProjectRequest,
    ProjectQuerySettingsRequest,
    ProjectQuerySettingsResponse,
    ProjectResponse,
    ProjectSummaryPageResponse,
    ProjectSummaryResponse,
    ProjectStatusRequest,
    ProjectStatusResponse,
    QueryPlatformRequest,
    QueryPlatformResponse,
    QueryDraftSelectionRequest,
    QueryDraftResponse,
    QueryGenerationRunRequest,
    QueryGenerationRunResponse,
    QueryRequest,
    QueryResearchRunRequest,
    QueryResearchRunResponse,
    QueryResponse,
    RunResultResponse,
    RunResultSemanticAnalysisResponse,
    ScheduleRequest,
    ScheduleResponse,
    TopicRequest,
    TopicResponse,
)
from younilab_seo.geo_analysis.application import (
    AcceptQueryDraftCommand,
    CalculateGeoReportMetrics,
    CreateQueryRunJobCommand,
    DispatchQueryRunJob,
    DispatchQueryRunJobError,
    ExternalRunCallback,
    GeoEntityAliasCommand,
    GeoEntityCommand,
    GeoMarketCommand,
    GeoProjectCommand,
    GeoProjectQuerySettingsCommand,
    GeoProjectStatusCommand,
    GeoQueryCommand,
    GeoQueryPlatformCommand,
    GeoQueryScheduleCommand,
    GeoMetricFormulaQuery,
    GeoMetricFormulaSourceProjectNotFound,
    GeoOverviewQuery,
    GeoTopicCommand,
    GetGeoDashboardReport,
    GetGeoOverviewReport,
    KMindHubWorkspaceMappingCommand,
    KMindHubWorkspaceProvisionCommand,
    ManageQueryPlanning,
    ManageKMindHubWorkspaceMapping,
    QueryDraftSelectionCommand,
    QueryGenerationCommand,
    QueryResearchCommand,
    ManageGeoSetup,
    ManageQueryRunJobs,
    ListGeoOverviewResponses,
    ReceiveExternalRunCallback,
)
from younilab_seo.geo_analysis.application import AuthorizedPrincipal
from younilab_seo.geo_analysis.domain import GeoQueryRunJob

router = APIRouter(prefix="/api/geo", tags=["geo-analysis"])


def _setup(request: Request) -> ManageGeoSetup:
    return request.app.state.manage_geo_setup


def _jobs(request: Request) -> ManageQueryRunJobs:
    return request.app.state.manage_query_run_jobs


def _planning(request: Request) -> ManageQueryPlanning:
    return request.app.state.manage_query_planning


def _kmindhub_workspace(request: Request) -> ManageKMindHubWorkspaceMapping:
    return request.app.state.manage_kmindhub_workspace_mapping


def _report_metrics(request: Request) -> CalculateGeoReportMetrics:
    return request.app.state.calculate_geo_report_metrics


def _dashboard_report(request: Request) -> GetGeoDashboardReport:
    return request.app.state.get_geo_dashboard_report


def _overview_report(request: Request) -> GetGeoOverviewReport:
    return request.app.state.get_geo_overview_report


def _overview_responses(request: Request) -> ListGeoOverviewResponses:
    return request.app.state.list_geo_overview_responses


def _dispatcher(request: Request) -> DispatchQueryRunJob | None:
    return request.app.state.dispatch_query_run_job


def _callback_receiver(request: Request) -> ReceiveExternalRunCallback:
    return request.app.state.receive_external_run_callback


async def _principal(request: Request, permission: str) -> AuthorizedPrincipal:
    token = await bearer_token(request.headers.get("authorization"))
    return await request.app.state.geo_authorizer.require(token, permission)


async def _access_token(request: Request) -> str:
    return await bearer_token(request.headers.get("authorization"))


def _record_data(record) -> dict:
    return record.model_dump()


def _job_data(job: GeoQueryRunJob) -> dict:
    data = asdict(job)
    data["status"] = job.status.value
    return data


def _run_result_data(record) -> dict:
    return record.model_dump()


def _planning_data(record) -> dict:
    return record.model_dump()


@router.get(
    "/integrations/kmindhub/workspace",
    response_model=KMindHubWorkspaceMappingResponse,
)
async def get_kmindhub_workspace_mapping(
    request: Request,
) -> KMindHubWorkspaceMappingResponse:
    principal = await _principal(request, "geo.projects.read")
    mapping = await _kmindhub_workspace(request).get_mapping(principal.tenant_id)
    if mapping is None:
        raise HTTPException(status_code=404, detail="KMindHub workspace mapping not found")
    return KMindHubWorkspaceMappingResponse(**_record_data(mapping))


@router.put(
    "/integrations/kmindhub/workspace",
    response_model=KMindHubWorkspaceMappingResponse,
)
async def bind_kmindhub_workspace_mapping(
    request: Request,
    payload: KMindHubWorkspaceMappingRequest,
) -> KMindHubWorkspaceMappingResponse:
    principal = await _principal(request, "geo.projects.update")
    try:
        mapping = await _kmindhub_workspace(request).bind_workspace(
            principal.tenant_id,
            KMindHubWorkspaceMappingCommand(**payload.model_dump()),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    return KMindHubWorkspaceMappingResponse(**_record_data(mapping))


@router.post(
    "/integrations/kmindhub/workspace/provision",
    response_model=KMindHubWorkspaceMappingResponse,
    status_code=201,
)
async def provision_kmindhub_workspace_mapping(
    request: Request,
    payload: KMindHubWorkspaceProvisionRequest,
) -> KMindHubWorkspaceMappingResponse:
    principal = await _principal(request, "geo.projects.update")
    try:
        mapping = await _kmindhub_workspace(request).provision_workspace(
            principal.tenant_id,
            KMindHubWorkspaceProvisionCommand(**payload.model_dump()),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    return KMindHubWorkspaceMappingResponse(**_record_data(mapping))


@router.get(
    "/projects",
    response_model=ProjectSummaryPageResponse,
    responses={
        401: {"model": ProblemDetailsResponse},
        403: {"model": ProblemDetailsResponse},
        422: {"model": ProblemDetailsResponse},
    },
)
async def list_projects(
    request: Request,
    customer_id: UUID | None = Query(default=None, alias="customerId"),
) -> ProjectSummaryPageResponse:
    principal = await _principal(request, "geo.projects.read")
    token = await _access_token(request)
    items = await _setup(request).list_project_summaries(
        principal,
        customer_id,
        access_token=token,
    )
    return ProjectSummaryPageResponse(
        items=[ProjectSummaryResponse(**_record_data(item)) for item in items],
        total=len(items),
    )


@router.post("/projects", response_model=ProjectResponse, status_code=201)
async def create_project(request: Request, payload: ProjectRequest) -> ProjectResponse:
    principal = await _principal(request, "geo.projects.create")
    token = await _access_token(request)
    project = await _setup(request).create_project(
        GeoProjectCommand(tenant_id=principal.tenant_id, **payload.model_dump()),
        principal,
        access_token=token,
    )
    return ProjectResponse(**_record_data(project))


@router.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(request: Request, project_id: UUID) -> ProjectResponse:
    principal = await _principal(request, "geo.projects.read")
    project = await _setup(request).get_project(principal, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="project not found")
    return ProjectResponse(**_record_data(project))


@router.patch(
    "/projects/{project_id}/status",
    response_model=ProjectStatusResponse,
    responses={
        401: {"model": ProblemDetailsResponse},
        403: {"model": ProblemDetailsResponse},
        404: {"model": ProblemDetailsResponse},
        422: {"model": ProblemDetailsResponse},
    },
)
async def update_project_status(
    request: Request,
    project_id: UUID,
    payload: ProjectStatusRequest,
) -> ProjectStatusResponse:
    principal = await _principal(request, "geo.projects.update")
    project = await _setup(request).update_project_status(
        principal,
        project_id,
        GeoProjectStatusCommand(**payload.model_dump()),
    )
    if project is None:
        raise HTTPException(status_code=404, detail="project not found")
    return ProjectStatusResponse(
        project_id=project.id,
        status=project.status,
        updated_at=project.updated_at,
    )


@router.get(
    "/projects/{project_id}/query-settings",
    response_model=ProjectQuerySettingsResponse,
    responses={
        401: {"model": ProblemDetailsResponse},
        403: {"model": ProblemDetailsResponse},
        404: {"model": ProblemDetailsResponse},
        422: {"model": ProblemDetailsResponse},
    },
)
async def get_project_query_settings(
    request: Request,
    project_id: UUID,
) -> ProjectQuerySettingsResponse:
    principal = await _principal(request, "geo.projects.read")
    settings = await _setup(request).get_project_query_settings(principal, project_id)
    if settings is None:
        raise HTTPException(status_code=404, detail="project query settings not found")
    return ProjectQuerySettingsResponse(**_record_data(settings))


@router.put(
    "/projects/{project_id}/query-settings",
    response_model=ProjectQuerySettingsResponse,
    responses={
        401: {"model": ProblemDetailsResponse},
        403: {"model": ProblemDetailsResponse},
        404: {"model": ProblemDetailsResponse},
        422: {"model": ProblemDetailsResponse},
    },
)
async def replace_project_query_settings(
    request: Request,
    project_id: UUID,
    payload: ProjectQuerySettingsRequest,
) -> ProjectQuerySettingsResponse:
    principal = await _principal(request, "geo.projects.update")
    settings = await _setup(request).replace_project_query_settings(
        principal,
        project_id,
        GeoProjectQuerySettingsCommand(**payload.model_dump()),
    )
    if settings is None:
        raise HTTPException(status_code=404, detail="project not found")
    return ProjectQuerySettingsResponse(**_record_data(settings))


@router.get(
    "/projects/{project_id}/metrics",
    response_model=MetricFormulaResultResponse,
)
async def get_project_metrics(
    request: Request,
    project_id: UUID,
    period_start: datetime = Query(alias="periodStart"),
    period_end: datetime = Query(alias="periodEnd"),
    comparison_start: datetime | None = Query(default=None, alias="comparisonStart"),
    comparison_end: datetime | None = Query(default=None, alias="comparisonEnd"),
    query_id: UUID | None = Query(default=None, alias="queryId"),
    topic_id: UUID | None = Query(default=None, alias="topicId"),
    provider: str | None = None,
    region: str | None = None,
    language: str | None = None,
) -> MetricFormulaResultResponse:
    principal = await _principal(request, "geo.projects.read")
    project = await _setup(request).get_project(principal, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="project not found")
    try:
        metrics_query = GeoMetricFormulaQuery(
            period_start=period_start,
            period_end=period_end,
            comparison_start=comparison_start,
            comparison_end=comparison_end,
            query_id=query_id,
            topic_id=topic_id,
            provider=provider,
            region=region,
            language=language,
        )
        result = await _report_metrics(request).execute(
            principal.tenant_id,
            project_id,
            metrics_query,
        )
    except GeoMetricFormulaSourceProjectNotFound:
        raise HTTPException(status_code=404, detail="project not found") from None
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    return MetricFormulaResultResponse(**result.model_dump())


@router.get(
    "/projects/{project_id}/reports/dashboard",
    response_model=DashboardReportResponse,
)
async def get_project_dashboard_report(
    request: Request,
    project_id: UUID,
    period_start: datetime = Query(alias="periodStart"),
    period_end: datetime = Query(alias="periodEnd"),
    comparison_start: datetime | None = Query(default=None, alias="comparisonStart"),
    comparison_end: datetime | None = Query(default=None, alias="comparisonEnd"),
    query_id: UUID | None = Query(default=None, alias="queryId"),
    topic_id: UUID | None = Query(default=None, alias="topicId"),
    provider: str | None = None,
    region: str | None = None,
    language: str | None = None,
) -> DashboardReportResponse:
    principal = await _principal(request, "geo.projects.read")
    project = await _setup(request).get_project(principal, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="project not found")
    try:
        metrics_query = GeoMetricFormulaQuery(
            period_start=period_start,
            period_end=period_end,
            comparison_start=comparison_start,
            comparison_end=comparison_end,
            query_id=query_id,
            topic_id=topic_id,
            provider=provider,
            region=region,
            language=language,
        )
        result = await _dashboard_report(request).execute(
            principal.tenant_id,
            project_id,
            metrics_query,
        )
    except GeoMetricFormulaSourceProjectNotFound:
        raise HTTPException(status_code=404, detail="project not found") from None
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    return DashboardReportResponse(**result.model_dump())


@router.get(
    "/projects/{project_id}/reports/overview",
    response_model=OverviewReportResponse,
)
async def get_project_overview_report(
    request: Request,
    project_id: UUID,
    period_start: datetime = Query(alias="periodStart"),
    period_end: datetime = Query(alias="periodEnd"),
    topic_ids: list[UUID] = Query(default=[], alias="topicIds"),
    providers: list[str] = Query(default=[]),
    region: str | None = None,
    metadata_industry: list[str] = Query(default=[], alias="metadataIndustry"),
    metadata_type: list[str] = Query(default=[], alias="metadataType"),
    time_zone: str = Query(default="Asia/Taipei", alias="timeZone"),
) -> OverviewReportResponse:
    principal = await _principal(request, "geo.projects.read")
    if await _setup(request).get_project(principal, project_id) is None:
        raise HTTPException(status_code=404, detail="project not found")
    try:
        result = await _overview_report(request).execute(
            principal.tenant_id,
            project_id,
            GeoOverviewQuery(
                period_start=period_start,
                period_end=period_end,
                topic_ids=topic_ids,
                providers=providers,
                region=region,
                metadata_industry=metadata_industry,
                metadata_type=metadata_type,
                time_zone=time_zone,
            ),
        )
    except GeoMetricFormulaSourceProjectNotFound:
        raise HTTPException(status_code=404, detail="project not found") from None
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    return OverviewReportResponse(**result.model_dump())


@router.get(
    "/projects/{project_id}/reports/overview/responses",
    response_model=OverviewResponsePageResponse,
)
async def list_project_overview_responses(
    request: Request,
    project_id: UUID,
    period_start: datetime = Query(alias="periodStart"),
    period_end: datetime = Query(alias="periodEnd"),
    topic_ids: list[UUID] = Query(default=[], alias="topicIds"),
    providers: list[str] = Query(default=[]),
    region: str | None = None,
    metadata_industry: list[str] = Query(default=[], alias="metadataIndustry"),
    metadata_type: list[str] = Query(default=[], alias="metadataType"),
    time_zone: str = Query(default="Asia/Taipei", alias="timeZone"),
    query_id: UUID | None = Query(default=None, alias="queryId"),
    mention_status: str = Query(default="all", alias="mentionStatus"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100, alias="pageSize"),
) -> OverviewResponsePageResponse:
    principal = await _principal(request, "geo.projects.read")
    if await _setup(request).get_project(principal, project_id) is None:
        raise HTTPException(status_code=404, detail="project not found")
    try:
        result = await _overview_responses(request).execute(
            principal.tenant_id,
            project_id,
            GeoOverviewQuery(
                period_start=period_start,
                period_end=period_end,
                topic_ids=topic_ids,
                providers=providers,
                region=region,
                metadata_industry=metadata_industry,
                metadata_type=metadata_type,
                time_zone=time_zone,
            ),
            query_id=query_id,
            mention_status=mention_status,
            page=page,
            page_size=page_size,
        )
    except GeoMetricFormulaSourceProjectNotFound:
        raise HTTPException(status_code=404, detail="project not found") from None
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    return OverviewResponsePageResponse(**result.model_dump())


@router.patch("/projects/{project_id}", response_model=ProjectResponse)
async def update_project(
    request: Request,
    project_id: UUID,
    payload: ProjectRequest,
) -> ProjectResponse:
    principal = await _principal(request, "geo.projects.update")
    token = await _access_token(request)
    project = await _setup(request).update_project(
        principal,
        project_id,
        GeoProjectCommand(tenant_id=principal.tenant_id, **payload.model_dump()),
        access_token=token,
    )
    if project is None:
        raise HTTPException(status_code=404, detail="project not found")
    return ProjectResponse(**_record_data(project))


@router.delete("/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(request: Request, project_id: UUID) -> None:
    principal = await _principal(request, "geo.projects.delete")
    if not await _setup(request).delete_project(principal, project_id):
        raise HTTPException(status_code=404, detail="project not found")


@router.get("/projects/{project_id}/markets", response_model=PageResponse)
async def list_markets(request: Request, project_id: UUID) -> PageResponse:
    principal = await _principal(request, "geo.projects.read")
    items = await _setup(request).list_markets(principal, project_id)
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
    principal = await _principal(request, "geo.projects.update")
    market = await _setup(request).create_market(
        principal,
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
    principal = await _principal(request, "geo.projects.update")
    market = await _setup(request).update_market(
        principal,
        market_id,
        GeoMarketCommand(**payload.model_dump()),
    )
    if market is None:
        raise HTTPException(status_code=404, detail="market not found")
    return MarketResponse(**_record_data(market))


@router.delete("/markets/{market_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_market(request: Request, market_id: UUID) -> None:
    principal = await _principal(request, "geo.projects.update")
    if not await _setup(request).delete_market(principal, market_id):
        raise HTTPException(status_code=404, detail="market not found")


@router.get("/projects/{project_id}/entities", response_model=PageResponse)
async def list_entities(request: Request, project_id: UUID) -> PageResponse:
    principal = await _principal(request, "geo.projects.read")
    items = await _setup(request).list_entities(principal, project_id)
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
    principal = await _principal(request, "geo.projects.update")
    entity = await _setup(request).create_entity(
        principal,
        project_id,
        GeoEntityCommand(**payload.model_dump()),
    )
    if entity is None:
        raise HTTPException(status_code=404, detail="project not found")
    return EntityResponse(**_record_data(entity))


@router.get("/projects/{project_id}/entity-aliases", response_model=PageResponse)
async def list_project_aliases(request: Request, project_id: UUID) -> PageResponse:
    principal = await _principal(request, "geo.projects.read")
    items = await _setup(request).list_project_aliases(principal, project_id)
    return PageResponse(
        items=[AliasResponse(**_record_data(item)) for item in items],
        total=len(items),
    )


@router.get("/entities/{entity_id}", response_model=EntityResponse)
async def get_entity(request: Request, entity_id: UUID) -> EntityResponse:
    principal = await _principal(request, "geo.projects.read")
    entity = await _setup(request).get_entity(principal, entity_id)
    if entity is None:
        raise HTTPException(status_code=404, detail="entity not found")
    return EntityResponse(**_record_data(entity))


@router.patch("/entities/{entity_id}", response_model=EntityResponse)
async def update_entity(
    request: Request,
    entity_id: UUID,
    payload: EntityRequest,
) -> EntityResponse:
    principal = await _principal(request, "geo.projects.update")
    entity = await _setup(request).update_entity(
        principal,
        entity_id,
        GeoEntityCommand(**payload.model_dump()),
    )
    if entity is None:
        raise HTTPException(status_code=404, detail="entity not found")
    return EntityResponse(**_record_data(entity))


@router.delete("/entities/{entity_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_entity(request: Request, entity_id: UUID) -> None:
    principal = await _principal(request, "geo.projects.update")
    if not await _setup(request).delete_entity(principal, entity_id):
        raise HTTPException(status_code=404, detail="entity not found")


@router.get(
    "/entities/{entity_id}/aliases",
    response_model=AliasCollectionResponse,
    responses={
        401: {"model": ProblemDetailsResponse},
        403: {"model": ProblemDetailsResponse},
        404: {"model": ProblemDetailsResponse},
        422: {"model": ProblemDetailsResponse},
    },
)
async def list_aliases(request: Request, entity_id: UUID) -> AliasCollectionResponse:
    principal = await _principal(request, "geo.projects.read")
    items = await _setup(request).list_aliases(principal, entity_id)
    if items is None:
        raise HTTPException(status_code=404, detail="entity not found")
    return AliasCollectionResponse(
        items=[AliasResponse(**_record_data(item)) for item in items],
        total=len(items),
    )


@router.put(
    "/entities/{entity_id}/aliases",
    response_model=AliasCollectionResponse,
    responses={
        401: {"model": ProblemDetailsResponse},
        403: {"model": ProblemDetailsResponse},
        404: {"model": ProblemDetailsResponse},
        422: {"model": ProblemDetailsResponse},
    },
)
async def replace_aliases(
    request: Request,
    entity_id: UUID,
    payload: AliasCollectionRequest,
) -> AliasCollectionResponse:
    principal = await _principal(request, "geo.projects.update")
    aliases = await _setup(request).replace_aliases(
        principal,
        entity_id,
        [GeoEntityAliasCommand(**item.model_dump()) for item in payload.items],
    )
    if aliases is None:
        raise HTTPException(status_code=404, detail="entity not found")
    return AliasCollectionResponse(
        items=[AliasResponse(**_record_data(alias)) for alias in aliases],
        total=len(aliases),
    )


@router.get("/projects/{project_id}/topics", response_model=PageResponse)
async def list_topics(request: Request, project_id: UUID) -> PageResponse:
    principal = await _principal(request, "geo.projects.read")
    items = await _setup(request).list_topics(principal, project_id)
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
    principal = await _principal(request, "geo.projects.update")
    topic = await _setup(request).create_topic(
        principal,
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
    principal = await _principal(request, "geo.projects.update")
    topic = await _setup(request).update_topic(
        principal,
        topic_id,
        GeoTopicCommand(**payload.model_dump()),
    )
    if topic is None:
        raise HTTPException(status_code=404, detail="topic not found")
    return TopicResponse(**_record_data(topic))


@router.delete("/topics/{topic_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_topic(request: Request, topic_id: UUID) -> None:
    principal = await _principal(request, "geo.projects.update")
    if not await _setup(request).delete_topic(principal, topic_id):
        raise HTTPException(status_code=404, detail="topic not found")


@router.get("/projects/{project_id}/queries", response_model=PageResponse)
async def list_queries(request: Request, project_id: UUID) -> PageResponse:
    principal = await _principal(request, "geo.projects.read")
    items = await _setup(request).list_queries(principal, project_id)
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
    principal = await _principal(request, "geo.queries.manage")
    query = await _setup(request).create_query(
        principal,
        project_id,
        GeoQueryCommand(**payload.model_dump()),
    )
    if query is None:
        raise HTTPException(status_code=404, detail="project not found")
    return QueryResponse(**_record_data(query))


@router.get("/queries/{query_id}", response_model=QueryResponse)
async def get_query(request: Request, query_id: UUID) -> QueryResponse:
    principal = await _principal(request, "geo.projects.read")
    query = await _setup(request).get_query(principal, query_id)
    if query is None:
        raise HTTPException(status_code=404, detail="query not found")
    return QueryResponse(**_record_data(query))


@router.patch("/queries/{query_id}", response_model=QueryResponse)
async def update_query(
    request: Request,
    query_id: UUID,
    payload: QueryRequest,
) -> QueryResponse:
    principal = await _principal(request, "geo.queries.manage")
    query = await _setup(request).update_query(
        principal,
        query_id,
        GeoQueryCommand(**payload.model_dump()),
    )
    if query is None:
        raise HTTPException(status_code=404, detail="query not found")
    return QueryResponse(**_record_data(query))


@router.delete("/queries/{query_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_query(request: Request, query_id: UUID) -> None:
    principal = await _principal(request, "geo.queries.manage")
    if not await _setup(request).delete_query(principal, query_id):
        raise HTTPException(status_code=404, detail="query not found")


@router.post(
    "/projects/{project_id}/query-research-runs",
    response_model=QueryResearchRunResponse,
    status_code=201,
)
async def run_query_research(
    request: Request,
    project_id: UUID,
    payload: QueryResearchRunRequest,
) -> QueryResearchRunResponse:
    principal = await _principal(request, "geo.queries.manage")
    run = await _planning(request).run_query_research(
        principal,
        project_id,
        QueryResearchCommand(**payload.model_dump()),
    )
    if run is None:
        raise HTTPException(status_code=404, detail="project not found")
    return QueryResearchRunResponse(**_planning_data(run))


@router.get("/projects/{project_id}/query-research-runs", response_model=PageResponse)
async def list_query_research_runs(request: Request, project_id: UUID) -> PageResponse:
    principal = await _principal(request, "geo.projects.read")
    items = await _planning(request).list_query_research_runs(
        principal,
        project_id,
    )
    return PageResponse(
        items=[QueryResearchRunResponse(**_planning_data(item)) for item in items],
        total=len(items),
    )


@router.get(
    "/query-research-runs/{run_id}",
    response_model=QueryResearchRunResponse,
)
async def get_query_research_run(
    request: Request,
    run_id: UUID,
) -> QueryResearchRunResponse:
    principal = await _principal(request, "geo.projects.read")
    run = await _planning(request).get_query_research_run(principal, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="query research run not found")
    return QueryResearchRunResponse(**_planning_data(run))


@router.post(
    "/projects/{project_id}/query-generation-runs",
    response_model=QueryGenerationRunResponse,
    status_code=201,
)
async def run_query_generation(
    request: Request,
    project_id: UUID,
    payload: QueryGenerationRunRequest,
) -> QueryGenerationRunResponse:
    principal = await _principal(request, "geo.queries.manage")
    run = await _planning(request).run_query_generation(
        principal,
        project_id,
        QueryGenerationCommand(**payload.model_dump()),
    )
    if run is None:
        raise HTTPException(status_code=404, detail="project not found")
    return QueryGenerationRunResponse(**_planning_data(run))


@router.get("/projects/{project_id}/query-generation-runs", response_model=PageResponse)
async def list_query_generation_runs(request: Request, project_id: UUID) -> PageResponse:
    principal = await _principal(request, "geo.projects.read")
    items = await _planning(request).list_query_generation_runs(
        principal,
        project_id,
    )
    return PageResponse(
        items=[QueryGenerationRunResponse(**_planning_data(item)) for item in items],
        total=len(items),
    )


@router.get(
    "/query-generation-runs/{run_id}",
    response_model=QueryGenerationRunResponse,
)
async def get_query_generation_run(
    request: Request,
    run_id: UUID,
) -> QueryGenerationRunResponse:
    principal = await _principal(request, "geo.projects.read")
    run = await _planning(request).get_query_generation_run(principal, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="query generation run not found")
    return QueryGenerationRunResponse(**_planning_data(run))


@router.patch("/query-drafts/{draft_id}/selection", response_model=QueryDraftResponse)
async def update_query_draft_selection(
    request: Request,
    draft_id: UUID,
    payload: QueryDraftSelectionRequest,
) -> QueryDraftResponse:
    principal = await _principal(request, "geo.queries.manage")
    try:
        draft = await _planning(request).update_query_draft_selection(
            principal,
            draft_id,
            QueryDraftSelectionCommand(**payload.model_dump()),
        )
    except ValueError as exc:
        status_code = 409 if str(exc) == "query draft already accepted" else 422
        raise HTTPException(status_code=status_code, detail=str(exc)) from None
    if draft is None:
        raise HTTPException(status_code=404, detail="query draft not found")
    return QueryDraftResponse(**_planning_data(draft))


@router.post("/query-drafts/{draft_id}/accept", response_model=QueryResponse)
async def accept_query_draft(
    request: Request,
    draft_id: UUID,
    payload: AcceptQueryDraftRequest,
) -> QueryResponse:
    principal = await _principal(request, "geo.queries.manage")
    try:
        query = await _planning(request).accept_query_draft(
            principal,
            draft_id,
            AcceptQueryDraftCommand(**payload.model_dump()),
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None
    if query is None:
        raise HTTPException(status_code=404, detail="query draft not found")
    return QueryResponse(**_planning_data(query))


@router.get("/platforms", response_model=PageResponse)
async def list_ai_platforms(request: Request) -> PageResponse:
    await _principal(request, "geo.projects.read")
    items = await _setup(request).list_ai_platforms()
    return PageResponse(
        items=[AiPlatformResponse(**_record_data(item)) for item in items],
        total=len(items),
    )


@router.get("/queries/{query_id}/platforms", response_model=PageResponse)
async def list_query_platforms(request: Request, query_id: UUID) -> PageResponse:
    principal = await _principal(request, "geo.projects.read")
    items = await _setup(request).list_query_platforms(principal, query_id)
    return PageResponse(
        items=[QueryPlatformResponse(**_record_data(item)) for item in items],
        total=len(items),
    )


@router.get("/projects/{project_id}/query-platforms", response_model=PageResponse)
async def list_project_query_platforms(
    request: Request,
    project_id: UUID,
) -> PageResponse:
    principal = await _principal(request, "geo.projects.read")
    items = await _setup(request).list_project_query_platforms(principal, project_id)
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
    principal = await _principal(request, "geo.queries.manage")
    items = await _setup(request).replace_query_platforms(
        principal,
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
    principal = await _principal(request, "geo.projects.read")
    items = await _setup(request).list_schedules(principal, query_id)
    return PageResponse(
        items=[ScheduleResponse(**_record_data(item)) for item in items],
        total=len(items),
    )


@router.get("/projects/{project_id}/schedules", response_model=PageResponse)
async def list_project_schedules(request: Request, project_id: UUID) -> PageResponse:
    principal = await _principal(request, "geo.projects.read")
    items = await _setup(request).list_project_schedules(principal, project_id)
    return PageResponse(
        items=[ScheduleResponse(**_record_data(item)) for item in items],
        total=len(items),
    )


@router.post(
    "/queries/{query_id}/schedules",
    response_model=ScheduleResponse,
    status_code=201,
)
async def create_schedule(
    request: Request,
    query_id: UUID,
    payload: ScheduleRequest,
) -> ScheduleResponse:
    principal = await _principal(request, "geo.queries.manage")
    schedule = await _setup(request).create_schedule(
        principal,
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
    principal = await _principal(request, "geo.queries.manage")
    schedule = await _setup(request).update_schedule(
        principal,
        schedule_id,
        GeoQueryScheduleCommand(**payload.model_dump()),
    )
    if schedule is None:
        raise HTTPException(status_code=404, detail="schedule not found")
    return ScheduleResponse(**_record_data(schedule))


@router.delete("/schedules/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_schedule(request: Request, schedule_id: UUID) -> None:
    principal = await _principal(request, "geo.queries.manage")
    if not await _setup(request).delete_schedule(principal, schedule_id):
        raise HTTPException(status_code=404, detail="schedule not found")


@router.post(
    "/queries/{query_id}/jobs",
    response_model=CreateJobResponse,
    status_code=201,
    responses={200: {"model": CreateJobResponse}},
)
async def create_job(
    request: Request,
    response: Response,
    query_id: UUID,
    payload: CreateJobRequest,
) -> CreateJobResponse:
    principal = await _principal(request, "geo.jobs.run")
    creation = await _jobs(request).create_job(
        principal,
        query_id,
        CreateQueryRunJobCommand(**payload.model_dump()),
    )
    if creation is None:
        raise HTTPException(status_code=404, detail="query not found")
    job, was_created = creation
    response.status_code = status.HTTP_201_CREATED if was_created else status.HTTP_200_OK
    return CreateJobResponse(**_job_data(job), was_created=was_created)


@router.get("/projects/{project_id}/jobs", response_model=PageResponse)
async def list_jobs(request: Request, project_id: UUID) -> PageResponse:
    principal = await _principal(request, "geo.jobs.read")
    jobs = await _jobs(request).list_jobs(principal, project_id)
    return PageResponse(
        items=[JobResponse(**_job_data(job)) for job in jobs],
        total=len(jobs),
    )


@router.get("/projects/{project_id}/run-results", response_model=PageResponse)
async def list_project_run_results(request: Request, project_id: UUID) -> PageResponse:
    principal = await _principal(request, "geo.jobs.read")
    items = await _jobs(request).list_project_run_results(
        principal,
        project_id,
    )
    return PageResponse(
        items=[RunResultResponse(**_run_result_data(item)) for item in items],
        total=len(items),
    )


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job(request: Request, job_id: UUID) -> JobResponse:
    principal = await _principal(request, "geo.jobs.read")
    job = await _jobs(request).get_job(principal, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    return JobResponse(**_job_data(job))


@router.get("/jobs/{job_id}/run-results", response_model=PageResponse)
async def list_job_run_results(request: Request, job_id: UUID) -> PageResponse:
    principal = await _principal(request, "geo.jobs.read")
    job = await _jobs(request).get_job(principal, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    items = await _jobs(request).list_job_run_results(principal, job_id)
    return PageResponse(
        items=[RunResultResponse(**_run_result_data(item)) for item in items],
        total=len(items),
    )


@router.get("/run-results/{result_id}", response_model=RunResultResponse)
async def get_run_result(request: Request, result_id: UUID) -> RunResultResponse:
    principal = await _principal(request, "geo.jobs.read")
    result = await _jobs(request).get_run_result(principal, result_id)
    if result is None:
        raise HTTPException(status_code=404, detail="run result not found")
    return RunResultResponse(**_run_result_data(result))


@router.get(
    "/run-results/{result_id}/semantic-analysis",
    response_model=RunResultSemanticAnalysisResponse,
)
async def get_run_result_semantic_analysis(
    request: Request,
    result_id: UUID,
) -> RunResultSemanticAnalysisResponse:
    principal = await _principal(request, "geo.jobs.read")
    analysis = await _jobs(request).get_run_result_semantic_analysis(
        principal,
        result_id,
    )
    if analysis is None:
        raise HTTPException(status_code=404, detail="semantic analysis not found")
    return RunResultSemanticAnalysisResponse(
        **analysis.model_dump(mode="json", by_alias=False)
    )


@router.post(
    "/run-results/{result_id}/analysis-extractions",
)
async def run_result_analysis_extraction(
    request: Request,
    result_id: UUID,
) -> None:
    await _principal(request, "geo.jobs.run")
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail=(
            "legacy analysis extraction is disabled; dashboard reports use the "
            "worker semantic and citation pipeline"
        ),
    )


@router.post("/jobs/{job_id}/dispatch", response_model=JobResponse)
async def dispatch_job(request: Request, job_id: UUID) -> JobResponse:
    principal = await _principal(request, "geo.jobs.run")
    dispatcher = _dispatcher(request)
    if dispatcher is None:
        job = await _jobs(request).get_job(principal, job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="job not found")
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="message publisher adapter is not configured",
        )
    try:
        job = await dispatcher.execute(
            job_id,
            request.app.state.geo_callback_base_url,
            principal,
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="job not found") from None
    except DispatchQueryRunJobError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None
    return JobResponse(**_job_data(job))


@router.post("/jobs/{job_id}/cancel", response_model=JobResponse)
async def cancel_job(request: Request, job_id: UUID) -> JobResponse:
    principal = await _principal(request, "geo.jobs.cancel")
    job = await _jobs(request).cancel_job(principal, job_id)
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
        job = await _callback_receiver(request).execute(callback)
    except KeyError:
        raise HTTPException(status_code=404, detail="job not found") from None
    return JobResponse(**_job_data(job))
