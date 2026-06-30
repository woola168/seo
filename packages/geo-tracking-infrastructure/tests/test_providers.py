import pytest
from younilab_geo_tracking_application import AnswerRequest, ProviderRequestError
from younilab_geo_tracking_domain import MarketType, ProviderCode, RegionCode
from younilab_geo_tracking_infrastructure import (
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
    def __init__(self, url: str | None) -> None:
        self.grounding_chunks = [FakeGroundingChunk(url)] if url else []
        self.web_search_queries = ["supplier search"] if url else []


class FakeGroundingChunk:
    def __init__(self, url: str | None) -> None:
        self.web = FakeWeb(url) if url else None


class FakeWeb:
    def __init__(self, url: str) -> None:
        self.uri = url
        self.title = "Reference title"


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
    provider = SerpApiGoogleAioAnswerProvider(
        GeoTrackingSettings(serpapi_api_key="")
    )

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
