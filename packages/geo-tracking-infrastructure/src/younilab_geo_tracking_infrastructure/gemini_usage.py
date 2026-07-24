from typing import Any

from younilab_provider_request_audit import ProviderRequestUsage


def gemini_request_usage(response: Any) -> ProviderRequestUsage | None:
    metadata = getattr(response, "usage_metadata", None)
    if metadata is None:
        return None
    output_token_count = _integer_value(metadata, "response_token_count")
    if output_token_count is None:
        output_token_count = _integer_value(metadata, "candidates_token_count")
    search_query_count = sum(
        len(getattr(grounding_metadata, "web_search_queries", None) or [])
        for candidate in (getattr(response, "candidates", None) or [])
        if (grounding_metadata := getattr(candidate, "grounding_metadata", None))
        is not None
    )
    return ProviderRequestUsage(
        input_token_count=_integer_value(metadata, "prompt_token_count"),
        output_token_count=output_token_count,
        total_token_count=_integer_value(metadata, "total_token_count"),
        cached_input_token_count=_integer_value(
            metadata,
            "cached_content_token_count",
        ),
        reasoning_token_count=_integer_value(metadata, "thoughts_token_count"),
        tool_input_token_count=_integer_value(
            metadata,
            "tool_use_prompt_token_count",
        ),
        traffic_type=_text_value(getattr(metadata, "traffic_type", None)),
        usage_metadata=_metadata_payload(metadata),
        meter_usage={"google_web_search_query": search_query_count},
    )


def _integer_value(value: Any, name: str) -> int | None:
    candidate = getattr(value, name, None)
    return candidate if isinstance(candidate, int) else None


def _text_value(value: Any) -> str | None:
    if value is None:
        return None
    raw_value = getattr(value, "value", value)
    return str(raw_value)


def _metadata_payload(metadata: Any) -> dict[str, Any]:
    model_dump = getattr(metadata, "model_dump", None)
    if callable(model_dump):
        payload = model_dump(mode="json", exclude_none=True)
        if isinstance(payload, dict):
            return payload
    names = (
        "prompt_token_count",
        "response_token_count",
        "candidates_token_count",
        "total_token_count",
        "cached_content_token_count",
        "thoughts_token_count",
        "tool_use_prompt_token_count",
        "traffic_type",
    )
    return {
        name: normalized
        for name in names
        if (normalized := _json_value(getattr(metadata, name, None))) is not None
    }


def _json_value(value: Any) -> str | int | float | bool | None:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raw_value = getattr(value, "value", None)
    if isinstance(raw_value, (str, int, float, bool)):
        return raw_value
    return str(value)
