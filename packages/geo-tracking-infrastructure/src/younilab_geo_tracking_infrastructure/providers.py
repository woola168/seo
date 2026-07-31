import asyncio
import logging
import os
import random
import re
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from typing import Any

import aiohttp
import httpx
from google.genai.errors import APIError
from pydantic import BaseModel, Field
from younilab_provider_request_audit import (
    ProviderRequestContext,
    ProviderRequestExecutor,
    ProviderRequestFailure,
    ProviderRequestRecorder,
)
from younilab_geo_tracking_application import (
    AnswerProvider,
    AnswerRequest,
    AnswerResponse,
    DummyQueryGenerationProvider,
    DummyQueryResearchProvider,
    ProviderRequestError,
    QueryDraft,
    QueryGenerationCommand,
    QueryGenerationProvider,
    QueryIntent,
    QueryResearchCommand,
    QueryResearchProvider,
    QueryResearchResult,
    Reference,
)
from younilab_geo_tracking_application.prompt_templates import default_language
from younilab_geo_tracking_domain import MarketType, ProviderCode, RegionCode

from younilab_geo_tracking_infrastructure.config import (
    SERPAPI_LOCALE_PROFILES,
    GeoTrackingSettings,
    SerpApiLocaleProfile,
)
from younilab_geo_tracking_infrastructure.gemini_usage import (
    gemini_request_usage,
)


logger = logging.getLogger(__name__)

_GEMINI_MAX_API_CALLS = 3
_GEMINI_RETRYABLE_STATUS_CODES = frozenset({408, 429})
_GEMINI_RETRY_INITIAL_DELAY_SECONDS = 1.0
_GEMINI_HTTP_TIMEOUT_MILLISECONDS = 60_000
_GEMINI_ERROR_CODES = {
    400: "gemini_invalid_argument",
    401: "gemini_unauthenticated",
    403: "gemini_permission_denied",
    404: "gemini_not_found",
    408: "gemini_request_timeout",
    429: "gemini_resource_exhausted",
    499: "gemini_client_closed_request",
    500: "gemini_internal_error",
    502: "gemini_bad_gateway",
    503: "gemini_unavailable",
    504: "gemini_deadline_exceeded",
}
_GEMINI_RETRYABLE_TRANSPORT_ERRORS = (
    httpx.TimeoutException,
    httpx.NetworkError,
    httpx.RemoteProtocolError,
)


@dataclass
class _GeminiApiCallBudget:
    _generate: Callable[[str], Awaitable[Any]]
    _executor: ProviderRequestExecutor
    _call_count: int = 0

    def has_remaining_calls(self) -> bool:
        return self._call_count < _GEMINI_MAX_API_CALLS

    async def generate(self, contents: str, request_kind: str = "initial") -> Any:
        first_attempt = True
        while self.has_remaining_calls():
            self._call_count += 1
            try:
                return await self._executor.execute(
                    lambda: self._generate(contents),
                    request_kind=(
                        request_kind if first_attempt else "transient_retry"
                    ),
                    classify_failure=_classify_gemini_failure,
                    read_usage=gemini_request_usage,
                )
            except APIError as exc:
                await self._retry_or_raise(
                    exc,
                    error_code=_gemini_api_error_code(exc.code),
                    retryable=_is_retryable_gemini_api_error(exc.code),
                    status_code=exc.code,
                )
            except _GEMINI_RETRYABLE_TRANSPORT_ERRORS as exc:
                await self._retry_or_raise(
                    exc,
                    error_code=(
                        "gemini_request_timeout"
                        if isinstance(exc, httpx.TimeoutException)
                        else "gemini_network_error"
                    ),
                    retryable=True,
                )
            first_attempt = False
        raise ProviderRequestError("gemini_retry_budget_exhausted")

    async def _retry_or_raise(
        self,
        error: Exception,
        *,
        error_code: str,
        retryable: bool,
        status_code: int | None = None,
    ) -> None:
        if not retryable or not self.has_remaining_calls():
            raise ProviderRequestError(error_code) from error
        base_delay = _GEMINI_RETRY_INITIAL_DELAY_SECONDS * (
            2 ** (self._call_count - 1)
        )
        delay = base_delay + random.uniform(0, base_delay)
        logger.warning(
            (
                "Retrying Gemini API request after transient failure: "
                "attempt=%s statusCode=%s exceptionType=%s delaySeconds=%.3f"
            ),
            self._call_count,
            status_code,
            error.__class__.__name__,
            delay,
            extra={
                "attempt": self._call_count,
                "status_code": status_code,
                "exception_type": error.__class__.__name__,
                "delay_seconds": delay,
            },
        )
        await asyncio.sleep(delay)


def _is_retryable_gemini_api_error(status_code: int | None) -> bool:
    return status_code in _GEMINI_RETRYABLE_STATUS_CODES or (
        isinstance(status_code, int) and 500 <= status_code <= 599
    )


def _gemini_api_error_code(status_code: int | None) -> str:
    if status_code in _GEMINI_ERROR_CODES:
        return _GEMINI_ERROR_CODES[status_code]
    if isinstance(status_code, int) and 500 <= status_code <= 599:
        return "gemini_server_error"
    if isinstance(status_code, int) and 400 <= status_code <= 499:
        return "gemini_client_error"
    return "gemini_request_failed"


def _classify_gemini_failure(error: Exception) -> ProviderRequestFailure:
    status_code = error.code if isinstance(error, APIError) else None
    if isinstance(error, httpx.TimeoutException):
        error_code = "gemini_request_timeout"
    elif isinstance(error, _GEMINI_RETRYABLE_TRANSPORT_ERRORS):
        error_code = "gemini_network_error"
    else:
        error_code = _gemini_api_error_code(status_code)
    return ProviderRequestFailure(
        http_status=status_code,
        error_code=error_code,
        error_type=error.__class__.__name__,
    )


class _GeminiIntent(BaseModel):
    category: str = Field(
        description="Copy one user-provided intent category exactly."
    )
    description: str = Field(
        description="Copy the selected intent description exactly."
    )


class _GeminiAudience(BaseModel):
    name: str = Field(description="Copy the user-provided audience name exactly.")
    description: str = Field(
        description="Copy the user-provided audience description exactly."
    )


class _GeminiBrandMentionRules(BaseModel):
    shouldMentionOwnBrand: bool = Field(
        description="Copy whether the query should mention the user's own brand."
    )
    shouldMentionCompetitor: bool = Field(
        description="Copy whether the query should mention a competitor brand."
    )


class _GeminiQueryAttributes(BaseModel):
    intent: _GeminiIntent = Field(
        description=(
            "The selected intent used as the generation angle; "
            "do not classify or change it."
        )
    )
    keyword: str = Field(
        description="One seed keyword from the input keywords that guides this query."
    )
    topicName: str = Field(description="Copy one input topic name exactly.")
    topicDescription: str = Field(
        default="",
        description=(
            "Copy the selected topic description and use it as a generation "
            "constraint."
        ),
    )
    audience: _GeminiAudience = Field(
        description="The selected target audience; copy the input values exactly."
    )
    brandMentionRules: _GeminiBrandMentionRules = Field(
        description="Copy the input brand mention rules exactly."
    )


class _GeminiQueryDraft(BaseModel):
    attributes: _GeminiQueryAttributes = Field(
        description="Generation constraints copied from the provided input."
    )
    query: str = Field(
        description=(
            "A concise query that a real user would naturally type into a search "
            "engine or AI assistant to express one concrete need."
        )
    )
    keywords: list[str] = Field(
        default_factory=list,
        description=(
            "Seed keywords from the input keywords used by this query; "
            "do not invent keywords."
        ),
    )


class _GeminiQueryDraftList(BaseModel):
    items: list[_GeminiQueryDraft] = Field(
        description="Generated query candidates."
    )


class _GeminiQueryResearchOutput(BaseModel):
    researchContext: str
    searchedKeywords: list[str]
    sourceUrls: list[str]


class DummyAnswerProvider:
    async def generate_answer(self, request: AnswerRequest) -> AnswerResponse:
        branded_note = "branded" if request.is_branded else "non-branded"
        return AnswerResponse(
            provider=ProviderCode.DUMMY,
            surface="Dummy AI",
            model="dummy-answer-v1",
            raw_response=(
                f"[{request.region}/{request.language}/"
                f"{request.market_type}/{branded_note}] "
                f"Dummy response for: {request.query_text}"
            ),
            reference_urls=[],
        )


class SerpApiGoogleAioAnswerProvider:
    def __init__(
        self,
        settings: GeoTrackingSettings,
        recorder: ProviderRequestRecorder,
        fetch_json: Callable[[Mapping[str, str]], Awaitable[dict[str, Any]]]
        | None = None,
    ) -> None:
        self._settings = settings
        self._recorder = recorder
        self._fetch_json = fetch_json
        self._session: aiohttp.ClientSession | None = None

    async def generate_answer(self, request: AnswerRequest) -> AnswerResponse:
        if not self._settings.serpapi_api_key:
            raise ProviderRequestError("serpapi_api_key_missing")

        profile = _serpapi_locale_profile(request.region)
        language = request.language or profile.default_language
        operation = ProviderRequestExecutor(
            self._recorder,
            ProviderRequestContext(
                platform_code="google_aio",
                provider_code="serpapi",
                provider_operation="search",
                use_case="google_ai_overview",
                source_service="geo-tracking-api",
                model="serpapi-google-ai-overview",
                query_id=request.query_id,
                run_request_id=request.run_request_id,
                tenant_id=request.tenant_id,
                project_id=request.project_id,
                job_id=request.job_id,
            ),
        )
        search_payload = await self._request_serpapi(
            {
                "engine": "google",
                "q": request.query_text,
                "hl": _serpapi_hl(language, profile),
                "gl": profile.gl,
                "location": profile.location,
            },
            operation,
            request_kind="initial",
        )
        ai_overview = await self._resolve_ai_overview(search_payload, operation)
        raw_response = _ai_overview_text(ai_overview)
        references = _ai_overview_references(ai_overview)
        if not raw_response:
            raise ProviderRequestError("no_google_aio_result")

        return AnswerResponse(
            provider=ProviderCode.GOOGLE_AIO,
            surface="Google AI Overview",
            model="serpapi-google-ai-overview",
            raw_response=raw_response,
            reference_urls=[reference.url for reference in references],
            references=references,
        )

    async def close(self) -> None:
        if self._session is not None:
            await self._session.close()
            self._session = None

    async def _resolve_ai_overview(
        self,
        search_payload: dict[str, Any],
        operation: ProviderRequestExecutor,
    ) -> dict[str, Any]:
        ai_overview = _payload_ai_overview(search_payload)
        if _has_ai_overview_content(ai_overview):
            return ai_overview

        page_token = ai_overview.get("page_token")
        if isinstance(page_token, str) and page_token:
            ai_overview_payload = await self._request_serpapi(
                {
                    "engine": "google_ai_overview",
                    "page_token": page_token,
                },
                operation,
                request_kind="page_token",
            )
            ai_overview = _payload_ai_overview(ai_overview_payload)
            if _has_ai_overview_content(ai_overview):
                return ai_overview

        raise ProviderRequestError("no_google_aio_result")

    async def _request_serpapi(
        self,
        params: Mapping[str, str],
        operation: ProviderRequestExecutor,
        *,
        request_kind: str,
    ) -> dict[str, Any]:
        request_params = {**params, "api_key": self._settings.serpapi_api_key}
        if self._fetch_json is not None:
            return await operation.execute(
                lambda: self._fetch_json(request_params),
                request_kind=request_kind,
            )

        async def send() -> dict[str, Any]:
            session = self._client_session()
            try:
                async with session.get(
                    "https://serpapi.com/search.json",
                    params=request_params,
                ) as response:
                    payload = await response.json(content_type=None)
            except aiohttp.ClientError as exc:
                raise ProviderRequestError("serpapi_request_failed") from exc
            if response.status >= 400 or not isinstance(payload, dict):
                raise ProviderRequestError(
                    "serpapi_request_failed",
                    status_code=response.status,
                )
            if payload.get("error"):
                raise ProviderRequestError(
                    "serpapi_request_failed",
                    status_code=response.status,
                )
            return payload

        return await operation.execute(
            send,
            request_kind=request_kind,
            read_http_status=lambda _: 200,
        )

    def _client_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(
                total=self._settings.serpapi_timeout_seconds
            )
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session


def _serpapi_locale_profile(region: RegionCode) -> SerpApiLocaleProfile:
    try:
        return SERPAPI_LOCALE_PROFILES[region]
    except KeyError as exc:
        raise ProviderRequestError("serpapi_locale_not_supported") from exc


def _serpapi_hl(language: str, profile: SerpApiLocaleProfile) -> str:
    normalized = language.strip().lower()
    if normalized in {"zh-tw", "zh_tw"}:
        return "zh-tw"
    if normalized.startswith("en"):
        return "en"
    if normalized.startswith("ja"):
        return "ja"
    return profile.hl


def _payload_ai_overview(payload: dict[str, Any]) -> dict[str, Any]:
    ai_overview = payload.get("ai_overview")
    return ai_overview if isinstance(ai_overview, dict) else {}


def _has_ai_overview_content(ai_overview: dict[str, Any]) -> bool:
    return bool(ai_overview.get("text_blocks") or ai_overview.get("references"))


def _ai_overview_text(ai_overview: dict[str, Any]) -> str:
    return "\n\n".join(
        _render_ai_overview_blocks(ai_overview.get("text_blocks"))
    ).strip()


def _render_ai_overview_blocks(
    value: Any,
    *,
    heading_level: int = 2,
) -> list[str]:
    if not isinstance(value, list):
        return []
    rendered: list[str] = []
    for block in value:
        if not isinstance(block, dict):
            continue
        content = _render_ai_overview_block(block, heading_level=heading_level)
        if content:
            rendered.append(content)
    return rendered


def _render_ai_overview_block(
    block: dict[str, Any],
    *,
    heading_level: int,
) -> str:
    block_type = block.get("type")
    snippet = _clean_ai_overview_text(block.get("snippet"))
    if block_type == "heading":
        if not snippet:
            return ""
        marker = "#" * min(max(heading_level, 1), 6)
        return f"{marker} {snippet}"
    if block_type == "list":
        list_text = "\n".join(_ai_overview_list_lines(block.get("list")))
        return "\n".join(part for part in (snippet, list_text) if part)
    if block_type == "table":
        table_text = _render_markdown_table(_ai_overview_table_rows(block))
        return "\n\n".join(part for part in (snippet, table_text) if part)
    if block_type == "expandable":
        return _render_ai_overview_expandable(block, heading_level=heading_level)
    if block_type == "comparison":
        comparison = _render_ai_overview_comparison(block)
        return "\n\n".join(part for part in (snippet, comparison) if part)
    return snippet


def _render_ai_overview_expandable(
    block: dict[str, Any],
    *,
    heading_level: int,
) -> str:
    sections: list[str] = []
    title = _clean_ai_overview_text(block.get("title"))
    if title:
        marker = "#" * min(max(heading_level, 1), 6)
        sections.append(f"{marker} {title}")
    subtitle = _clean_ai_overview_text(block.get("subtitle"))
    if subtitle:
        sections.append(subtitle)
    sections.extend(
        _render_ai_overview_blocks(
            block.get("text_blocks"),
            heading_level=min(heading_level + 1, 6),
        )
    )
    return "\n\n".join(sections)


def _ai_overview_list_lines(value: Any, *, depth: int = 0) -> list[str]:
    if not isinstance(value, list):
        return []
    lines: list[str] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        title = _clean_ai_overview_text(item.get("title"))
        snippet = _clean_ai_overview_text(item.get("snippet"))
        label = _join_ai_overview_text(title, snippet)
        if label:
            lines.append(f"{'  ' * depth}- {label}")
        nested_depth = depth + 1 if label else depth
        lines.extend(
            _ai_overview_list_lines(item.get("list"), depth=nested_depth)
        )
    return lines


def _join_ai_overview_text(first: str, second: str) -> str:
    if not first:
        return second
    if not second:
        return first
    if second[0] in ",.;:!?，。；：！？、":
        return f"{first}{second}"
    return f"{first} {second}"


def _ai_overview_table_rows(block: dict[str, Any]) -> list[list[str]]:
    rows = _ai_overview_plain_table_rows(block.get("table"))
    if rows:
        return rows
    rows = _ai_overview_detailed_table_rows(block.get("detailed"))
    if rows:
        return rows
    return _ai_overview_formatted_table_rows(block.get("formatted"))


def _ai_overview_plain_table_rows(value: Any) -> list[list[str]]:
    if not isinstance(value, list):
        return []
    rows: list[list[str]] = []
    for row in value:
        if not isinstance(row, list):
            continue
        cells = [_ai_overview_table_cell(cell) for cell in row]
        if any(cells):
            rows.append(cells)
    return rows


def _ai_overview_detailed_table_rows(value: Any) -> list[list[str]]:
    if not isinstance(value, list):
        return []
    rows: list[list[str]] = []
    for row in value:
        if not isinstance(row, list):
            continue
        cells = [
            _clean_ai_overview_text(cell.get("snippet"))
            if isinstance(cell, dict)
            else ""
            for cell in row
        ]
        if any(cells):
            rows.append(cells)
    return rows


def _ai_overview_formatted_table_rows(value: Any) -> list[list[str]]:
    if not isinstance(value, list):
        return []
    records = [item for item in value if isinstance(item, dict)]
    headers: list[str] = []
    for record in records:
        for key in record:
            header = _clean_ai_overview_text(key)
            if header and header not in headers:
                headers.append(header)
    if not headers:
        return []
    rows = [headers]
    for record in records:
        values_by_header = {
            _clean_ai_overview_text(key): value
            for key, value in record.items()
            if _clean_ai_overview_text(key)
        }
        rows.append(
            [
                _ai_overview_table_cell(values_by_header.get(header))
                for header in headers
            ]
        )
    return rows


def _render_ai_overview_comparison(block: dict[str, Any]) -> str:
    labels = block.get("product_labels")
    if not isinstance(labels, list):
        return ""
    clean_labels = [_ai_overview_table_cell(label) for label in labels]
    if not any(clean_labels):
        return ""
    comparison = block.get("comparison")
    if not isinstance(comparison, list):
        return ""
    rows = [["", *clean_labels]]
    for item in comparison:
        if not isinstance(item, dict):
            continue
        feature = _clean_ai_overview_text(item.get("feature"))
        values = item.get("values")
        clean_values = (
            [_ai_overview_table_cell(value) for value in values]
            if isinstance(values, list)
            else []
        )
        if feature or any(clean_values):
            rows.append([feature, *clean_values])
    if len(rows) == 1:
        return ""
    return _render_markdown_table(rows)


def _render_markdown_table(rows: list[list[str]]) -> str:
    if not rows:
        return ""
    column_count = max(len(row) for row in rows)
    normalized_rows = [row + [""] * (column_count - len(row)) for row in rows]
    escaped_rows = [
        [cell.replace("|", "\\|") for cell in row]
        for row in normalized_rows
    ]
    rendered = [_markdown_table_row(escaped_rows[0])]
    rendered.append(_markdown_table_row(["---"] * column_count))
    rendered.extend(_markdown_table_row(row) for row in escaped_rows[1:])
    return "\n".join(rendered)


def _markdown_table_row(cells: list[str]) -> str:
    return f"| {' | '.join(cells)} |"


def _ai_overview_table_cell(value: Any) -> str:
    if isinstance(value, str):
        return _clean_ai_overview_text(value)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(value)
    return ""


def _clean_ai_overview_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    text = re.sub(r"\s+", " ", value.strip())
    return re.sub(r"\s+([,.;:!?，。；：！？、])", r"\1", text)


def _clean_text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _ai_overview_references(ai_overview: dict[str, Any]) -> list[Reference]:
    references = ai_overview.get("references")
    if not isinstance(references, list):
        return []
    references_by_url: dict[str, Reference] = {}
    for item in references:
        if not isinstance(item, dict):
            continue
        link = _clean_text(item.get("link"))
        if not link:
            continue
        title = _clean_text(item.get("title"))
        references_by_url.setdefault(
            link,
            Reference(url=link, title=title or None),
        )
    return list(references_by_url.values())


class GeminiVertexAnswerProvider:
    def __init__(
        self,
        settings: GeoTrackingSettings,
        recorder: ProviderRequestRecorder,
    ) -> None:
        self._settings = settings
        self._recorder = recorder

    async def generate_answer(self, request: AnswerRequest) -> AnswerResponse:
        from google import genai
        from google.genai import types

        project_id = self._settings.resolve_vertex_project()
        if not project_id:
            raise RuntimeError(
                "VERTEX_AI_PROJECT or Vertex credentials project_id is required"
            )
        if self._settings.vertex_credentials_path:
            os.environ.setdefault(
                "GOOGLE_APPLICATION_CREDENTIALS",
                self._settings.vertex_credentials_path,
            )
        client = genai.Client(
            vertexai=True,
            project=project_id,
            location=self._settings.vertex_location,
            http_options=types.HttpOptions(
                retry_options=types.HttpRetryOptions(attempts=1),
                timeout=_GEMINI_HTTP_TIMEOUT_MILLISECONDS,
            ),
        )
        config = types.GenerateContentConfig(
            temperature=self._settings.gemini_temperature,
            system_instruction=request.system_prompt,
            tools=[types.Tool(google_search=types.GoogleSearch())],
            thinking_config=types.ThinkingConfig(
                thinking_level=self._settings.gemini_thinking_level.upper(),
            ),
        )
        executor = ProviderRequestExecutor(
            self._recorder,
            ProviderRequestContext(
                platform_code="gemini",
                provider_code="google_vertex_ai",
                provider_operation="generate_content",
                use_case="geo_query_answer",
                source_service="geo-tracking-api",
                model=self._settings.gemini_model,
                provider_region=self._settings.vertex_location,
                uses_grounding=True,
                tenant_id=request.tenant_id,
                project_id=request.project_id,
                job_id=request.job_id,
                query_id=request.query_id,
                run_request_id=request.run_request_id,
            ),
        )
        api_call_budget = _GeminiApiCallBudget(
            lambda contents: self._generate_content(client, contents, config),
            executor,
        )
        try:
            response, references = await _generate_with_reference_retry(
                api_call_budget.generate,
                request.query_text,
                request.language,
                has_remaining_calls=api_call_budget.has_remaining_calls,
            )
        finally:
            client.close()
        return AnswerResponse(
            provider=ProviderCode.GEMINI,
            surface="Gemini",
            model=self._settings.gemini_model,
            raw_response=response.text or "",
            reference_urls=[reference.url for reference in references],
            references=references,
        )

    async def _generate_content(
        self,
        client: Any,
        contents: str,
        config: Any,
    ) -> Any:
        return await asyncio.to_thread(
            client.models.generate_content,
            model=self._settings.gemini_model,
            contents=contents,
            config=config,
        )


class GeminiQueryGenerationProvider:
    def __init__(self, settings: GeoTrackingSettings, recorder: ProviderRequestRecorder) -> None:
        self._settings = settings
        self._recorder = recorder

    async def generate_drafts(
        self,
        command: QueryGenerationCommand,
    ) -> list[QueryDraft]:
        from google import genai
        from google.genai import types

        project_id = self._settings.resolve_vertex_project()
        if not project_id:
            raise RuntimeError(
                "VERTEX_AI_PROJECT or Vertex credentials project_id is required"
            )
        if self._settings.vertex_credentials_path:
            os.environ.setdefault(
                "GOOGLE_APPLICATION_CREDENTIALS",
                self._settings.vertex_credentials_path,
            )
        client = genai.Client(
            vertexai=True,
            project=project_id,
            location=self._settings.vertex_location,
            http_options=types.HttpOptions(
                retry_options=types.HttpRetryOptions(attempts=1),
            ),
        )
        language = _effective_language(command.language, command.region)
        config = types.GenerateContentConfig(
            temperature=self._settings.gemini_temperature,
            system_instruction=_query_generation_system_prompt(language),
            response_mime_type="application/json",
            response_schema=_GeminiQueryDraftList,
            thinking_config=types.ThinkingConfig(
                thinking_level=self._settings.gemini_thinking_level.upper(),
            ),
        )
        operation = ProviderRequestExecutor(
            self._recorder,
            ProviderRequestContext(
                platform_code="gemini",
                provider_code="google_vertex_ai",
                provider_operation="generate_content",
                use_case="query_generation",
                source_service="geo-tracking-api",
                model=self._settings.gemini_model,
                provider_region=self._settings.vertex_location,
            ),
        )
        try:
            response = await operation.execute(
                lambda: asyncio.to_thread(
                    client.models.generate_content,
                    model=self._settings.gemini_model,
                    contents=_query_generation_prompt(command, language),
                    config=config,
                ),
                request_kind="initial",
                classify_failure=_classify_gemini_failure,
                read_usage=gemini_request_usage,
            )
            drafts = _query_drafts_from_gemini(
                command,
                _gemini_query_draft_list(response),
            )
            missing_intents = _missing_query_intents(command, drafts)
            if missing_intents:
                repair_command = command.model_copy(
                    update={
                        "intents": missing_intents,
                        "max_queries": len(missing_intents),
                    }
                )
                repair_response = await operation.execute(
                    lambda: asyncio.to_thread(
                        client.models.generate_content,
                        model=self._settings.gemini_model,
                        contents=_query_generation_prompt(repair_command, language),
                        config=config,
                    ),
                    request_kind="intent_coverage",
                    classify_failure=_classify_gemini_failure,
                    read_usage=gemini_request_usage,
                )
                repair_drafts = _query_drafts_from_gemini(
                    repair_command,
                    _gemini_query_draft_list(repair_response),
                )
                drafts = _merge_intent_coverage_drafts(
                    command,
                    drafts,
                    repair_drafts,
                )
        finally:
            client.close()
        return drafts


class GeminiQueryResearchProvider:
    def __init__(self, settings: GeoTrackingSettings, recorder: ProviderRequestRecorder) -> None:
        self._settings = settings
        self._recorder = recorder

    async def research(self, command: QueryResearchCommand) -> QueryResearchResult:
        from google import genai
        from google.genai import types

        project_id = self._settings.resolve_vertex_project()
        if not project_id:
            raise RuntimeError(
                "VERTEX_AI_PROJECT or Vertex credentials project_id is required"
            )
        if self._settings.vertex_credentials_path:
            os.environ.setdefault(
                "GOOGLE_APPLICATION_CREDENTIALS",
                self._settings.vertex_credentials_path,
            )
        client = genai.Client(
            vertexai=True,
            project=project_id,
            location=self._settings.vertex_location,
            http_options=types.HttpOptions(
                retry_options=types.HttpRetryOptions(attempts=1),
            ),
        )
        language = _effective_language(command.language, command.region)
        config = types.GenerateContentConfig(
            temperature=self._settings.gemini_temperature,
            system_instruction=_query_research_system_prompt(language),
            tools=[types.Tool(google_search=types.GoogleSearch())],
            response_mime_type="application/json",
            response_schema=_GeminiQueryResearchOutput,
            thinking_config=types.ThinkingConfig(
                thinking_level=self._settings.gemini_thinking_level.upper(),
            ),
        )
        operation = ProviderRequestExecutor(
            self._recorder,
            ProviderRequestContext(
                platform_code="gemini",
                provider_code="google_vertex_ai",
                provider_operation="generate_content",
                use_case="query_research",
                source_service="geo-tracking-api",
                model=self._settings.gemini_model,
                provider_region=self._settings.vertex_location,
                uses_grounding=True,
            ),
        )
        try:
            response = await operation.execute(
                lambda: asyncio.to_thread(
                    client.models.generate_content,
                    model=self._settings.gemini_model,
                    contents=_query_research_prompt(command, language),
                    config=config,
                ),
                request_kind="initial",
                classify_failure=_classify_gemini_failure,
                read_usage=gemini_request_usage,
            )
        finally:
            client.close()
        parsed = response.parsed
        if not isinstance(parsed, _GeminiQueryResearchOutput):
            parsed = _GeminiQueryResearchOutput.model_validate_json(
                response.text or "{}"
            )
        grounding_references = _grounding_references(response)
        search_queries = _grounding_search_queries(response)
        return QueryResearchResult(
            research_context=parsed.researchContext,
            searched_keywords=parsed.searchedKeywords or search_queries,
            source_urls=parsed.sourceUrls
            or [reference.url for reference in grounding_references],
        )


def build_answer_provider(
    settings: GeoTrackingSettings,
    recorder: ProviderRequestRecorder,
) -> AnswerProvider:
    if settings.provider == ProviderCode.GEMINI:
        return GeminiVertexAnswerProvider(settings, recorder)
    if settings.provider == ProviderCode.GOOGLE_AIO:
        return SerpApiGoogleAioAnswerProvider(settings, recorder)
    return DummyAnswerProvider()


def build_answer_providers(
    settings: GeoTrackingSettings,
    recorder: ProviderRequestRecorder,
) -> dict[ProviderCode, AnswerProvider]:
    return {
        ProviderCode.DUMMY: DummyAnswerProvider(),
        ProviderCode.GEMINI: GeminiVertexAnswerProvider(settings, recorder),
        ProviderCode.GOOGLE_AIO: SerpApiGoogleAioAnswerProvider(settings, recorder),
    }


def build_query_research_providers(
    settings: GeoTrackingSettings,
    recorder: ProviderRequestRecorder,
) -> dict[ProviderCode, QueryResearchProvider]:
    return {
        ProviderCode.DUMMY: DummyQueryResearchProvider(),
        ProviderCode.GEMINI: GeminiQueryResearchProvider(settings, recorder),
    }


def build_query_generation_providers(
    settings: GeoTrackingSettings,
    recorder: ProviderRequestRecorder,
) -> dict[ProviderCode, QueryGenerationProvider]:
    return {
        ProviderCode.DUMMY: DummyQueryGenerationProvider(),
        ProviderCode.GEMINI: GeminiQueryGenerationProvider(settings, recorder),
    }


def _query_generation_system_prompt(language: str | None) -> str:
    if language == "en-US":
        return (
            "You generate AI-search query candidates for GEO "
            "(Generative Engine Optimization) tracking. Write each candidate as "
            "something a real user in the specified audience and market would "
            "naturally type into a search engine or AI assistant, not as SEO or "
            "marketing copy. Express one concrete need per query. Prefer concise, "
            "everyday wording; short keyword fragments and complete questions are "
            "both valid. Avoid report titles, campaign briefs, procurement prose, "
            "stacked clauses, and forcing unrelated input constraints into one "
            "query. Use the provided JSON parameters and optional researchContext "
            "as context, obey explicit brandMentionRules, and classify each finished "
            "query with its most fitting selected intent."
        )
    return (
        "你負責產生 GEO（Generative Engine Optimization）追蹤用的"
        " AI 搜尋 query 候選。每一筆都要像指定 audience 與 market 中的真實"
        "使用者會在搜尋引擎或 AI 助理輸入的內容，而不是 SEO 或行銷文案。"
        "每筆 query 只表達一個具體需求，優先使用簡潔、日常的措辭；短關鍵字"
        "片段與完整問句都可以。避免報告標題、活動企劃、採購公文式語氣、堆疊"
        "多個子句，以及為了塞入條件而把不相關資訊放進同一筆 query。請將提供"
        "的 JSON 參數與可選 researchContext 作為情境，遵守明確的"
        " brandMentionRules，並在完成 query 後標示最符合的已選 intent。"
    )


def _effective_language(language: str | None, region: RegionCode) -> str:
    return language or default_language(region)


def _query_generation_prompt(
    command: QueryGenerationCommand,
    language: str,
) -> str:
    import json

    payload = {
        "brand": {
            "ownBrandName": command.brand_name,
            "competitorBrands": command.competitor_brands,
        },
        "market": {
            "region": command.region,
            "language": language,
            "marketType": command.market_type,
        },
        "keywords": command.keywords,
        "topics": [
            topic.model_dump(mode="json", by_alias=True)
            for topic in _command_topics(command)
        ],
        "intents": [
            intent.model_dump(mode="json", by_alias=True) for intent in command.intents
        ],
        "audience": command.audience.model_dump(mode="json", by_alias=True),
        "brandMentionRules": command.brand_mention_rules.model_dump(
            mode="json",
            by_alias=True,
        ),
        "generation": {
            "maxQueries": command.max_queries,
            "queryLanguage": language,
        },
        "intentGuidance": _intent_generation_guidance(language),
        "researchContext": command.research_context or "",
    }
    return json.dumps(payload, ensure_ascii=False)


def _query_drafts_from_gemini(
    command: QueryGenerationCommand,
    parsed: _GeminiQueryDraftList,
) -> list[QueryDraft]:
    allowed_topics = command.topic_names or _default_topic_names(command.market_type)
    drafts: list[QueryDraft] = []
    for item in parsed.items[: command.max_queries]:
        attributes = item.attributes
        intent = _matching_intent(command, attributes.intent)
        allowed_topics = _command_topics(command)
        topic = _matching_topic(attributes.topicName, allowed_topics)
        drafts.append(
            QueryDraft(
                attributes={
                    "intent": intent,
                    "keyword": _matching_value(attributes.keyword, command.keywords),
                    "topicName": topic.name,
                    "topicDescription": topic.description,
                    "audience": command.audience,
                    "brandMentionRules": command.brand_mention_rules,
                },
                query=item.query,
                keywords=_matching_keywords(item.keywords, command.keywords),
            )
        )
    return drafts


def _gemini_query_draft_list(response: Any) -> _GeminiQueryDraftList:
    parsed = response.parsed
    if isinstance(parsed, _GeminiQueryDraftList):
        return parsed
    return _GeminiQueryDraftList.model_validate_json(response.text or "{}")


def _missing_query_intents(
    command: QueryGenerationCommand,
    drafts: list[QueryDraft],
) -> list[QueryIntent]:
    if command.max_queries < len(command.intents):
        return []
    generated_categories = {draft.attributes.intent.category for draft in drafts}
    missing: list[QueryIntent] = []
    for intent in command.intents:
        if (
            intent.category not in generated_categories
            and all(item.category != intent.category for item in missing)
        ):
            missing.append(intent)
    return missing


def _merge_intent_coverage_drafts(
    command: QueryGenerationCommand,
    initial_drafts: list[QueryDraft],
    repair_drafts: list[QueryDraft],
) -> list[QueryDraft]:
    selected_categories = list(
        dict.fromkeys(intent.category for intent in command.intents)
    )
    drafts_by_category: dict[str, QueryDraft] = {}
    for draft in [*initial_drafts, *repair_drafts]:
        category = draft.attributes.intent.category
        if category in selected_categories and category not in drafts_by_category:
            drafts_by_category[category] = draft
    missing = [
        category for category in selected_categories if category not in drafts_by_category
    ]
    if missing:
        raise ProviderRequestError("query_intent_coverage_failed")

    required = [drafts_by_category[category] for category in selected_categories]
    required_ids = {id(draft) for draft in required}
    extras = [draft for draft in initial_drafts if id(draft) not in required_ids]
    return [*required, *extras][: command.max_queries]


def _command_topics(command: QueryGenerationCommand) -> list[Any]:
    if command.topics:
        return command.topics
    topic_names = command.topic_names or _default_topic_names(command.market_type)
    return [_TopicLike(name=name, description="") for name in topic_names]


class _TopicLike(BaseModel):
    name: str
    description: str = ""


def _matching_intent(
    command: QueryGenerationCommand,
    intent: _GeminiIntent,
) -> QueryIntent:
    for candidate in command.intents:
        if candidate.category == intent.category:
            return candidate
    return QueryIntent(category=intent.category, description=intent.description)


def _intent_generation_guidance(language: str) -> list[str]:
    if language == "en-US":
        return [
            "Treat every selected intent equally; array order does not indicate priority.",
            "When maxQueries allows, generate at least one query for every selected intent.",
            "When maxQueries is lower than the number of selected intents, choose the most relevant intents from the keyword, topic, audience, and market context.",
            "Allocate remaining queries naturally; equal distribution is not required.",
        ]
    return [
        "所有選取的 intent 皆同等重要；陣列順序不代表優先順序。",
        "當 maxQueries 容量足夠時，每個選取的 intent 至少生成一筆 query。",
        "當 maxQueries 少於選取的 intent 數量時，依 keyword、topic、audience 與 market context 選擇最相關的 intent。",
        "其餘 query 依情境自然分配，不要求平均分配。",
    ]


def _matching_value(value: str, allowed_values: list[str]) -> str:
    if value in allowed_values:
        return value
    for allowed_value in allowed_values:
        if allowed_value and allowed_value in value:
            return allowed_value
    return allowed_values[0]


def _matching_keywords(values: list[str], allowed_values: list[str]) -> list[str]:
    keywords: list[str] = []
    for value in values:
        matched = _matching_value(value, allowed_values)
        if matched not in keywords:
            keywords.append(matched)
    return keywords or [allowed_values[0]]


def _matching_topic(value: str, allowed_topics: list[Any]) -> Any:
    for topic in allowed_topics:
        if value == topic.name:
            return topic
    for topic in allowed_topics:
        if topic.name and topic.name in value:
            return topic
    return allowed_topics[0]


def _default_topic_names(market_type: MarketType) -> list[str]:
    if market_type == MarketType.B2B_PROCUREMENT:
        return ["品牌型", "產品型", "採購評估"]
    return ["品牌型", "產品型", "資訊型"]


def _query_research_system_prompt(language: str | None) -> str:
    if language == "en-US":
        return (
            "You research current search language used by real users for GEO query "
            "generation. You must use the Google Search tool as a reference. Look "
            "for short keyword fragments, natural questions, pain points, "
            "comparisons, recommendation wording, and related-question or "
            "related-search phrasing when available. Keep only language relevant to "
            "the specified brand, audience, keywords, and market; exclude adjacent "
            "but irrelevant needs. In researchContext, distinguish wording observed "
            "in search references from wording you inferred. Do not fabricate "
            "search-volume claims. Return only structured JSON with researchContext, "
            "searchedKeywords, and sourceUrls."
        )
    return (
        "你負責研究真實使用者目前用於搜尋的語言，供 GEO query generation"
        " 使用。"
        "你必須使用 Google Search tool 作為 reference。"
        "研究短關鍵字片段、自然問句、痛點、比較、推薦，以及可取得時的相關問題"
        "或相關搜尋措辭。只保留與指定品牌、audience、keywords 和 market 有關的"
        "語言，排除相鄰但不相關的需求。researchContext 必須區分搜尋 reference"
        " 中實際觀察到的措辭與推論出的措辭，不得捏造搜尋量資訊。"
        "只回傳符合 schema 的 structured JSON，包含 researchContext、"
        "searchedKeywords、sourceUrls。"
    )


def _query_research_prompt(
    command: QueryResearchCommand,
    language: str,
) -> str:
    competitors = ", ".join(command.competitor_brands) or "none"
    audience = command.audience.description if command.audience else "not specified"
    brand_rules = command.brand_mention_rules
    return (
        "Research current market language and natural search phrasing used by real "
        "users. Preserve concise fragments and conversational questions instead of "
        "rewriting them into formal or promotional sentences.\n"
        f"Brand: {command.brand_name}\n"
        f"Competitors: {competitors}\n"
        f"Keywords: {', '.join(command.keywords)}\n"
        f"Region: {command.region}\n"
        f"Language: {language}\n"
        f"Market type: {command.market_type}\n"
        f"Audience: {audience}\n"
        "Brand mention rules: "
        f"ownBrand={brand_rules.should_mention_own_brand}, "
        f"competitor={brand_rules.should_mention_competitor}\n"
        "Return concise researchContext with representative phrasing patterns, "
        "searchedKeywords actually used or useful for this research, and sourceUrls "
        "from references when available. Do not claim that inferred wording has "
        "measured popularity or search volume."
    )

async def _generate_with_reference_retry(
    generate: Callable[[str, str], Awaitable[Any]],
    query_text: str,
    language: str,
    *,
    has_remaining_calls: Callable[[], bool] | None = None,
) -> tuple[Any, list[Reference]]:
    response = await generate(
        _initial_grounding_prompt(query_text, language),
        "initial",
    )
    references = _grounding_references(response)
    if references:
        return response, references
    if has_remaining_calls is not None and not has_remaining_calls():
        return response, references

    retry_response = await generate(
        _reference_retry_prompt(query_text, language),
        "reference_retry",
    )
    retry_references = _grounding_references(retry_response)
    if retry_references:
        return retry_response, retry_references
    return response, references


def _initial_grounding_prompt(query_text: str, language: str) -> str:
    if language == "zh-TW":
        return (
            "回答前的第一個動作必須是使用 Google Search tool 搜尋網頁。"
            "請先搜尋原始 query；必要時可使用 query 中的品牌名、產品名、"
            "供應商名、規範名稱、常見別名或地點作為補充搜尋關鍵字。"
            "回答中的主要事實必須以本次搜尋取得、目前可查證的網頁內容為依據。"
            "請讓主要事實能明確對應到實際使用的來源網站或頁面。"
            "比較多個品牌或供應商時，不要只根據其中一方的資料推論其他對象。"
            "如果搜尋結果不足，請縮小結論並說明資料限制，"
            "不要使用模型既有知識補寫無法查證的內容。"
            "即使 query 模糊，也必須先搜尋，再說明採用的假設與仍需釐清的事項。"
            "\n\n"
            f"Query: {query_text}"
        )
    return (
        "Your first action before answering must be to use the Google Search tool. "
        "Search the original query first. When necessary, use brand names, product "
        "names, supplier names, regulation names, common aliases, or location context "
        "from the query as additional search terms. Ground the main factual claims in "
        "currently verifiable web pages retrieved during this request. Make the main "
        "claims clearly attributable to the source websites or pages actually used. "
        "When comparing multiple brands or suppliers, do not infer facts about one "
        "party solely from sources about another. If the search results are "
        "insufficient, narrow the conclusion and state the limitation instead of "
        "filling gaps with prior model knowledge. Even when the query is ambiguous, "
        "search first, then state the assumptions and remaining uncertainties.\n\n"
        f"Query: {query_text}"
    )


def _reference_retry_prompt(query_text: str, language: str) -> str:
    if language == "zh-TW":
        return (
            "上一輪回應沒有產生 grounding references。"
            "這一輪的第一個動作必須是使用 Google Search tool 搜尋網頁。"
            "請搜尋原始 query，以及你判斷最可能的同義詞、品牌名、產品名、"
            "供應商名或地點脈絡。即使問題模糊，也必須先搜尋，"
            "再說明採用的假設與仍需釐清的事項。"
            "回答內容必須根據目前可查證的網頁來源；不要只靠既有知識。"
            "請在回答中明確提到你使用的來源網站或頁面，讓 grounding references "
            "可以被系統擷取。\n\n"
            f"Query: {query_text}"
        )
    return (
        "The previous response produced no grounding references. Your first action "
        "in this turn must be to use the Google Search tool. Search the original "
        "query plus the most likely synonyms, brand names, product names, supplier "
        "names, or location context. Even if the query is ambiguous, search first, "
        "then state your working assumptions and what still needs clarification. "
        "Ground the answer in currently discoverable web pages; do not rely only on "
        "prior knowledge. Explicitly mention the source websites or pages you used "
        "so grounding references can be extracted.\n\n"
        f"Query: {query_text}"
    )


def _grounding_references(response: Any) -> list[Reference]:
    references_by_url: dict[str, Reference] = {}
    for candidate in getattr(response, "candidates", []) or []:
        metadata = getattr(candidate, "grounding_metadata", None)
        if not metadata:
            continue
        for chunk in getattr(metadata, "grounding_chunks", []) or []:
            web = getattr(chunk, "web", None)
            uri = getattr(web, "uri", None) if web else None
            title = getattr(web, "title", None) if web else None
            if uri:
                references_by_url.setdefault(
                    uri,
                    Reference(url=uri, title=title or None),
                )
    return sorted(references_by_url.values(), key=lambda reference: reference.url)


def _grounding_search_queries(response: Any) -> list[str]:
    queries: list[str] = []
    for candidate in getattr(response, "candidates", []) or []:
        metadata = getattr(candidate, "grounding_metadata", None)
        if not metadata:
            continue
        for query in getattr(metadata, "web_search_queries", []) or []:
            if query:
                queries.append(query)
    return sorted(set(queries))
