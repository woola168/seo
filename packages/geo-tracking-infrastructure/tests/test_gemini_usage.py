from enum import Enum
from types import SimpleNamespace

from younilab_geo_tracking_infrastructure.gemini_usage import gemini_request_usage


class _TrafficType(Enum):
    ON_DEMAND = "ON_DEMAND"


def test_gemini_usage_maps_tokens_and_search_queries_without_deduplication() -> None:
    metadata = SimpleNamespace(
        prompt_token_count=120,
        response_token_count=30,
        candidates_token_count=99,
        total_token_count=165,
        cached_content_token_count=20,
        thoughts_token_count=15,
        tool_use_prompt_token_count=12,
        traffic_type=_TrafficType.ON_DEMAND,
    )
    response = SimpleNamespace(
        usage_metadata=metadata,
        candidates=[
            SimpleNamespace(
                grounding_metadata=SimpleNamespace(
                    web_search_queries=["same query", "same query"]
                )
            ),
            SimpleNamespace(
                grounding_metadata=SimpleNamespace(
                    web_search_queries=["another query"]
                )
            ),
        ],
    )

    usage = gemini_request_usage(response)

    assert usage is not None
    assert usage.input_token_count == 120
    assert usage.output_token_count == 30
    assert usage.cached_input_token_count == 20
    assert usage.reasoning_token_count == 15
    assert usage.tool_input_token_count == 12
    assert usage.total_token_count == 165
    assert usage.traffic_type == "ON_DEMAND"
    assert usage.meter_usage == {"google_web_search_query": 3}
    assert usage.usage_metadata == {
        "prompt_token_count": 120,
        "response_token_count": 30,
        "candidates_token_count": 99,
        "total_token_count": 165,
        "cached_content_token_count": 20,
        "thoughts_token_count": 15,
        "tool_use_prompt_token_count": 12,
        "traffic_type": "ON_DEMAND",
    }


def test_gemini_usage_falls_back_to_candidates_token_count() -> None:
    response = SimpleNamespace(
        usage_metadata=SimpleNamespace(
            prompt_token_count=10,
            response_token_count=None,
            candidates_token_count=4,
        ),
        candidates=[],
    )

    usage = gemini_request_usage(response)

    assert usage is not None
    assert usage.output_token_count == 4


def test_gemini_usage_returns_none_when_sdk_usage_is_missing() -> None:
    assert gemini_request_usage(SimpleNamespace(candidates=[])) is None
