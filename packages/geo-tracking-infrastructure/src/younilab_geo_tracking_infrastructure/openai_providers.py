import inspect
import json
from collections.abc import Callable, Mapping
from typing import Any

from pydantic import ValidationError
from younilab_geo_tracking_application import (
    ProviderRequestError,
    QueryDraft,
    QueryGenerationCommand,
    QueryResearchCommand,
    QueryResearchResult,
)
from younilab_provider_request_audit import (
    ProviderRequestContext,
    ProviderRequestExecutor,
    ProviderRequestFailure,
    ProviderRequestRecorder,
    ProviderRequestUsage,
)

from younilab_geo_tracking_infrastructure.config import GeoTrackingSettings
from younilab_geo_tracking_infrastructure.query_generation_validation import (
    merge_intent_coverage_drafts,
    missing_query_intents,
    validated_query_drafts_or_empty,
)


class OpenAIClientManager:
    def __init__(
        self,
        settings: GeoTrackingSettings,
        client_factory: Callable[[GeoTrackingSettings], Any] | None = None,
    ) -> None:
        self._settings = settings
        self._client_factory = client_factory
        self._client: Any | None = None

    async def get_client(self) -> Any:
        if self._client is not None:
            return self._client
        if not self._settings.openai_api_key and self._client_factory is None:
            raise ProviderRequestError("openai_api_key_missing")
        if self._client_factory is not None:
            self._client = self._client_factory(self._settings)
            return self._client

        from openai import AsyncOpenAI, DefaultAioHttpClient

        self._client = AsyncOpenAI(
            api_key=self._settings.openai_api_key,
            timeout=self._settings.openai_timeout_seconds,
            http_client=DefaultAioHttpClient(),
        )
        return self._client

    async def close(self) -> None:
        if self._client is None:
            return
        close = getattr(self._client, "close", None)
        if callable(close):
            result = close()
            if inspect.isawaitable(result):
                await result
        self._client = None


class OpenAIQueryGenerationProvider:
    def __init__(
        self,
        settings: GeoTrackingSettings,
        recorder: ProviderRequestRecorder,
        client_manager: OpenAIClientManager | None = None,
    ) -> None:
        self._settings = settings
        self._recorder = recorder
        self._client_manager = client_manager or OpenAIClientManager(settings)
        self._owns_client_manager = client_manager is None

    async def generate_drafts(
        self,
        command: QueryGenerationCommand,
    ) -> list[QueryDraft]:
        client = await self._client_manager.get_client()
        operation = ProviderRequestExecutor(
            self._recorder,
            ProviderRequestContext(
                platform_code="openai",
                provider_code="openai",
                provider_operation="responses.create",
                use_case="query_generation",
                source_service="geo-tracking-api",
                model=self._settings.openai_query_generation_model,
            ),
        )
        response = await operation.execute(
            lambda: client.responses.create(
                model=self._settings.openai_query_generation_model,
                input=_generation_input(command),
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "geo_query_draft_list",
                        "strict": True,
                        "schema": _query_draft_schema(),
                    }
                },
            ),
            request_kind="initial",
            classify_failure=_classify_openai_failure,
            read_usage=openai_request_usage,
        )
        drafts = validated_query_drafts_or_empty(
            command,
            _query_draft_items(response),
        )
        missing_intents = missing_query_intents(command, drafts)
        if missing_intents:
            repair_command = command.model_copy(
                update={
                    "intents": missing_intents,
                    "max_queries": len(missing_intents),
                }
            )
            repair_response = await operation.execute(
                lambda: client.responses.create(
                    model=self._settings.openai_query_generation_model,
                    input=_generation_input(repair_command),
                    text={
                        "format": {
                            "type": "json_schema",
                            "name": "geo_query_draft_list",
                            "strict": True,
                            "schema": _query_draft_schema(),
                        }
                    },
                ),
                request_kind="intent_coverage",
                classify_failure=_classify_openai_failure,
                read_usage=openai_request_usage,
            )
            repair_drafts = validated_query_drafts_or_empty(
                repair_command,
                _query_draft_items(repair_response),
            )
            drafts = merge_intent_coverage_drafts(
                command,
                drafts,
                repair_drafts,
            )
        if not drafts:
            raise ProviderRequestError("query_generation_constraints_invalid")
        return drafts

    async def close(self) -> None:
        if self._owns_client_manager:
            await self._client_manager.close()


class OpenAIQueryResearchProvider:
    def __init__(
        self,
        settings: GeoTrackingSettings,
        recorder: ProviderRequestRecorder,
        client_manager: OpenAIClientManager | None = None,
    ) -> None:
        self._settings = settings
        self._recorder = recorder
        self._client_manager = client_manager or OpenAIClientManager(settings)
        self._owns_client_manager = client_manager is None

    async def research(self, command: QueryResearchCommand) -> QueryResearchResult:
        client = await self._client_manager.get_client()
        operation = ProviderRequestExecutor(
            self._recorder,
            ProviderRequestContext(
                platform_code="openai",
                provider_code="openai",
                provider_operation="responses.create",
                use_case="query_research",
                source_service="geo-tracking-api",
                model=self._settings.openai_query_research_model,
                uses_grounding=True,
            ),
        )
        response = await operation.execute(
            lambda: client.responses.create(
                model=self._settings.openai_query_research_model,
                input=_research_input(command),
                tools=[{"type": "web_search"}],
                include=["web_search_call.action.sources"],
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "geo_query_research_output",
                        "strict": True,
                        "schema": _research_schema(),
                    }
                },
            ),
            request_kind="initial",
            classify_failure=_classify_openai_failure,
            read_usage=openai_request_usage,
        )
        parsed = _research_output(response)
        search_queries = _openai_search_queries(response)
        citation_urls = _openai_citation_urls(response)
        search_source_urls = _openai_search_source_urls(response)
        return QueryResearchResult(
            research_context=parsed["researchContext"],
            searched_keywords=search_queries or parsed["searchedKeywords"],
            source_urls=(citation_urls or search_source_urls or parsed["sourceUrls"]),
        )

    async def close(self) -> None:
        if self._owns_client_manager:
            await self._client_manager.close()


def _generation_input(command: QueryGenerationCommand) -> list[dict[str, str]]:
    from younilab_geo_tracking_infrastructure.providers import (
        _effective_language,
        _query_generation_prompt,
        _query_generation_system_prompt,
    )

    language = _effective_language(command.language, command.region)
    return [
        {
            "role": "system",
            "content": _query_generation_system_prompt(language),
        },
        {
            "role": "user",
            "content": _query_generation_prompt(command, language),
        },
    ]


def _research_input(command: QueryResearchCommand) -> list[dict[str, str]]:
    from younilab_geo_tracking_infrastructure.providers import (
        _effective_language,
        _query_research_prompt,
        _query_research_system_prompt,
    )

    language = _effective_language(command.language, command.region)
    return [
        {
            "role": "system",
            "content": _query_research_system_prompt(language).replace(
                "Google Search tool",
                "OpenAI web search tool",
            ),
        },
        {
            "role": "user",
            "content": _query_research_prompt(command, language),
        },
    ]


def _query_draft_schema() -> dict[str, Any]:
    from younilab_geo_tracking_infrastructure.providers import _GeminiQueryDraftList

    return _strict_json_schema(_GeminiQueryDraftList.model_json_schema())


def _research_schema() -> dict[str, Any]:
    from younilab_geo_tracking_infrastructure.providers import (
        _GeminiQueryResearchOutput,
    )

    return _strict_json_schema(_GeminiQueryResearchOutput.model_json_schema())


def _query_draft_items(response: Any) -> list[Any]:
    from younilab_geo_tracking_infrastructure.providers import _GeminiQueryDraftList

    try:
        parsed = json.loads(_response_text(response))
        return _GeminiQueryDraftList.model_validate(parsed).items
    except (json.JSONDecodeError, ValidationError) as exc:
        raise ProviderRequestError("openai_structured_output_invalid") from exc


def _research_output(response: Any) -> dict[str, Any]:
    from younilab_geo_tracking_infrastructure.providers import (
        _GeminiQueryResearchOutput,
    )

    try:
        parsed = _GeminiQueryResearchOutput.model_validate(
            json.loads(_response_text(response))
        )
    except (json.JSONDecodeError, ValidationError) as exc:
        raise ProviderRequestError("openai_structured_output_invalid") from exc
    return {
        "researchContext": parsed.researchContext,
        "searchedKeywords": parsed.searchedKeywords,
        "sourceUrls": parsed.sourceUrls,
    }


def _response_text(response: Any) -> str:
    output_text = _read_value(response, "output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text
    for output_item in _read_value(response, "output") or []:
        for content in _read_value(output_item, "content") or []:
            if _read_value(content, "type") == "output_text":
                text = _read_value(content, "text")
                if isinstance(text, str) and text.strip():
                    return text
    raise ProviderRequestError("openai_structured_output_missing")


def _openai_search_queries(response: Any) -> list[str]:
    queries: list[str] = []
    for item in _read_value(response, "output") or []:
        if _read_value(item, "type") != "web_search_call":
            continue
        action = _read_value(item, "action")
        action_queries = _read_value(action, "queries") or []
        for value in [_read_value(action, "query"), *action_queries]:
            if isinstance(value, str) and value and value not in queries:
                queries.append(value)
    return queries


def _openai_citation_urls(response: Any) -> list[str]:
    urls: list[str] = []
    for item in _read_value(response, "output") or []:
        for content in _read_value(item, "content") or []:
            for annotation in _read_value(content, "annotations") or []:
                url = _read_value(annotation, "url")
                if not isinstance(url, str):
                    url_citation = _read_value(annotation, "url_citation")
                    url = _read_value(url_citation, "url")
                if isinstance(url, str) and url and url not in urls:
                    urls.append(url)
    return urls


def _openai_search_source_urls(response: Any) -> list[str]:
    urls: list[str] = []
    for item in _read_value(response, "output") or []:
        if _read_value(item, "type") != "web_search_call":
            continue
        action = _read_value(item, "action")
        for source in _read_value(action, "sources") or []:
            url = _read_value(source, "url")
            if isinstance(url, str) and url and url not in urls:
                urls.append(url)
    return urls


def _strict_json_schema(value: Any) -> Any:
    if isinstance(value, dict):
        normalized = {key: _strict_json_schema(child) for key, child in value.items()}
        if normalized.get("type") == "object":
            normalized["additionalProperties"] = False
        return normalized
    if isinstance(value, list):
        return [_strict_json_schema(child) for child in value]
    return value


def openai_request_usage(response: Any) -> ProviderRequestUsage | None:
    usage = _read_value(response, "usage")
    if usage is None:
        return None
    input_details = _read_value(usage, "input_tokens_details")
    output_details = _read_value(usage, "output_tokens_details")
    return ProviderRequestUsage(
        input_token_count=_integer_value(usage, "input_tokens"),
        output_token_count=_integer_value(usage, "output_tokens"),
        total_token_count=_integer_value(usage, "total_tokens"),
        cached_input_token_count=_integer_value(input_details, "cached_tokens"),
        reasoning_token_count=_integer_value(output_details, "reasoning_tokens"),
        usage_metadata=_mapping_value(usage),
        meter_usage={
            "openai_web_search_call": sum(
                1
                for item in _read_value(response, "output") or []
                if _read_value(item, "type") == "web_search_call"
            )
        },
    )


def _classify_openai_failure(error: Exception) -> ProviderRequestFailure:
    status = _read_value(error, "status_code") or _read_value(error, "status")
    code = _read_value(error, "code")
    return ProviderRequestFailure(
        http_status=status if isinstance(status, int) else None,
        error_code=code if isinstance(code, str) else "openai_request_failed",
        error_type=error.__class__.__name__,
    )


def _read_value(value: Any, name: str) -> Any:
    if isinstance(value, Mapping):
        return value.get(name)
    return getattr(value, name, None)


def _integer_value(value: Any, name: str) -> int | None:
    candidate = _read_value(value, name)
    return candidate if isinstance(candidate, int) else None


def _mapping_value(value: Any) -> dict[str, Any] | None:
    if isinstance(value, Mapping):
        return dict(value)
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        result = model_dump(mode="json", exclude_none=True)
        if isinstance(result, dict):
            return result
    return None
