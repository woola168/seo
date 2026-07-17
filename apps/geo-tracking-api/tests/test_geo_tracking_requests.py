import logging

from fastapi.testclient import TestClient
from younilab_geo_tracking_api import create_app
from younilab_geo_tracking_application import (
    AnswerRequest,
    AnswerResponse,
    ProjectDiscoveryIdentity,
    ProjectDiscoveryInspection,
    ProjectInspectionCommand,
    ProjectSuggestionCommand,
    ProjectSuggestionResult,
    ProviderRequestError,
    QueryDraft,
    QueryGenerationCommand,
    QueryResearchCommand,
    QueryResearchResult,
    Reference,
    TopicInput,
    VerifiedProjectIdentity,
)
from younilab_geo_tracking_domain import ProviderCode
from younilab_geo_tracking_infrastructure import DummyAnswerProvider

TOPIC_DESCRIPTION = "聚焦供應商條件、交期、認證、外銷能力與採購風險。"


def test_local_admin_portal_preflight_is_allowed() -> None:
    response = TestClient(create_app(answer_provider=DummyAnswerProvider())).options(
        "/api/v1/geo-tracking/query-research",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type,authorization",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert response.headers["access-control-allow-credentials"] == "true"
    assert "POST" in response.headers["access-control-allow-methods"]
    assert "Authorization" in response.headers["access-control-allow-headers"]
    assert "Content-Type" in response.headers["access-control-allow-headers"]


class GeminiAnswerStubProvider:
    async def generate_answer(self, request: AnswerRequest) -> AnswerResponse:
        return AnswerResponse(
            provider=ProviderCode.GEMINI,
            surface="Gemini Stub",
            model="gemini-stub",
            raw_response=f"Gemini stub response for: {request.query_text}",
            reference_urls=["https://example.com/reference"],
            references=[
                Reference(
                    url="https://example.com/reference",
                    title="Example reference title",
                )
            ],
        )


class CapturingAnswerStubProvider(GeminiAnswerStubProvider):
    def __init__(self) -> None:
        self.requests: list[AnswerRequest] = []

    async def generate_answer(self, request: AnswerRequest) -> AnswerResponse:
        self.requests.append(request)
        return await super().generate_answer(request)


class GoogleAioAnswerStubProvider:
    async def generate_answer(self, request: AnswerRequest) -> AnswerResponse:
        return AnswerResponse(
            provider=ProviderCode.GOOGLE_AIO,
            surface="Google AI Overview",
            model="serpapi-google-ai-overview",
            raw_response=f"Google AIO stub response for: {request.query_text}",
            reference_urls=["https://example.com/aio-reference"],
            references=[
                Reference(
                    url="https://example.com/aio-reference",
                    title="AIO reference title",
                )
            ],
        )


class GoogleAioNoResultStubProvider:
    async def generate_answer(self, request: AnswerRequest) -> AnswerResponse:
        raise ProviderRequestError("no_google_aio_result")


class GeminiFailingAnswerStubProvider:
    async def generate_answer(self, request: AnswerRequest) -> AnswerResponse:
        raise RuntimeError("vertex unavailable")


class CloseableAnswerStubProvider(GeminiAnswerStubProvider):
    def __init__(self) -> None:
        self.closed = False

    async def close(self) -> None:
        self.closed = True


class GeminiQueryGenerationStubProvider:
    async def generate_drafts(
        self,
        command: QueryGenerationCommand,
    ) -> list[QueryDraft]:
        return [
            QueryDraft(
                attributes={
                    "intent": command.intents[0],
                    "keyword": command.keywords[0],
                    "topicName": command.topics[0].name
                    if command.topics
                    else command.topic_names[0],
                    "topicDescription": command.topics[0].description
                    if command.topics
                    else "",
                    "audience": command.audience,
                    "brandMentionRules": command.brand_mention_rules,
                },
                query="山華塑膠氣動管採購評估需要看哪些供應商條件？",
                keywords=[command.keywords[0]],
            )
        ]


class GeminiQueryResearchStubProvider:
    def __init__(self) -> None:
        self.last_command: QueryResearchCommand | None = None

    async def research(self, command: QueryResearchCommand) -> QueryResearchResult:
        self.last_command = command
        return QueryResearchResult(
            research_context=f"Research context for {command.brand_name}",
            searched_keywords=["山華塑膠 氣動管", "台灣 氣動管 供應商"],
            source_urls=["https://example.com/source"],
        )


class ProjectDiscoveryStubProvider:
    def __init__(self) -> None:
        self.last_inspection_command: ProjectInspectionCommand | None = None
        self.last_suggestion_command: ProjectSuggestionCommand | None = None
        self.last_identity: VerifiedProjectIdentity | None = None
        self.research_calls = 0

    async def inspect_url(
        self,
        command: ProjectInspectionCommand,
    ) -> ProjectDiscoveryInspection:
        self.last_inspection_command = command
        return ProjectDiscoveryInspection(
            retrieval_succeeded=True,
            retrieved_url=command.project_url,
            identity=ProjectDiscoveryIdentity(
                project_name="港香蘭藥廠股份有限公司",
                project_description="位於台灣的中藥製藥公司。",
                project_type="company",
                core_offerings=["科學中藥"],
                sufficient_context=True,
                limitation="",
            ),
        )

    async def research_suggestions(
        self,
        command: ProjectSuggestionCommand,
        identity: VerifiedProjectIdentity,
    ) -> ProjectSuggestionResult:
        self.research_calls += 1
        self.last_suggestion_command = command
        self.last_identity = identity
        return ProjectSuggestionResult(
            search_succeeded=True,
            competitors=["順天堂藥廠", "勝昌製藥"],
            topics=[
                TopicInput(
                    name="科學中藥",
                    description="聚焦製程、品質與產品使用情境。",
                )
            ],
            keywords=["科學中藥", "中藥濃縮粉"],
            references=[Reference(url="https://example.com/source", title="市場來源")],
        )


class InsufficientProjectDiscoveryStubProvider(ProjectDiscoveryStubProvider):
    async def inspect_url(
        self,
        command: ProjectInspectionCommand,
    ) -> ProjectDiscoveryInspection:
        return ProjectDiscoveryInspection(
            retrieval_succeeded=True,
            retrieved_url=command.project_url,
            identity=ProjectDiscoveryIdentity(
                project_name="agent-settings",
                project_description="頁面缺少用途說明。",
                project_type="repository",
                core_offerings=[],
                sufficient_context=False,
                limitation="README 沒有提供專案用途。",
            ),
        )

    async def research_suggestions(
        self,
        command: ProjectSuggestionCommand,
        identity: VerifiedProjectIdentity,
    ) -> ProjectSuggestionResult:
        raise AssertionError("market research must not run")


def _generation_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "seoTaskId": "11111111-1111-4111-8111-111111111111",
        "provider": "dummy",
        "brandName": "Shan Hua Plastic Industrial Co., Ltd. (SHPI)",
        "competitorBrands": ["CEJN Industrial Corporation"],
        "keywords": ["pneumatic tubing"],
        "region": "US",
        "language": "en-US",
        "marketType": "b2b_procurement",
        "topics": [
            {
                "name": "採購評估",
                "description": TOPIC_DESCRIPTION,
            }
        ],
        "topicNames": ["採購評估"],
        "intents": [
            {
                "category": "commercial_investigation",
                "description": "比較供應商、品質、交期與採購風險。",
            }
        ],
        "audience": {
            "name": "B2B 採購",
            "description": "正在評估供應商的採購人員",
        },
        "brandMentionRules": {
            "shouldMentionOwnBrand": True,
            "shouldMentionCompetitor": True,
        },
        "maxQueries": 4,
    }
    payload.update(overrides)
    return payload


def test_query_generation_request_generates_b2b_us_queries() -> None:
    client = TestClient(create_app(answer_provider=DummyAnswerProvider()))

    response = client.post(
        "/api/v1/geo-tracking/query-generation",
        json=_generation_payload(),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["topics"][0]["name"] == "採購評估"
    assert body["topics"][0]["description"] == TOPIC_DESCRIPTION
    assert len(body["queries"]) == 1
    query = body["queries"][0]
    assert query["region"] == "US"
    assert query["language"] == "en-US"
    assert query["marketType"] == "b2b_procurement"
    assert query["keywords"] == ["pneumatic tubing"]
    assert query["isBranded"] is True
    assert query["attributes"]["intent"]["category"] == "commercial_investigation"
    assert query["attributes"]["brandMentionRules"]["shouldMentionOwnBrand"] is True
    assert query["attributes"]["brandMentionRules"]["shouldMentionCompetitor"] is True
    assert query["attributes"]["topicDescription"] == TOPIC_DESCRIPTION
    assert query["metadata"]["topicDescription"] == TOPIC_DESCRIPTION


def test_query_generation_response_does_not_include_seo_task_id() -> None:
    client = TestClient(create_app(answer_provider=DummyAnswerProvider()))
    payload = _generation_payload()
    payload.pop("seoTaskId")

    response = client.post(
        "/api/v1/geo-tracking/query-generation",
        json=payload,
    )

    assert response.status_code == 200
    assert "seoTaskId" not in response.json()["queries"][0]


def test_query_generation_request_still_accepts_legacy_topic_names() -> None:
    client = TestClient(create_app(answer_provider=DummyAnswerProvider()))

    response = client.post(
        "/api/v1/geo-tracking/query-generation",
        json=_generation_payload(topics=[]),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["topics"][0]["name"] == "採購評估"
    assert body["topics"][0]["description"] == ""
    assert body["queries"][0]["attributes"]["topicDescription"] == ""


def test_query_generation_request_generates_b2b_taiwan_queries_in_chinese() -> None:
    client = TestClient(create_app(answer_provider=DummyAnswerProvider()))

    response = client.post(
        "/api/v1/geo-tracking/query-generation",
        json=_generation_payload(
            brandName="山華塑膠",
            competitorBrands=["主要競品"],
            keywords=["氣動管"],
            region="TW",
            language="zh-TW",
        ),
    )

    assert response.status_code == 200
    query = response.json()["queries"][0]
    assert query["region"] == "TW"
    assert query["language"] == "zh-TW"
    assert "山華塑膠" in query["text"]
    assert "氣動管" in query["text"]
    assert query["keywords"] == ["氣動管"]


def test_query_generation_request_can_use_gemini_structured_provider() -> None:
    client = TestClient(
        create_app(
            answer_provider=DummyAnswerProvider(),
            query_generation_providers={
                ProviderCode.DUMMY: GeminiQueryGenerationStubProvider(),
                ProviderCode.GEMINI: GeminiQueryGenerationStubProvider(),
            },
        )
    )

    response = client.post(
        "/api/v1/geo-tracking/query-generation",
        json=_generation_payload(provider="gemini", brandName="山華塑膠"),
    )

    assert response.status_code == 200
    query = response.json()["queries"][0]
    assert query["text"] == "山華塑膠氣動管採購評估需要看哪些供應商條件？"
    assert query["keywords"] == ["pneumatic tubing"]
    assert query["attributes"]["intent"]["category"] == "commercial_investigation"
    assert query["attributes"]["topicDescription"] == TOPIC_DESCRIPTION
    assert "name" not in query["attributes"]["intent"]
    assert "sourceUrls" not in query["attributes"]
    assert "searchedKeywords" not in query["attributes"]


def test_query_generation_request_rejects_google_aio_provider() -> None:
    client = TestClient(create_app(answer_provider=DummyAnswerProvider()))

    response = client.post(
        "/api/v1/geo-tracking/query-generation",
        json=_generation_payload(provider="google_aio"),
    )

    assert response.status_code == 422


def test_query_research_request_returns_search_context() -> None:
    provider = GeminiQueryResearchStubProvider()
    client = TestClient(
        create_app(
            answer_provider=DummyAnswerProvider(),
            query_research_providers={
                ProviderCode.DUMMY: GeminiQueryResearchStubProvider(),
                ProviderCode.GEMINI: provider,
            },
        )
    )

    response = client.post(
        "/api/v1/geo-tracking/query-research",
        json={
            "provider": "gemini",
            "brandName": "山華塑膠",
            "competitorBrands": ["主要競品"],
            "keywords": ["氣動管"],
            "region": "TW",
            "language": "zh-TW",
            "marketType": "b2b_procurement",
            "audience": {
                "name": "B2B 採購",
                "description": "正在評估供應商的採購人員",
            },
            "intents": [
                {
                    "category": "commercial_investigation",
                    "description": "比較供應商",
                }
            ],
            "brandMentionRules": {
                "shouldMentionOwnBrand": True,
                "shouldMentionCompetitor": True,
            },
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["researchContext"] == "Research context for 山華塑膠"
    assert body["searchedKeywords"] == ["山華塑膠 氣動管", "台灣 氣動管 供應商"]
    assert body["sourceUrls"] == ["https://example.com/source"]
    assert provider.last_command is not None
    assert provider.last_command.intents[0].category == "commercial_investigation"
    assert provider.last_command.brand_mention_rules.should_mention_own_brand is True
    assert provider.last_command.brand_mention_rules.should_mention_competitor is True


def test_query_research_request_rejects_google_aio_provider() -> None:
    client = TestClient(create_app(answer_provider=DummyAnswerProvider()))

    response = client.post(
        "/api/v1/geo-tracking/query-research",
        json={
            "provider": "google_aio",
            "brandName": "山華塑膠",
            "competitorBrands": ["主要競品"],
            "keywords": ["氣動管"],
            "region": "TW",
            "language": "zh-TW",
            "marketType": "b2b_procurement",
        },
    )

    assert response.status_code == 422


def test_project_inspection_returns_editable_identity() -> None:
    provider = ProjectDiscoveryStubProvider()
    client = TestClient(
        create_app(
            answer_provider=DummyAnswerProvider(),
            project_discovery_provider=provider,
        )
    )

    response = client.post(
        "/api/v1/geo-tracking/project-discovery/inspection",
        json={
            "projectUrl": "https://www.kaiser.com.tw/",
            "language": "zh-TW",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "sourceUrl": "https://www.kaiser.com.tw/",
        "retrievedUrl": "https://www.kaiser.com.tw/",
        "projectName": "港香蘭藥廠股份有限公司",
        "projectDescription": "位於台灣的中藥製藥公司。",
        "projectType": "company",
        "coreOfferings": ["科學中藥"],
    }
    assert provider.last_inspection_command is not None
    assert provider.last_inspection_command.language == "zh-TW"
    assert provider.research_calls == 0


def test_project_suggestions_use_confirmed_identity() -> None:
    provider = ProjectDiscoveryStubProvider()
    client = TestClient(
        create_app(
            answer_provider=DummyAnswerProvider(),
            project_discovery_provider=provider,
        )
    )

    response = client.post(
        "/api/v1/geo-tracking/project-discovery/suggestions",
        json={
            "confirmedProject": {
                "sourceUrl": "https://www.kaiser.com.tw/",
                "retrievedUrl": "https://www.kaiser.com.tw/",
                "projectName": "使用者確認的港香蘭",
                "projectDescription": "使用者確認的科學中藥品牌描述。",
                "projectType": "company",
                "coreOfferings": ["科學中藥"],
            },
            "region": "TW",
            "language": "zh-TW",
            "marketType": "b2c",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "competitors": ["順天堂藥廠", "勝昌製藥"],
        "topics": [
            {
                "name": "科學中藥",
                "description": "聚焦製程、品質與產品使用情境。",
            }
        ],
        "keywords": ["科學中藥", "中藥濃縮粉"],
        "references": [{"url": "https://example.com/source", "title": "市場來源"}],
    }
    assert provider.last_suggestion_command is not None
    assert provider.last_suggestion_command.competitor_count == 5
    assert provider.last_suggestion_command.topic_count == 5
    assert provider.last_suggestion_command.keyword_count == 5
    assert provider.last_identity is not None
    assert provider.last_identity.project_name == "使用者確認的港香蘭"
    assert provider.last_identity.project_description == (
        "使用者確認的科學中藥品牌描述。"
    )


def test_project_discovery_rejects_legacy_audience_fields() -> None:
    client = TestClient(
        create_app(
            answer_provider=DummyAnswerProvider(),
            project_discovery_provider=ProjectDiscoveryStubProvider(),
        )
    )

    response = client.post(
        "/api/v1/geo-tracking/project-discovery/suggestions",
        json={
            "confirmedProject": {
                "sourceUrl": "https://www.kaiser.com.tw/",
                "retrievedUrl": "https://www.kaiser.com.tw/",
                "projectName": "港香蘭",
                "projectDescription": "提供科學中藥產品。",
                "projectType": "company",
                "coreOfferings": ["科學中藥"],
                "targetAudiences": ["一般消費者"],
            },
            "region": "TW",
            "language": "zh-TW",
            "marketType": "b2c",
            "audience": {
                "name": "B2C 消費",
                "description": "一般消費者",
            },
        },
    )

    assert response.status_code == 422


def test_project_discovery_reports_insufficient_public_context() -> None:
    client = TestClient(
        create_app(
            answer_provider=DummyAnswerProvider(),
            project_discovery_provider=InsufficientProjectDiscoveryStubProvider(),
        )
    )

    response = client.post(
        "/api/v1/geo-tracking/project-discovery/inspection",
        json={
            "projectUrl": "https://github.com/pleomax0730/agent-settings",
            "language": "en-US",
        },
    )

    assert response.status_code == 422
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["code"] == "insufficient_project_context"


def test_project_discovery_rejects_private_url() -> None:
    client = TestClient(
        create_app(
            answer_provider=DummyAnswerProvider(),
            project_discovery_provider=ProjectDiscoveryStubProvider(),
        )
    )

    response = client.post(
        "/api/v1/geo-tracking/project-discovery/inspection",
        json={
            "projectUrl": "http://127.0.0.1:8000/internal",
            "language": "zh-TW",
        },
    )

    assert response.status_code == 422


def test_run_request_returns_dummy_result_for_generated_query() -> None:
    client = TestClient(create_app(answer_provider=DummyAnswerProvider()))

    research_response = client.post(
        "/api/v1/geo-tracking/query-generation",
        json=_generation_payload(
            seoTaskId="22222222-2222-4222-8222-222222222222",
            brandName="港香蘭",
            competitorBrands=["順天堂"],
            keywords=["睡眠保健食品"],
            region="TW",
            language="zh-TW",
            marketType="b2c",
            topicNames=["產品型"],
            maxQueries=1,
            brandMentionRules={
                "shouldMentionOwnBrand": True,
                "shouldMentionCompetitor": False,
            },
        ),
    )
    query = research_response.json()["queries"][0]

    run_response = client.post(
        "/api/v1/geo-tracking/run-requests",
        json={
            "seoTaskId": "22222222-2222-4222-8222-222222222222",
            "provider": "dummy",
            "timing": "run_now",
            "queries": [
                {
                    "id": query["id"],
                    "text": query["text"],
                    "topicName": query["topicName"],
                    "region": query["region"],
                    "language": query["language"],
                    "marketType": query["marketType"],
                    "isBranded": query["isBranded"],
                    "metadata": query["metadata"],
                }
            ],
        },
    )

    assert run_response.status_code == 200
    body = run_response.json()
    assert "seoTaskId" not in body
    assert body["timing"] == "run_now"
    assert body["results"][0]["provider"] == "dummy"
    assert body["results"][0]["surface"] == "Dummy AI"
    assert body["results"][0]["status"] == "completed"
    assert body["results"][0]["referenceUrls"] == []
    assert body["results"][0]["references"] == []
    assert query["text"] in body["results"][0]["rawResponse"]


def test_run_request_does_not_require_or_return_seo_task_id() -> None:
    client = TestClient(create_app(answer_provider=DummyAnswerProvider()))

    response = client.post(
        "/api/v1/geo-tracking/run-requests",
        json={
            "provider": "dummy",
            "timing": "run_now",
            "queries": [
                {
                    "id": "44444444-4444-4444-8444-444444444444",
                    "text": "沒有 seoTaskId 的測試 query",
                    "topicName": "產品型",
                    "region": "TW",
                    "language": "zh-TW",
                    "marketType": "b2c",
                    "isBranded": False,
                    "metadata": {},
                }
            ],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert "seoTaskId" not in body
    assert body["results"][0]["status"] == "completed"


def test_run_request_does_not_trust_metadata_for_audit_attribution() -> None:
    provider = CapturingAnswerStubProvider()
    client = TestClient(
        create_app(
            answer_providers={
                ProviderCode.DUMMY: DummyAnswerProvider(),
                ProviderCode.GEMINI: provider,
            }
        )
    )

    response = client.post(
        "/api/v1/geo-tracking/run-requests",
        json={
            "provider": "gemini",
            "timing": "run_now",
            "queries": [
                {
                    "id": "44444444-4444-4444-8444-444444444444",
                    "text": "audit attribution test",
                    "topicName": "topic",
                    "region": "TW",
                    "language": "zh-TW",
                    "marketType": "b2c",
                    "isBranded": False,
                    "metadata": {
                        "tenantId": "11111111-1111-4111-8111-111111111111",
                        "projectId": "22222222-2222-4222-8222-222222222222",
                        "geoJobId": "33333333-3333-4333-8333-333333333333",
                    },
                }
            ],
        },
    )

    assert response.status_code == 200
    request = provider.requests[0]
    assert request.tenant_id is None
    assert request.project_id is None
    assert request.job_id is None


def test_run_request_uses_provider_from_request_body() -> None:
    client = TestClient(
        create_app(
            answer_providers={
                ProviderCode.DUMMY: DummyAnswerProvider(),
                ProviderCode.GEMINI: GeminiAnswerStubProvider(),
            }
        )
    )

    response = client.post(
        "/api/v1/geo-tracking/run-requests",
        json={
            "seoTaskId": "33333333-3333-4333-8333-333333333333",
            "provider": "gemini",
            "timing": "run_now",
            "queries": [
                {
                    "id": "44444444-4444-4444-8444-444444444444",
                    "text": "How does SHPI compare for pneumatic tubing sourcing?",
                    "topicName": "採購評估",
                    "region": "US",
                    "language": "en-US",
                    "marketType": "b2b_procurement",
                    "isBranded": True,
                    "metadata": {},
                }
            ],
        },
    )

    assert response.status_code == 200
    result = response.json()["results"][0]
    assert result["provider"] == "gemini"
    assert result["surface"] == "Gemini Stub"
    assert result["model"] == "gemini-stub"
    assert result["referenceUrls"] == ["https://example.com/reference"]
    assert result["references"] == [
        {
            "url": "https://example.com/reference",
            "title": "Example reference title",
        }
    ]


def test_run_request_can_use_google_aio_provider() -> None:
    client = TestClient(
        create_app(
            answer_providers={
                ProviderCode.DUMMY: DummyAnswerProvider(),
                ProviderCode.GEMINI: GeminiAnswerStubProvider(),
                ProviderCode.GOOGLE_AIO: GoogleAioAnswerStubProvider(),
            }
        )
    )

    response = client.post(
        "/api/v1/geo-tracking/run-requests",
        json={
            "seoTaskId": "33333333-3333-4333-8333-333333333333",
            "provider": "google_aio",
            "timing": "run_now",
            "queries": [
                {
                    "id": "44444444-4444-4444-8444-444444444444",
                    "text": "黃連膏 推薦",
                    "topicName": "產品型",
                    "region": "TW",
                    "language": "zh-TW",
                    "marketType": "b2c",
                    "isBranded": False,
                    "metadata": {},
                }
            ],
        },
    )

    assert response.status_code == 200
    result = response.json()["results"][0]
    assert result["provider"] == "google_aio"
    assert result["surface"] == "Google AI Overview"
    assert result["model"] == "serpapi-google-ai-overview"
    assert result["status"] == "completed"
    assert result["referenceUrls"] == ["https://example.com/aio-reference"]
    assert result["references"] == [
        {
            "url": "https://example.com/aio-reference",
            "title": "AIO reference title",
        }
    ]


def test_run_request_preserves_google_aio_no_result_error_code() -> None:
    client = TestClient(
        create_app(
            answer_providers={
                ProviderCode.DUMMY: DummyAnswerProvider(),
                ProviderCode.GEMINI: GeminiAnswerStubProvider(),
                ProviderCode.GOOGLE_AIO: GoogleAioNoResultStubProvider(),
            }
        )
    )

    response = client.post(
        "/api/v1/geo-tracking/run-requests",
        json={
            "seoTaskId": "33333333-3333-4333-8333-333333333333",
            "provider": "google_aio",
            "timing": "run_now",
            "queries": [
                {
                    "id": "44444444-4444-4444-8444-444444444444",
                    "text": "沒有 AIO 的 query",
                    "topicName": "產品型",
                    "region": "TW",
                    "language": "zh-TW",
                    "marketType": "b2c",
                    "isBranded": False,
                    "metadata": {},
                }
            ],
        },
    )

    assert response.status_code == 200
    result = response.json()["results"][0]
    assert result["provider"] == "google_aio"
    assert result["status"] == "failed"
    assert result["error"] == "no_google_aio_result"
    assert result["referenceUrls"] == []
    assert result["references"] == []


def test_run_request_logs_known_provider_failure_for_docker_logs(caplog) -> None:
    client = TestClient(
        create_app(
            answer_providers={
                ProviderCode.DUMMY: DummyAnswerProvider(),
                ProviderCode.GEMINI: GeminiAnswerStubProvider(),
                ProviderCode.GOOGLE_AIO: GoogleAioNoResultStubProvider(),
            }
        )
    )

    with caplog.at_level(logging.WARNING):
        response = client.post(
            "/api/v1/geo-tracking/run-requests",
            json={
                "provider": "google_aio",
                "timing": "run_now",
                "queries": [
                    {
                        "id": "44444444-4444-4444-8444-444444444444",
                        "text": "query with no aio result",
                        "topicName": "topic",
                        "region": "TW",
                        "language": "zh-TW",
                        "marketType": "b2c",
                        "isBranded": False,
                        "metadata": {},
                    }
                ],
            },
        )

    assert response.status_code == 200
    record = next(
        item
        for item in caplog.records
        if item.message.startswith("Geo tracking provider request failed: ")
    )
    assert "provider=google_aio" in record.message
    assert "queryId=44444444-4444-4444-8444-444444444444" in record.message
    assert "errorCode=no_google_aio_result" in record.message
    assert "exceptionType=ProviderRequestError" in record.message
    assert record.error_code == "no_google_aio_result"


def test_run_request_logs_unexpected_provider_failure_for_docker_logs(caplog) -> None:
    client = TestClient(
        create_app(
            answer_providers={
                ProviderCode.DUMMY: DummyAnswerProvider(),
                ProviderCode.GEMINI: GeminiFailingAnswerStubProvider(),
            }
        )
    )

    with caplog.at_level(logging.ERROR):
        response = client.post(
            "/api/v1/geo-tracking/run-requests",
            json={
                "provider": "gemini",
                "timing": "run_now",
                "queries": [
                    {
                        "id": "55555555-5555-4555-8555-555555555555",
                        "text": "query with provider exception",
                        "topicName": "topic",
                        "region": "US",
                        "language": "en-US",
                        "marketType": "b2b_procurement",
                        "isBranded": True,
                        "metadata": {},
                    }
                ],
            },
        )

    assert response.status_code == 200
    result = response.json()["results"][0]
    assert result["status"] == "failed"
    assert result["error"] == "provider_request_failed"
    record = next(
        item
        for item in caplog.records
        if item.message.startswith("Geo tracking provider request failed: ")
    )
    assert "provider=gemini" in record.message
    assert "queryId=55555555-5555-4555-8555-555555555555" in record.message
    assert "errorCode=provider_request_failed" in record.message
    assert "exceptionType=RuntimeError" in record.message
    assert record.exc_info is not None
    assert record.error_code == "provider_request_failed"


def test_app_lifespan_closes_answer_providers() -> None:
    closeable_provider = CloseableAnswerStubProvider()

    with TestClient(
        create_app(
            answer_providers={
                ProviderCode.DUMMY: closeable_provider,
                ProviderCode.GEMINI: GeminiAnswerStubProvider(),
                ProviderCode.GOOGLE_AIO: GoogleAioAnswerStubProvider(),
            }
        )
    ) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert closeable_provider.closed is True


def test_dummy_project_request_provides_frontend_seed_data() -> None:
    client = TestClient(create_app(answer_provider=DummyAnswerProvider()))

    response = client.get("/api/v1/geo-tracking/dummy-project")

    assert response.status_code == 200
    assert response.json()["region"] == "US"
    assert response.json()["marketType"] == "b2b_procurement"
