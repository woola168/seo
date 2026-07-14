import json
from typing import Any

import pytest
import younilab_geo_tracking_infrastructure.project_discovery as discovery_module
from younilab_geo_tracking_application import (
    AnswerRequest,
    ConfirmedProjectIdentity,
    ProjectInspectionCommand,
    ProjectSuggestionCommand,
    ProviderRequestError,
    QueryAudience,
    VerifiedProjectIdentity,
)
from younilab_geo_tracking_domain import MarketType, ProviderCode, RegionCode
from younilab_geo_tracking_infrastructure import (
    GeminiProjectDiscoveryProvider,
    GeoTrackingSettings,
    SerpApiGoogleAioAnswerProvider,
)
from younilab_geo_tracking_infrastructure.providers import (
    _generate_with_reference_retry,
    _reference_retry_prompt,
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

    async def generate(contents: str, config: Any) -> FakeProjectDiscoveryResponse:
        calls.append((contents, config))
        return FakeProjectDiscoveryResponse(
            {
                "projectName": "港香蘭藥廠股份有限公司",
                "projectDescription": "位於台灣的中藥製藥公司。",
                "projectType": "company",
                "coreOfferings": ["科學中藥"],
                "targetAudiences": ["一般消費者"],
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
                "targetAudiences": ["Fitness consumers"],
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
                "targetAudiences": [],
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
        target_audiences=("一般消費者",),
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
        "audience": {
            "name": "B2C 消費",
            "description": "正在了解中藥產品的一般消費者",
        },
    }
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
        target_audiences=("一般消費者",),
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
                "targetAudiences": ["一般消費者"],
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
        target_audiences=tuple(inspection.identity.target_audiences),
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

    async def generate(contents: str) -> FakeResponse:
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
    assert calls[0] == "ambiguous supplier query"
    assert "previous response produced no grounding references" in calls[1]
    assert "ambiguous supplier query" in calls[1]


@pytest.mark.anyio
async def test_reference_retry_keeps_first_response_when_references_exist() -> None:
    calls: list[str] = []

    async def generate(contents: str) -> FakeResponse:
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
    assert calls == ["clear supplier query"]


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
async def test_google_aio_provider_uses_page_token_second_request() -> None:
    calls: list[dict[str, str]] = []

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
        fetch_json=fetch_json,
    )

    response = await provider.generate_answer(_answer_request())

    assert [call["engine"] for call in calls] == ["google", "google_ai_overview"]
    assert calls[1]["page_token"] == "token-123"
    assert response.raw_response == "第二段 AIO 回答。"
    assert response.reference_urls == ["https://example.com/second-source"]


@pytest.mark.anyio
async def test_google_aio_provider_reports_no_aio_result() -> None:
    async def fetch_json(params: dict[str, str]) -> dict[str, object]:
        return {"search_metadata": {"status": "Success"}}

    provider = SerpApiGoogleAioAnswerProvider(
        GeoTrackingSettings(serpapi_api_key="test-key"),
        fetch_json=fetch_json,
    )

    with pytest.raises(ProviderRequestError) as exc_info:
        await provider.generate_answer(_answer_request())

    assert exc_info.value.code == "no_google_aio_result"


@pytest.mark.anyio
async def test_google_aio_provider_requires_api_key() -> None:
    provider = SerpApiGoogleAioAnswerProvider(GeoTrackingSettings(serpapi_api_key=""))

    with pytest.raises(ProviderRequestError) as exc_info:
        await provider.generate_answer(_answer_request())

    assert exc_info.value.code == "serpapi_api_key_missing"


@pytest.mark.anyio
async def test_google_aio_provider_reuses_aiohttp_session() -> None:
    provider = SerpApiGoogleAioAnswerProvider(
        GeoTrackingSettings(serpapi_api_key="test-key")
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
            target_audiences=["一般消費者"],
        ),
        region=RegionCode.TAIWAN,
        language="zh-TW",
        market_type=MarketType.B2C,
        audience=QueryAudience(
            name="B2C 消費",
            description="正在了解中藥產品的一般消費者",
        ),
    )


async def _no_fetched_page(url: str) -> None:
    return None
