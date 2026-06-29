from fastapi.testclient import TestClient
from younilab_geo_tracking_api import create_app
from younilab_geo_tracking_application import (
    AnswerRequest,
    AnswerResponse,
    ProviderRequestError,
    QueryDraft,
    QueryGenerationCommand,
    QueryResearchCommand,
    QueryResearchResult,
    Reference,
)
from younilab_geo_tracking_domain import ProviderCode
from younilab_geo_tracking_infrastructure import DummyAnswerProvider

TOPIC_DESCRIPTION = "聚焦供應商條件、交期、認證、外銷能力與採購風險。"


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
    assert body["seoTaskId"] == "22222222-2222-4222-8222-222222222222"
    assert body["timing"] == "run_now"
    assert body["results"][0]["provider"] == "dummy"
    assert body["results"][0]["surface"] == "Dummy AI"
    assert body["results"][0]["status"] == "completed"
    assert body["results"][0]["referenceUrls"] == []
    assert body["results"][0]["references"] == []
    assert query["text"] in body["results"][0]["rawResponse"]


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
