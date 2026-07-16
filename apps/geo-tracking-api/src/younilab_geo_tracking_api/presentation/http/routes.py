from fastapi import APIRouter, Request
from younilab_geo_tracking_application import (
    ProjectInspectionCommand,
    ProjectInspectionResult,
    ProjectSuggestionCommand,
    ProjectSuggestionsResult,
    QueryGenerationCommand,
    QueryGenerationResult,
    QueryResearchCommand,
    QueryResearchResult,
    RunRequestCommand,
    RunRequestResult,
)

router = APIRouter(prefix="/api/v1/geo-tracking", tags=["geo-tracking"])


@router.get("/dummy-project")
async def dummy_project() -> dict[str, object]:
    return {
        "brandName": "Shan Hua Plastic Industrial Co., Ltd. (SHPI)",
        "competitorBrands": ["CEJN Industrial Corporation"],
        "keywords": ["pneumatic tubing", "air brake hose"],
        "region": "US",
        "marketType": "b2b_procurement",
        "topics": [
            {
                "name": "品牌型",
                "description": "聚焦自身品牌、競品品牌、品牌比較與品牌信任度。",
            },
            {
                "name": "產品型",
                "description": "聚焦產品用途、規格、適用情境、品質與替代方案。",
            },
            {
                "name": "採購評估",
                "description": "聚焦供應商條件、交期、認證、外銷能力與採購風險。",
            },
        ],
        "topicNames": ["品牌型", "產品型", "採購評估"],
    }


@router.post("/query-research", response_model=QueryResearchResult)
async def research_queries(
    payload: QueryResearchCommand,
    request: Request,
) -> QueryResearchResult:
    return await request.app.state.query_research.research(payload)


@router.post("/query-generation", response_model=QueryGenerationResult)
async def generate_queries(
    payload: QueryGenerationCommand,
    request: Request,
) -> QueryGenerationResult:
    return await request.app.state.query_generation.generate(payload)


@router.post(
    "/project-discovery/inspection",
    response_model=ProjectInspectionResult,
)
async def inspect_project(
    payload: ProjectInspectionCommand,
    request: Request,
) -> ProjectInspectionResult:
    return await request.app.state.project_discovery.inspect(payload)


@router.post(
    "/project-discovery/suggestions",
    response_model=ProjectSuggestionsResult,
)
async def suggest_project_inputs(
    payload: ProjectSuggestionCommand,
    request: Request,
) -> ProjectSuggestionsResult:
    return await request.app.state.project_discovery.suggest(payload)


@router.post("/run-requests", response_model=RunRequestResult)
async def create_run_request(
    payload: RunRequestCommand,
    request: Request,
) -> RunRequestResult:
    return await request.app.state.run_engine.run(payload)
