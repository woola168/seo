import pytest
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
