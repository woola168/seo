import json
from typing import Any
from uuid import UUID

import httpx
import pytest
from google import genai
from google.genai.errors import APIError, ClientError
import younilab_geo_tracking_infrastructure.project_discovery as discovery_module
import younilab_geo_tracking_infrastructure.providers as providers_module
from younilab_geo_tracking_application import (
    AnswerRequest,
    ConfirmedProjectIdentity,
    ProjectInspectionCommand,
    ProjectSuggestionCommand,
    ProviderRequestError,
    QueryGenerationCommand,
    QueryResearchCommand,
    VerifiedProjectIdentity,
)
from younilab_geo_tracking_domain import MarketType, ProviderCode, RegionCode
from younilab_geo_tracking_infrastructure import (
    GeminiProjectDiscoveryProvider,
    GeminiQueryGenerationProvider,
    GeminiQueryResearchProvider,
    GeminiVertexAnswerProvider,
    GeoTrackingSettings,
    SerpApiGoogleAioAnswerProvider,
)
from younilab_geo_tracking_infrastructure.providers import (
    _GeminiApiCallBudget,
    _GeminiIntent,
    _generate_with_reference_retry,
    _matching_intent,
    _query_generation_prompt,
    _reference_retry_prompt,
)
from younilab_provider_request_audit import (
    MemoryProviderRequestRecorder,
    ProviderRequestContext,
    ProviderRequestExecutor,
)


def _recorder() -> MemoryProviderRequestRecorder:
    return MemoryProviderRequestRecorder()


def _gemini_executor() -> ProviderRequestExecutor:
    return ProviderRequestExecutor(
        _recorder(),
        ProviderRequestContext(
            platform_code="gemini",
            provider_code="google_vertex_ai",
            provider_operation="generate_content",
            use_case="test",
            source_service="test",
        ),
    )


def _query_generation_command() -> QueryGenerationCommand:
    return QueryGenerationCommand.model_validate(
        {
            "provider": "gemini",
            "brandName": "Acme",
            "competitorBrands": [],
            "keywords": ["erp"],
            "region": "TW",
            "language": "en-US",
            "marketType": "b2b_procurement",
            "topics": [{"name": "ERP", "description": "ERP selection"}],
            "intents": [
                {"category": "informational", "description": "Learn"},
                {"category": "transactional", "description": "Act"},
            ],
            "audience": {"name": "Buyer", "description": "Software buyer"},
            "maxQueries": 1,
        }
    )


def test_query_generation_prompt_guides_intent_coverage_without_equal_allocation() -> None:
    payload = json.loads(_query_generation_prompt(_query_generation_command(), "en-US"))

    guidance = " ".join(payload["intentGuidance"])
    assert "at least one query for every selected intent" in guidance
    assert "maxQueries is lower" in guidance
    assert "equal distribution is not required" in guidance
    assert "array order does not indicate priority" in guidance


def test_query_generation_preserves_unmatched_model_intent_for_later_classification() -> None:
    intent = _matching_intent(
        _query_generation_command(),
        _GeminiIntent(category="unexpected", description="Unexpected category"),
    )

    assert intent.category == "unexpected"
    assert intent.description == "Unexpected category"


@pytest.mark.anyio
async def test_query_planning_records_each_gemini_request_and_disables_sdk_retry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client_arguments: list[dict[str, Any]] = []
    responses = iter(
        [
            {
                "items": [
                    {
                        "attributes": {
                            "intent": {
                                "category": "informational",
                                "description": "Understand options",
                            },
                            "keyword": "erp",
                            "topicName": "ERP",
                            "topicDescription": "ERP selection",
                            "audience": {
                                "name": "Buyer",
                                "description": "Software buyer",
                            },
                            "brandMentionRules": {
                                "shouldMentionOwnBrand": False,
                                "shouldMentionCompetitor": False,
                            },
                        },
                        "query": "Which ERP fits a manufacturer?",
                        "keywords": ["erp"],
                    }
                ]
            },
            {
                "researchContext": "ERP buyers compare implementation support.",
                "searchedKeywords": ["erp"],
                "sourceUrls": ["https://example.com/erp"],
            },
        ]
    )

    class FakeModels:
        def generate_content(self, **kwargs: Any) -> Any:
            return type(
                "Response",
                (),
                {
                    "parsed": None,
                    "text": json.dumps(next(responses)),
                    "candidates": [],
                },
            )()

    class FakeClient:
        def __init__(self, **kwargs: Any) -> None:
            client_arguments.append(kwargs)
            self.models = FakeModels()

        def close(self) -> None:
            return None

    monkeypatch.setattr(genai, "Client", FakeClient)
    generation_recorder = _recorder()
    research_recorder = _recorder()
    generation_provider = GeminiQueryGenerationProvider(
        GeoTrackingSettings(vertex_project="test-project"),
        generation_recorder,
    )
    research_provider = GeminiQueryResearchProvider(
        GeoTrackingSettings(vertex_project="test-project"),
        research_recorder,
    )
    shared = {
        "provider": "gemini",
        "brandName": "Acme",
        "competitorBrands": [],
        "keywords": ["erp"],
        "region": "TW",
        "language": "en-US",
        "marketType": "b2b_procurement",
        "intents": [
            {
                "category": "informational",
                "description": "Understand options",
            }
        ],
        "audience": {"name": "Buyer", "description": "Software buyer"},
        "brandMentionRules": {
            "shouldMentionOwnBrand": False,
            "shouldMentionCompetitor": False,
        },
    }

    drafts = await generation_provider.generate_drafts(
        QueryGenerationCommand.model_validate(
            {
                **shared,
                "topics": [{"name": "ERP", "description": "ERP selection"}],
                "topicNames": ["ERP"],
                "maxQueries": 1,
            }
        )
    )
    research = await research_provider.research(
        QueryResearchCommand.model_validate(shared)
    )

    assert len(drafts) == 1
    assert research.research_context.startswith("ERP buyers")
    assert next(iter(generation_recorder.requests.values())).context.use_case == (
        "query_generation"
    )
    assert next(iter(research_recorder.requests.values())).context.use_case == (
        "query_research"
    )
    assert set(generation_recorder.usage_capture_statuses.values()) == {
        "unavailable"
    }
    assert set(research_recorder.usage_capture_statuses.values()) == {"unavailable"}
    assert all(
        arguments["http_options"].retry_options.attempts == 1
        for arguments in client_arguments
    )


class FakeResponse:
    def __init__(self, text: str, url: str | None = None) -> None:
        self.text = text
        self.candidates = [FakeCandidate(url)] if url else []


class FakeCandidate:
    def __init__(self, url: str | None) -> None:
        self.grounding_metadata = FakeGroundingMetadata(url)


class FakeGroundingMetadata:
    def __init__(self, url: str | None, search_entry_point_html: str = "") -> None:
        self.grounding_chunks = [FakeGroundingChunk(url)] if url else []
        self.web_search_queries = (
            ["supplier search"] if url or search_entry_point_html else []
        )
        self.search_entry_point = (
            FakeSearchEntryPoint(search_entry_point_html)
            if search_entry_point_html
            else None
        )


class FakeSearchEntryPoint:
    def __init__(self, rendered_content: str) -> None:
        self.rendered_content = rendered_content


class FakeGroundingChunk:
    def __init__(self, url: str | None) -> None:
        self.web = FakeWeb(url) if url else None


class FakeWeb:
    def __init__(self, url: str) -> None:
        self.uri = url
        self.title = "Reference title"


class FakeUrlMetadata:
    def __init__(self, url: str, status: str) -> None:
        self.retrieved_url = url
        self.url_retrieval_status = status


class FakeUrlContextMetadata:
    def __init__(self, url: str, status: str) -> None:
        self.url_metadata = [FakeUrlMetadata(url, status)]


class FakeProjectDiscoveryCandidate:
    def __init__(
        self,
        *,
        url_context_metadata: FakeUrlContextMetadata | None = None,
        grounding_metadata: Any = None,
    ) -> None:
        self.url_context_metadata = url_context_metadata
        self.grounding_metadata = grounding_metadata


class FakeProjectDiscoveryResponse:
    def __init__(self, payload: dict[str, object], candidates: list[Any]) -> None:
        self.parsed = None
        self.text = json.dumps(payload, ensure_ascii=False)
        self.candidates = candidates


@pytest.mark.anyio
async def test_project_discovery_inspects_url_with_url_context_only() -> None:
    calls: list[tuple[str, Any]] = []
    recorder = _recorder()

    async def generate(contents: str, config: Any) -> FakeProjectDiscoveryResponse:
        calls.append((contents, config))
        return FakeProjectDiscoveryResponse(
            {
                "projectName": "港香蘭藥廠股份有限公司",
                "projectDescription": "位於台灣的中藥製藥公司。",
                "projectType": "company",
                "coreOfferings": ["科學中藥"],
                "sufficientContext": True,
                "limitation": "",
            },
            [
                FakeProjectDiscoveryCandidate(
                    url_context_metadata=FakeUrlContextMetadata(
                        "https://www.kaiser.com.tw/",
                        "URL_RETRIEVAL_STATUS_SUCCESS",
                    )
                )
            ],
        )

    provider = GeminiProjectDiscoveryProvider(
        GeoTrackingSettings(),
        recorder,
        generate_content=generate,
        fetch_page=_no_fetched_page,
    )

    inspection = await provider.inspect_url(_inspection_command())

    assert inspection.retrieval_succeeded is True
    assert str(inspection.retrieved_url) == "https://www.kaiser.com.tw/"
    assert inspection.identity is not None
    assert inspection.identity.project_name == "港香蘭藥廠股份有限公司"
    prompt, config = calls[0]
    assert json.loads(prompt)["projectUrl"] == "https://www.kaiser.com.tw/"
    assert config.tools[0].url_context is not None
    assert config.tools[0].google_search is None
    recorded = next(iter(recorder.requests.values()))
    assert recorded.context.use_case == "project_inspection"
    assert recorded.request_kind == "initial"
    assert recorder.usage_capture_statuses[recorded.id] == "unavailable"
    assert "不得只依 domain" in config.system_instruction
    assert "工具結果本身不是最終答案" in config.system_instruction
    assert "sufficientContext=false" in config.system_instruction
    assert (
        "directly supported"
        in config.response_schema.model_fields["projectName"].description
    )


@pytest.mark.anyio
async def test_project_discovery_uses_page_metadata_when_url_context_fails() -> None:
    events: list[str] = []
    calls: list[tuple[str, Any]] = []

    async def fetch_page(url: str) -> tuple[str, bytes]:
        events.append("fetch")
        return (
            url,
            b"""
            <html>
              <head>
                <title>World Gym Taiwan</title>
                <meta name="description" content="Fitness clubs and coaching">
                <script type="application/ld+json">
                  {
                    "@type": "ExerciseGym",
                    "name": "World Gym Taiwan",
                    "description": "Fitness clubs and coaching"
                  }
                </script>
              </head>
            </html>
            """,
        )

    async def generate(contents: str, config: Any) -> FakeProjectDiscoveryResponse:
        events.append("generate")
        calls.append((contents, config))
        return FakeProjectDiscoveryResponse(
            {
                "projectName": "World Gym Taiwan",
                "projectDescription": "A fitness club operator in Taiwan.",
                "projectType": "service",
                "coreOfferings": ["Fitness clubs", "Personal coaching"],
                "sufficientContext": True,
                "limitation": "",
            },
            [
                FakeProjectDiscoveryCandidate(
                    url_context_metadata=FakeUrlContextMetadata(
                        "https://www.worldgymtaiwan.com/",
                        "URL_RETRIEVAL_STATUS_ERROR",
                    )
                )
            ],
        )

    provider = GeminiProjectDiscoveryProvider(
        GeoTrackingSettings(),
        _recorder(),
        generate_content=generate,
        fetch_page=fetch_page,
    )

    inspection = await provider.inspect_url(
        _inspection_command().model_copy(
            update={"project_url": "https://www.worldgymtaiwan.com/"}
        )
    )

    assert events == ["fetch", "generate"]
    assert inspection.retrieval_succeeded is True
    assert str(inspection.retrieved_url) == "https://www.worldgymtaiwan.com/"
    prompt, config = calls[0]
    payload = json.loads(prompt)
    assert payload["pageMetadata"]["title"] == "World Gym Taiwan"
    assert payload["pageMetadata"]["structuredData"][0]["types"] == ["ExerciseGym"]
    assert payload["pageMetadata"]["structuredData"][0]["name"] == ("World Gym Taiwan")
    assert config.tools[0].url_context is not None


@pytest.mark.anyio
async def test_project_discovery_passes_title_only_metadata_to_stage_one() -> None:
    calls: list[str] = []

    async def fetch_page(url: str) -> tuple[str, bytes]:
        return url, b"<html><head><title>Example Project</title></head></html>"

    async def generate(contents: str, config: Any) -> FakeProjectDiscoveryResponse:
        calls.append(contents)
        return FakeProjectDiscoveryResponse(
            {
                "projectName": "Example Project",
                "projectDescription": "An example service Project.",
                "projectType": "service",
                "coreOfferings": ["Example service"],
                "sufficientContext": True,
                "limitation": "",
            },
            [
                FakeProjectDiscoveryCandidate(
                    url_context_metadata=FakeUrlContextMetadata(
                        "https://example.com/",
                        "URL_RETRIEVAL_STATUS_ERROR",
                    )
                )
            ],
        )

    provider = GeminiProjectDiscoveryProvider(
        GeoTrackingSettings(),
        _recorder(),
        generate_content=generate,
        fetch_page=fetch_page,
    )

    inspection = await provider.inspect_url(
        _inspection_command().model_copy(update={"project_url": "https://example.com/"})
    )

    assert inspection.retrieval_succeeded is True
    assert str(inspection.retrieved_url) == "https://example.com/"
    assert json.loads(calls[0])["pageMetadata"]["title"] == "Example Project"


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/",
        "http://[::1]/",
        "http://example.local/",
        "http://user:password@example.com/",
        "https://example.com:8443/",
    ],
)
def test_project_discovery_metadata_fetch_rejects_unsafe_urls(url: str) -> None:
    assert discovery_module._is_public_http_url(url) is False


@pytest.mark.anyio
async def test_project_discovery_metadata_resolver_rejects_private_dns() -> None:
    class PrivateResolver:
        async def resolve(self, host: str, port: int, family: Any) -> list[Any]:
            return [{"host": "10.0.0.8"}]

        async def close(self) -> None:
            return None

    resolver = discovery_module._PublicOnlyResolver()
    resolver._delegate = PrivateResolver()

    with pytest.raises(OSError, match="non-public"):
        await resolver.resolve("internal.example", 443)


def test_project_discovery_identity_prompt_requires_final_assessment_in_english() -> (
    None
):
    prompt = discovery_module._identity_system_prompt("en-US")

    assert "tool result itself is not the final answer" in prompt
    assert "sufficientContext=false" in prompt


@pytest.mark.anyio
async def test_project_discovery_researches_with_verified_identity_and_search() -> None:
    calls: list[tuple[str, Any]] = []

    async def generate(contents: str, config: Any) -> FakeProjectDiscoveryResponse:
        calls.append((contents, config))
        return FakeProjectDiscoveryResponse(
            {
                "competitors": ["順天堂藥廠", "勝昌製藥"],
                "topics": [
                    {
                        "name": "科學中藥",
                        "description": "聚焦製程、品質與產品使用情境。",
                    }
                ],
                "keywords": ["科學中藥", "中藥濃縮粉"],
            },
            [
                FakeProjectDiscoveryCandidate(
                    grounding_metadata=FakeGroundingMetadata(
                        "https://example.com/market-source"
                    )
                )
            ],
        )

    provider = GeminiProjectDiscoveryProvider(
        GeoTrackingSettings(),
        _recorder(),
        generate_content=generate,
        fetch_page=_no_fetched_page,
    )
    identity = VerifiedProjectIdentity(
        source_url="https://www.kaiser.com.tw/",
        retrieved_url="https://www.kaiser.com.tw/",
        project_name="港香蘭藥廠股份有限公司",
        project_description="位於台灣的中藥製藥公司。",
        project_type="company",
        core_offerings=("科學中藥",),
    )

    result = await provider.research_suggestions(
        _suggestion_command(),
        identity,
    )

    assert result.search_succeeded is True
    assert result.competitors == ["順天堂藥廠", "勝昌製藥"]
    assert result.topics[0].name == "科學中藥"
    assert result.keywords == ["科學中藥", "中藥濃縮粉"]
    assert result.references[0].title == "Reference title"
    prompt, config = calls[0]
    payload = json.loads(prompt)
    assert payload["verifiedProject"]["projectName"] == "港香蘭藥廠股份有限公司"
    assert payload["market"] == {
        "region": "TW",
        "language": "zh-TW",
        "marketType": "b2c",
    }
    assert "targetAudiences" not in payload["verifiedProject"]
    assert payload["targetCounts"] == {
        "competitors": 5,
        "topics": 5,
        "keywords": 5,
    }
    assert config.tools[0].google_search is not None
    assert config.tools[0].url_context is None
    assert "authoritative context" in config.system_instruction


@pytest.mark.anyio
async def test_project_discovery_falls_back_to_search_entry_point() -> None:
    async def generate(contents: str, config: Any) -> FakeProjectDiscoveryResponse:
        return FakeProjectDiscoveryResponse(
            {"competitors": [], "topics": [], "keywords": []},
            [
                FakeProjectDiscoveryCandidate(
                    grounding_metadata=FakeGroundingMetadata(
                        None,
                        search_entry_point_html=(
                            '<div><a class="chip" '
                            'href="https://vertexaisearch.cloud.google.com/'
                            'grounding-api-redirect/verified">'
                            "台灣科學中藥品牌</a></div>"
                        ),
                    )
                )
            ],
        )

    provider = GeminiProjectDiscoveryProvider(
        GeoTrackingSettings(),
        _recorder(),
        generate_content=generate,
        fetch_page=_no_fetched_page,
    )
    identity = VerifiedProjectIdentity(
        source_url="https://www.kaiser.com.tw/",
        retrieved_url="https://www.kaiser.com.tw/",
        project_name="港香蘭藥廠股份有限公司",
        project_description="位於台灣的中藥製藥公司。",
        project_type="company",
        core_offerings=("科學中藥",),
    )

    result = await provider.research_suggestions(
        _suggestion_command(),
        identity,
    )

    assert result.search_succeeded is True
    assert [reference.model_dump(mode="json") for reference in result.references] == [
        {
            "url": (
                "https://vertexaisearch.cloud.google.com/"
                "grounding-api-redirect/verified"
            ),
            "title": "Google Search: 台灣科學中藥品牌",
        }
    ]


@pytest.mark.anyio
async def test_project_discovery_maps_vertex_inspection_failure() -> None:
    async def generate(contents: str, config: Any) -> Any:
        raise RuntimeError("vertex unavailable")

    provider = GeminiProjectDiscoveryProvider(
        GeoTrackingSettings(),
        _recorder(),
        generate_content=generate,
        fetch_page=_no_fetched_page,
    )

    with pytest.raises(ProviderRequestError) as exc_info:
        await provider.inspect_url(_inspection_command())

    assert exc_info.value.code == "project_url_inspection_failed"


@pytest.mark.anyio
async def test_project_discovery_reuses_and_closes_gemini_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    responses = [
        FakeProjectDiscoveryResponse(
            {
                "projectName": "港香蘭藥廠股份有限公司",
                "projectDescription": "位於台灣的中藥製藥公司。",
                "projectType": "company",
                "coreOfferings": ["科學中藥"],
                "sufficientContext": True,
                "limitation": "",
            },
            [
                FakeProjectDiscoveryCandidate(
                    url_context_metadata=FakeUrlContextMetadata(
                        "https://www.kaiser.com.tw/",
                        "URL_RETRIEVAL_STATUS_SUCCESS",
                    )
                )
            ],
        ),
        FakeProjectDiscoveryResponse(
            {"competitors": [], "topics": [], "keywords": []},
            [
                FakeProjectDiscoveryCandidate(
                    grounding_metadata=FakeGroundingMetadata(
                        "https://example.com/source"
                    )
                )
            ],
        ),
    ]

    class FakeModels:
        async def generate_content(self, **kwargs: Any) -> Any:
            return responses.pop(0)

    class FakeAsyncClient:
        def __init__(self) -> None:
            self.models = FakeModels()
            self.closed = False

        async def aclose(self) -> None:
            self.closed = True

    class FakeClient:
        def __init__(self) -> None:
            self.aio = FakeAsyncClient()

    clients: list[FakeClient] = []

    def create_client(**kwargs: Any) -> FakeClient:
        client = FakeClient()
        clients.append(client)
        return client

    monkeypatch.setattr(discovery_module.genai, "Client", create_client)
    provider = GeminiProjectDiscoveryProvider(
        GeoTrackingSettings(vertex_project="test-project"),
        _recorder(),
        fetch_page=_no_fetched_page,
    )

    inspection = await provider.inspect_url(_inspection_command())
    assert inspection.identity is not None
    identity = VerifiedProjectIdentity(
        source_url="https://www.kaiser.com.tw/",
        retrieved_url="https://www.kaiser.com.tw/",
        project_name=inspection.identity.project_name,
        project_description=inspection.identity.project_description,
        project_type=inspection.identity.project_type,
        core_offerings=tuple(inspection.identity.core_offerings),
    )
    await provider.research_suggestions(_suggestion_command(), identity)
    await provider.close()

    assert len(clients) == 1
    assert clients[0].aio.closed is True


@pytest.mark.anyio
async def test_reference_retry_runs_when_first_response_has_no_references() -> None:
    calls: list[str] = []
    responses = [
        FakeResponse("No grounded answer"),
        FakeResponse("Grounded answer", "https://example.com/reference"),
    ]

    async def generate(contents: str, request_kind: str) -> FakeResponse:
        calls.append(contents)
        return responses[len(calls) - 1]

    response, references = await _generate_with_reference_retry(
        generate,
        "ambiguous supplier query",
        "en-US",
    )

    assert response.text == "Grounded answer"
    assert [reference.url for reference in references] == [
        "https://example.com/reference"
    ]
    assert (
        "first action before answering must be to use the Google Search tool"
        in calls[0]
    )
    assert "Search the original query first" in calls[0]
    assert "ambiguous supplier query" in calls[0]
    assert "previous response produced no grounding references" in calls[1]
    assert "ambiguous supplier query" in calls[1]


@pytest.mark.anyio
async def test_reference_retry_keeps_first_response_when_references_exist() -> None:
    calls: list[str] = []

    async def generate(contents: str, request_kind: str) -> FakeResponse:
        calls.append(contents)
        return FakeResponse("Grounded answer", "https://example.com/reference")

    response, references = await _generate_with_reference_retry(
        generate,
        "clear supplier query",
        "en-US",
    )

    assert response.text == "Grounded answer"
    assert [reference.url for reference in references] == [
        "https://example.com/reference"
    ]
    assert len(calls) == 1
    assert "Search the original query first" in calls[0]
    assert "clear supplier query" in calls[0]


@pytest.mark.anyio
async def test_initial_grounding_prompt_uses_traditional_chinese() -> None:
    calls: list[str] = []

    async def generate(contents: str, request_kind: str) -> FakeResponse:
        calls.append(contents)
        return FakeResponse("有來源的回答", "https://example.com/reference")

    await _generate_with_reference_retry(
        generate,
        "山華塑膠 氣動管",
        "zh-TW",
    )

    assert len(calls) == 1
    assert "回答前的第一個動作必須是使用 Google Search tool" in calls[0]
    assert "請先搜尋原始 query" in calls[0]
    assert "山華塑膠 氣動管" in calls[0]


@pytest.mark.anyio
async def test_gemini_api_retries_resource_exhausted_with_fixed_backoff(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = 0
    delays: list[float] = []

    async def generate(contents: str) -> FakeResponse:
        nonlocal calls
        calls += 1
        if calls < 3:
            raise ClientError(
                429,
                {"status": "RESOURCE_EXHAUSTED", "message": "try again later"},
            )
        return FakeResponse("Grounded answer", "https://example.com/reference")

    async def sleep(delay: float) -> None:
        delays.append(delay)

    monkeypatch.setattr(providers_module.asyncio, "sleep", sleep)
    monkeypatch.setattr(providers_module.random, "uniform", lambda start, end: 0.0)

    budget = _GeminiApiCallBudget(generate, _gemini_executor())
    response = await budget.generate("supplier query")

    assert response.text == "Grounded answer"
    assert calls == 3
    assert delays == [1.0, 2.0]


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("status_code", "error_code"),
    [
        (400, "gemini_invalid_argument"),
        (401, "gemini_unauthenticated"),
        (403, "gemini_permission_denied"),
        (404, "gemini_not_found"),
        (499, "gemini_client_closed_request"),
    ],
)
async def test_gemini_api_does_not_retry_permanent_error(
    monkeypatch: pytest.MonkeyPatch,
    status_code: int,
    error_code: str,
) -> None:
    calls = 0

    async def generate(contents: str) -> FakeResponse:
        nonlocal calls
        calls += 1
        raise APIError(
            status_code,
            {"status": "PERMANENT_ERROR", "message": "request rejected"},
        )

    async def unexpected_sleep(delay: float) -> None:
        raise AssertionError("permanent Gemini errors must not be retried")

    monkeypatch.setattr(providers_module.asyncio, "sleep", unexpected_sleep)

    budget = _GeminiApiCallBudget(generate, _gemini_executor())

    with pytest.raises(ProviderRequestError) as exc_info:
        await budget.generate("supplier query")

    assert exc_info.value.code == error_code
    assert calls == 1


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("status_code", "error_code"),
    [
        (408, "gemini_request_timeout"),
        (429, "gemini_resource_exhausted"),
        (500, "gemini_internal_error"),
        (502, "gemini_bad_gateway"),
        (503, "gemini_unavailable"),
        (504, "gemini_deadline_exceeded"),
        (599, "gemini_server_error"),
    ],
)
async def test_gemini_api_reports_transient_error_after_retry_budget(
    monkeypatch: pytest.MonkeyPatch,
    status_code: int,
    error_code: str,
) -> None:
    calls = 0

    async def generate(contents: str) -> FakeResponse:
        nonlocal calls
        calls += 1
        raise APIError(
            status_code,
            {"status": "TRANSIENT_ERROR", "message": "try again later"},
        )

    async def sleep(delay: float) -> None:
        return None

    monkeypatch.setattr(providers_module.asyncio, "sleep", sleep)
    monkeypatch.setattr(providers_module.random, "uniform", lambda start, end: 0.0)

    budget = _GeminiApiCallBudget(generate, _gemini_executor())

    with pytest.raises(ProviderRequestError) as exc_info:
        await budget.generate("supplier query")

    assert exc_info.value.code == error_code
    assert calls == 3


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("error", "error_code"),
    [
        (httpx.ReadTimeout("request timed out"), "gemini_request_timeout"),
        (httpx.ConnectError("connection failed"), "gemini_network_error"),
        (httpx.RemoteProtocolError("connection closed"), "gemini_network_error"),
    ],
)
async def test_gemini_api_retries_temporary_transport_error(
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
    error_code: str,
) -> None:
    calls = 0

    async def generate(contents: str) -> FakeResponse:
        nonlocal calls
        calls += 1
        raise error

    async def sleep(delay: float) -> None:
        return None

    monkeypatch.setattr(providers_module.asyncio, "sleep", sleep)
    monkeypatch.setattr(providers_module.random, "uniform", lambda start, end: 0.0)

    budget = _GeminiApiCallBudget(generate, _gemini_executor())

    with pytest.raises(ProviderRequestError) as exc_info:
        await budget.generate("supplier query")

    assert exc_info.value.code == error_code
    assert calls == 3


@pytest.mark.anyio
async def test_gemini_api_does_not_retry_unexpected_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = 0

    async def generate(contents: str) -> FakeResponse:
        nonlocal calls
        calls += 1
        raise ValueError("invalid response")

    async def unexpected_sleep(delay: float) -> None:
        raise AssertionError("unexpected errors must not be retried")

    monkeypatch.setattr(providers_module.asyncio, "sleep", unexpected_sleep)

    budget = _GeminiApiCallBudget(generate, _gemini_executor())

    with pytest.raises(ValueError, match="invalid response"):
        await budget.generate("supplier query")

    assert calls == 1


@pytest.mark.anyio
async def test_gemini_api_does_not_retry_non_transient_transport_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = 0

    async def generate(contents: str) -> FakeResponse:
        nonlocal calls
        calls += 1
        raise httpx.UnsupportedProtocol("unsupported protocol")

    async def unexpected_sleep(delay: float) -> None:
        raise AssertionError("non-transient transport errors must not be retried")

    monkeypatch.setattr(providers_module.asyncio, "sleep", unexpected_sleep)

    budget = _GeminiApiCallBudget(generate, _gemini_executor())

    with pytest.raises(httpx.UnsupportedProtocol):
        await budget.generate("supplier query")

    assert calls == 1


@pytest.mark.anyio
async def test_grounding_fallback_shares_gemini_api_call_budget(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    async def generate(contents: str) -> FakeResponse:
        calls.append(contents)
        if len(calls) < 3:
            raise ClientError(
                429,
                {"status": "RESOURCE_EXHAUSTED", "message": "try again later"},
            )
        return FakeResponse("Answer without references")

    async def sleep(delay: float) -> None:
        return None

    monkeypatch.setattr(providers_module.asyncio, "sleep", sleep)
    monkeypatch.setattr(providers_module.random, "uniform", lambda start, end: 0.0)

    recorder = _recorder()
    executor = ProviderRequestExecutor(
        recorder,
        ProviderRequestContext(
            platform_code="gemini",
            provider_code="google_vertex_ai",
            provider_operation="generate_content",
            use_case="geo_query_answer",
            source_service="test",
        ),
    )
    budget = _GeminiApiCallBudget(generate, executor)
    response, references = await _generate_with_reference_retry(
        budget.generate,
        "supplier query",
        "en-US",
        has_remaining_calls=budget.has_remaining_calls,
    )

    assert response.text == "Answer without references"
    assert references == []
    assert len(calls) == 3
    assert [item.request_kind for item in recorder.requests.values()] == [
        "initial",
        "transient_retry",
        "transient_retry",
    ]
    assert set(recorder.usage_capture_statuses.values()) == {"unavailable"}


@pytest.mark.anyio
async def test_gemini_answer_provider_disables_sdk_retry_and_sets_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client_arguments: dict[str, Any] = {}
    clients: list[Any] = []

    class FakeModels:
        def generate_content(self, **kwargs: Any) -> FakeResponse:
            return FakeResponse(
                "Grounded answer",
                "https://example.com/reference",
            )

    class FakeClient:
        def __init__(self, **kwargs: Any) -> None:
            client_arguments.update(kwargs)
            self.models = FakeModels()
            self.closed = False
            clients.append(self)

        def close(self) -> None:
            self.closed = True

    monkeypatch.setattr(genai, "Client", FakeClient)

    recorder = _recorder()
    provider = GeminiVertexAnswerProvider(
        GeoTrackingSettings(vertex_project="test-project"),
        recorder,
    )
    run_request_id = UUID("11111111-1111-4111-8111-111111111111")

    response = await provider.generate_answer(
        _answer_request().model_copy(update={"run_request_id": run_request_id})
    )
    await provider.generate_answer(
        _answer_request().model_copy(update={"run_request_id": run_request_id})
    )

    http_options = client_arguments["http_options"]
    assert http_options.retry_options.attempts == 1
    assert http_options.timeout == 60_000
    assert response.raw_response == "Grounded answer"
    assert all(client.closed for client in clients)
    requests = list(recorder.requests.values())
    assert [request.request_number for request in requests] == [1, 1]
    assert len({request.operation_id for request in requests}) == 2
    assert {request.context.run_request_id for request in requests} == {run_request_id}


def test_reference_retry_prompt_uses_traditional_chinese_for_zh_tw() -> None:
    prompt = _reference_retry_prompt("山華塑膠 氣動管", "zh-TW")

    assert "第一個動作必須是使用 Google Search tool" in prompt
    assert "上一輪回應沒有產生 grounding references" in prompt
    assert "山華塑膠 氣動管" in prompt


@pytest.mark.anyio
async def test_google_aio_provider_uses_direct_ai_overview_content() -> None:
    calls: list[dict[str, str]] = []

    async def fetch_json(params: dict[str, str]) -> dict[str, object]:
        calls.append(params)
        return {
            "ai_overview": {
                "text_blocks": [
                    {
                        "type": "paragraph",
                        "snippet": "黃連膏可用於清熱與皮膚舒緩。",
                    },
                    {
                        "type": "list",
                        "list": [
                            {
                                "title": "選購重點",
                                "snippet": "確認來源與衛福部相關資訊。",
                            }
                        ],
                    },
                ],
                "references": [
                    {
                        "title": "黃連膏說明",
                        "link": "https://example.com/aio-source",
                    }
                ],
            }
        }

    provider = SerpApiGoogleAioAnswerProvider(
        GeoTrackingSettings(serpapi_api_key="test-key"),
        _recorder(),
        fetch_json=fetch_json,
    )

    response = await provider.generate_answer(_answer_request())

    assert len(calls) == 1
    assert calls[0]["engine"] == "google"
    assert calls[0]["hl"] == "zh-tw"
    assert calls[0]["gl"] == "tw"
    assert calls[0]["location"] == "Taiwan"
    assert response.provider == ProviderCode.GOOGLE_AIO
    assert response.surface == "Google AI Overview"
    assert response.model == "serpapi-google-ai-overview"
    assert "黃連膏可用於清熱與皮膚舒緩。" in response.raw_response
    assert "- 選購重點 確認來源與衛福部相關資訊。" in response.raw_response
    assert response.references[0].title == "黃連膏說明"
    assert response.reference_urls == ["https://example.com/aio-source"]


@pytest.mark.anyio
async def test_google_aio_provider_renders_nested_lists_and_table() -> None:
    async def fetch_json(params: dict[str, str]) -> dict[str, object]:
        return {
            "ai_overview": {
                "text_blocks": [
                    {
                        "type": "paragraph",
                        "snippet": (
                            "網訊、漸強實驗室與 Super8 的定位不同\n\n。"
                        ),
                    },
                    {
                        "type": "heading",
                        "snippet": "核心定位與協作模式差異",
                    },
                    {
                        "type": "list",
                        "list": [
                            {
                                "snippet": "網訊電通 (Telexpress)：",
                                "list": [
                                    {"snippet": "優勢\n：一站式 BPO 服務"},
                                    {"snippet": "協作特點：AI 與真人客服整合"},
                                ],
                            },
                            {
                                "snippet": "漸強實驗室 (Crescendo Lab)：",
                                "list": [
                                    {"snippet": "優勢：跨渠道行銷數據引擎"},
                                ],
                            },
                            {
                                "snippet": "Super8：",
                                "list": [
                                    {"snippet": "優勢：多代理對話式 CRM"},
                                ],
                            },
                        ],
                    },
                    {"type": "heading", "snippet": "數據架構對比"},
                    {
                        "type": "table",
                        "table": [
                            ["廠商", "數據架構"],
                            ["網訊電通", "BPO 與客服系統整合"],
                            ["漸強實驗室", "MAAC、CAAC、DAAC"],
                            ["Super8", "Agentic AI"],
                        ],
                        "detailed": [
                            [{"snippet": "廠商"}, {"snippet": "數據架構"}],
                            [
                                {"snippet": "網訊電通"},
                                {"snippet": "BPO 與客服系統整合"},
                            ],
                        ],
                        "formatted": [
                            {
                                "廠商": "網訊電通",
                                "數據架構": "BPO 與客服系統整合",
                            }
                        ],
                    },
                ],
                "references": [],
            }
        }

    provider = SerpApiGoogleAioAnswerProvider(
        GeoTrackingSettings(serpapi_api_key="test-key"),
        _recorder(),
        fetch_json=fetch_json,
    )

    response = await provider.generate_answer(_answer_request())

    assert response.raw_response == (
        "網訊、漸強實驗室與 Super8 的定位不同。\n\n"
        "## 核心定位與協作模式差異\n\n"
        "- 網訊電通 (Telexpress)：\n"
        "  - 優勢：一站式 BPO 服務\n"
        "  - 協作特點：AI 與真人客服整合\n"
        "- 漸強實驗室 (Crescendo Lab)：\n"
        "  - 優勢：跨渠道行銷數據引擎\n"
        "- Super8：\n"
        "  - 優勢：多代理對話式 CRM\n\n"
        "## 數據架構對比\n\n"
        "| 廠商 | 數據架構 |\n"
        "| --- | --- |\n"
        "| 網訊電通 | BPO 與客服系統整合 |\n"
        "| 漸強實驗室 | MAAC、CAAC、DAAC |\n"
        "| Super8 | Agentic AI |"
    )
    assert response.raw_response.count("BPO 與客服系統整合") == 1


@pytest.mark.parametrize(
    ("table_block", "expected"),
    [
        (
            {
                "type": "table",
                "detailed": [
                    [{"snippet": "廠商"}, {"snippet": "評分"}],
                    [{"snippet": "網訊"}, {"snippet": "5"}],
                ],
            },
            "| 廠商 | 評分 |\n| --- | --- |\n| 網訊 | 5 |",
        ),
        (
            {
                "type": "table",
                "formatted": [
                    {" vendor\n": "網訊", "score": 5},
                    {"vendor": "Super8", "score": 4},
                ],
            },
            (
                "| vendor | score |\n"
                "| --- | --- |\n"
                "| 網訊 | 5 |\n"
                "| Super8 | 4 |"
            ),
        ),
    ],
)
def test_ai_overview_table_uses_documented_fallbacks(
    table_block: dict[str, object],
    expected: str,
) -> None:
    assert providers_module._ai_overview_text(
        {"text_blocks": [table_block]}
    ) == expected


def test_ai_overview_renderer_handles_expandable_comparison_and_malformed_data(
) -> None:
    ai_overview = {
        "text_blocks": [
            {
                "type": "expandable",
                "title": "相機比較",
                "subtitle": "兩款產品的規格",
                "text_blocks": [
                    {"type": "paragraph", "snippet": "先比較解析度。"},
                    {
                        "type": "comparison",
                        "product_labels": ["產品 A", "產品 B"],
                        "comparison": [
                            {
                                "feature": "鏡頭 | 類型",
                                "values": ["廣角", "望遠"],
                            },
                            {"feature": "變焦", "values": ["2x"]},
                            "invalid",
                        ],
                    },
                ],
            },
            {"type": "unknown", "snippet": "仍應保留的文字"},
            {"type": "list", "list": [None, {"list": [{"snippet": "孤立子項"}]}]},
            None,
        ]
    }

    assert providers_module._ai_overview_text(ai_overview) == (
        "## 相機比較\n\n"
        "兩款產品的規格\n\n"
        "先比較解析度。\n\n"
        "|  | 產品 A | 產品 B |\n"
        "| --- | --- | --- |\n"
        "| 鏡頭 \\| 類型 | 廣角 | 望遠 |\n"
        "| 變焦 | 2x |  |\n\n"
        "仍應保留的文字\n\n"
        "- 孤立子項"
    )


def test_ai_overview_table_pads_ragged_rows_and_escapes_pipes() -> None:
    ai_overview = {
        "text_blocks": [
            {
                "type": "table",
                "table": [
                    ["欄位", "內容"],
                    ["A|B"],
                    [None, "值", "額外欄位"],
                ],
            }
        ]
    }

    assert providers_module._ai_overview_text(ai_overview) == (
        "| 欄位 | 內容 |  |\n"
        "| --- | --- | --- |\n"
        "| A\\|B |  |  |\n"
        "|  | 值 | 額外欄位 |"
    )


@pytest.mark.anyio
async def test_google_aio_provider_uses_distinct_operations_for_queries_in_same_run(
) -> None:
    recorder = _recorder()

    async def fetch_json(params: dict[str, str]) -> dict[str, object]:
        return {
            "ai_overview": {
                "text_blocks": [{"type": "paragraph", "snippet": "answer"}],
                "references": [],
            }
        }

    provider = SerpApiGoogleAioAnswerProvider(
        GeoTrackingSettings(serpapi_api_key="test-key"),
        recorder,
        fetch_json=fetch_json,
    )
    run_request_id = UUID("11111111-1111-4111-8111-111111111111")

    await provider.generate_answer(
        _answer_request().model_copy(update={"run_request_id": run_request_id})
    )
    await provider.generate_answer(
        _answer_request().model_copy(update={"run_request_id": run_request_id})
    )

    requests = list(recorder.requests.values())
    assert [request.request_number for request in requests] == [1, 1]
    assert len({request.operation_id for request in requests}) == 2
    assert {request.context.run_request_id for request in requests} == {run_request_id}


@pytest.mark.anyio
async def test_google_aio_provider_uses_page_token_second_request() -> None:
    calls: list[dict[str, str]] = []
    recorder = _recorder()

    async def fetch_json(params: dict[str, str]) -> dict[str, object]:
        calls.append(params)
        if params["engine"] == "google":
            return {"ai_overview": {"page_token": "token-123"}}
        return {
            "ai_overview": {
                "text_blocks": [{"type": "paragraph", "snippet": "第二段 AIO 回答。"}],
                "references": [
                    {
                        "title": "第二段來源",
                        "link": "https://example.com/second-source",
                    }
                ],
            }
        }

    provider = SerpApiGoogleAioAnswerProvider(
        GeoTrackingSettings(serpapi_api_key="test-key"),
        recorder,
        fetch_json=fetch_json,
    )

    response = await provider.generate_answer(_answer_request())

    assert [call["engine"] for call in calls] == ["google", "google_ai_overview"]
    assert calls[1]["page_token"] == "token-123"
    assert [item.request_kind for item in recorder.requests.values()] == [
        "initial",
        "page_token",
    ]
    assert {
        item.context.use_case for item in recorder.requests.values()
    } == {"google_ai_overview"}
    assert response.raw_response == "第二段 AIO 回答。"
    assert response.reference_urls == ["https://example.com/second-source"]


@pytest.mark.anyio
async def test_google_aio_provider_reports_no_aio_result() -> None:
    async def fetch_json(params: dict[str, str]) -> dict[str, object]:
        return {"search_metadata": {"status": "Success"}}

    provider = SerpApiGoogleAioAnswerProvider(
        GeoTrackingSettings(serpapi_api_key="test-key"),
        _recorder(),
        fetch_json=fetch_json,
    )

    with pytest.raises(ProviderRequestError) as exc_info:
        await provider.generate_answer(_answer_request())

    assert exc_info.value.code == "no_google_aio_result"


@pytest.mark.anyio
async def test_google_aio_provider_requires_api_key() -> None:
    provider = SerpApiGoogleAioAnswerProvider(
        GeoTrackingSettings(serpapi_api_key=""),
        _recorder(),
    )

    with pytest.raises(ProviderRequestError) as exc_info:
        await provider.generate_answer(_answer_request())

    assert exc_info.value.code == "serpapi_api_key_missing"


@pytest.mark.anyio
async def test_google_aio_provider_reuses_aiohttp_session() -> None:
    provider = SerpApiGoogleAioAnswerProvider(
        GeoTrackingSettings(serpapi_api_key="test-key"),
        _recorder(),
    )

    first_session = provider._client_session()
    second_session = provider._client_session()
    await provider.close()

    assert first_session is second_session
    assert first_session.closed


def _answer_request() -> AnswerRequest:
    return AnswerRequest(
        query_id="44444444-4444-4444-8444-444444444444",
        query_text="黃連膏 推薦",
        region=RegionCode.TAIWAN,
        language="zh-TW",
        market_type=MarketType.B2C,
        is_branded=False,
        system_prompt="",
    )


def _inspection_command() -> ProjectInspectionCommand:
    return ProjectInspectionCommand(
        project_url="https://www.kaiser.com.tw/",
        language="zh-TW",
    )


def _suggestion_command() -> ProjectSuggestionCommand:
    return ProjectSuggestionCommand(
        confirmed_project=ConfirmedProjectIdentity(
            source_url="https://www.kaiser.com.tw/",
            retrieved_url="https://www.kaiser.com.tw/",
            project_name="港香蘭藥廠股份有限公司",
            project_description="位於台灣的中藥製藥公司。",
            project_type="company",
            core_offerings=["科學中藥"],
        ),
        region=RegionCode.TAIWAN,
        language="zh-TW",
        market_type=MarketType.B2C,
    )


async def _no_fetched_page(url: str) -> None:
    return None
