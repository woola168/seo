import asyncio
import os
from collections.abc import Awaitable, Callable, Mapping
from typing import Any

import aiohttp
from pydantic import BaseModel, Field
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


class _GeminiIntent(BaseModel):
    category: str
    description: str


class _GeminiAudience(BaseModel):
    name: str
    description: str


class _GeminiBrandMentionRules(BaseModel):
    shouldMentionOwnBrand: bool
    shouldMentionCompetitor: bool


class _GeminiQueryAttributes(BaseModel):
    intent: _GeminiIntent
    keyword: str
    topicName: str
    topicDescription: str = ""
    audience: _GeminiAudience
    brandMentionRules: _GeminiBrandMentionRules


class _GeminiQueryDraft(BaseModel):
    attributes: _GeminiQueryAttributes
    query: str
    keywords: list[str] = Field(default_factory=list)


class _GeminiQueryDraftList(BaseModel):
    items: list[_GeminiQueryDraft]


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
        fetch_json: Callable[[Mapping[str, str]], Awaitable[dict[str, Any]]]
        | None = None,
    ) -> None:
        self._settings = settings
        self._fetch_json = fetch_json
        self._session: aiohttp.ClientSession | None = None

    async def generate_answer(self, request: AnswerRequest) -> AnswerResponse:
        if not self._settings.serpapi_api_key:
            raise ProviderRequestError("serpapi_api_key_missing")

        profile = _serpapi_locale_profile(request.region)
        language = request.language or profile.default_language
        search_payload = await self._request_serpapi(
            {
                "engine": "google",
                "q": request.query_text,
                "hl": _serpapi_hl(language, profile),
                "gl": profile.gl,
                "location": profile.location,
            }
        )
        ai_overview = await self._resolve_ai_overview(search_payload)
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
                }
            )
            ai_overview = _payload_ai_overview(ai_overview_payload)
            if _has_ai_overview_content(ai_overview):
                return ai_overview

        raise ProviderRequestError("no_google_aio_result")

    async def _request_serpapi(
        self,
        params: Mapping[str, str],
    ) -> dict[str, Any]:
        request_params = {**params, "api_key": self._settings.serpapi_api_key}
        if self._fetch_json is not None:
            return await self._fetch_json(request_params)

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
            raise ProviderRequestError("serpapi_request_failed")
        if payload.get("error"):
            raise ProviderRequestError("serpapi_request_failed")
        return payload

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
    blocks = ai_overview.get("text_blocks")
    if not isinstance(blocks, list):
        return ""
    lines: list[str] = []
    for block in blocks:
        if not isinstance(block, dict):
            continue
        snippet = _clean_text(block.get("snippet"))
        block_type = block.get("type")
        if snippet:
            lines.append(snippet)
        if block_type == "list":
            lines.extend(_ai_overview_list_lines(block.get("list")))
    return "\n\n".join(lines).strip()


def _ai_overview_list_lines(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    lines: list[str] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        title = _clean_text(item.get("title"))
        snippet = _clean_text(item.get("snippet"))
        if title and snippet:
            lines.append(f"- {title} {snippet}")
        elif title:
            lines.append(f"- {title}")
        elif snippet:
            lines.append(f"- {snippet}")
    return lines


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
    def __init__(self, settings: GeoTrackingSettings) -> None:
        self._settings = settings

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
        )
        config = types.GenerateContentConfig(
            temperature=self._settings.gemini_temperature,
            system_instruction=request.system_prompt,
            tools=[types.Tool(google_search=types.GoogleSearch())],
            thinking_config=types.ThinkingConfig(
                thinking_level=self._settings.gemini_thinking_level.upper(),
            ),
        )
        response, references = await _generate_with_reference_retry(
            lambda contents: self._generate_content(client, contents, config),
            request.query_text,
            request.language,
        )
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
    def __init__(self, settings: GeoTrackingSettings) -> None:
        self._settings = settings

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
        response = await asyncio.to_thread(
            client.models.generate_content,
            model=self._settings.gemini_model,
            contents=_query_generation_prompt(command, language),
            config=config,
        )
        parsed = response.parsed
        if not isinstance(parsed, _GeminiQueryDraftList):
            parsed = _GeminiQueryDraftList.model_validate_json(response.text or "{}")
        return _query_drafts_from_gemini(command, parsed)


class GeminiQueryResearchProvider:
    def __init__(self, settings: GeoTrackingSettings) -> None:
        self._settings = settings

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
        response = await asyncio.to_thread(
            client.models.generate_content,
            model=self._settings.gemini_model,
            contents=_query_research_prompt(command, language),
            config=config,
        )
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


def build_answer_provider(settings: GeoTrackingSettings) -> AnswerProvider:
    if settings.provider == ProviderCode.GEMINI:
        return GeminiVertexAnswerProvider(settings)
    if settings.provider == ProviderCode.GOOGLE_AIO:
        return SerpApiGoogleAioAnswerProvider(settings)
    return DummyAnswerProvider()


def build_answer_providers(
    settings: GeoTrackingSettings,
) -> dict[ProviderCode, AnswerProvider]:
    return {
        ProviderCode.DUMMY: DummyAnswerProvider(),
        ProviderCode.GEMINI: GeminiVertexAnswerProvider(settings),
        ProviderCode.GOOGLE_AIO: SerpApiGoogleAioAnswerProvider(settings),
    }


def build_query_research_providers(
    settings: GeoTrackingSettings,
) -> dict[ProviderCode, QueryResearchProvider]:
    return {
        ProviderCode.DUMMY: DummyQueryResearchProvider(),
        ProviderCode.GEMINI: GeminiQueryResearchProvider(settings),
    }


def build_query_generation_providers(
    settings: GeoTrackingSettings,
) -> dict[ProviderCode, QueryGenerationProvider]:
    return {
        ProviderCode.DUMMY: DummyQueryGenerationProvider(),
        ProviderCode.GEMINI: GeminiQueryGenerationProvider(settings),
    }


def _query_generation_system_prompt(language: str | None) -> str:
    if language == "en-US":
        return (
            "You generate AI-search query candidates for GEO tracking. "
            "Do not use Google Search or any external search tool. "
            "Use only the provided JSON parameters and optional researchContext. "
            "The attributes object must copy the provided intent, audience, "
            "brandMentionRules, keyword, topicName, and topicDescription values. "
            "Use topicDescription as a generation constraint, but do not invent, "
            "infer, or classify intent. Do not include searchedKeywords, sourceUrls, "
            "SERP, or evidence fields. "
            "Return only structured JSON that matches the schema. For each item, "
            "attributes must appear first, query must appear next, and keywords must "
            "appear after query. keywords must be a list of the provided seed "
            "keywords used by that query. Do not invent keywords."
        )
    return (
        "你負責產生 GEO 追蹤用的 AI 搜尋 query 候選。"
        "不要使用 Google Search 或任何外部搜尋工具。"
        "只根據提供的 JSON 參數與可選 researchContext 生成。"
        "attributes 必須複製輸入提供的 intent、audience、brandMentionRules、"
        "keyword、topicName、topicDescription。topicDescription 必須作為生成約束，"
        "但不得自行推論、分類或改寫 intent。"
        "不得輸出 searchedKeywords、sourceUrls、SERP 或 evidence 欄位。"
        "只回傳符合 schema 的結構化 JSON。每筆資料必須先輸出 attributes，"
        "接著輸出 query，最後輸出 keywords。keywords 必須是該 query 用到的"
        "輸入 seed keywords 陣列，不得自行發明 keyword。"
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
    return command.intents[0]


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
            "You research market language for GEO query generation. "
            "You must use the Google Search tool as a reference. Return only "
            "structured JSON with researchContext, searchedKeywords, and sourceUrls."
        )
    return (
        "你負責研究 GEO query generation 需要的市場語氣與搜尋語言。"
        "你必須使用 Google Search tool 作為 reference。"
        "只回傳符合 schema 的 structured JSON，包含 researchContext、"
        "searchedKeywords、sourceUrls。"
    )


def _query_research_prompt(
    command: QueryResearchCommand,
    language: str,
) -> str:
    competitors = ", ".join(command.competitor_brands) or "none"
    audience = command.audience.description if command.audience else "not specified"
    return (
        "Research current market language and search phrasing.\n"
        f"Brand: {command.brand_name}\n"
        f"Competitors: {competitors}\n"
        f"Keywords: {', '.join(command.keywords)}\n"
        f"Region: {command.region}\n"
        f"Language: {language}\n"
        f"Market type: {command.market_type}\n"
        f"Audience: {audience}\n"
        "Return concise researchContext, searchedKeywords actually used or useful for "
        "this research, and sourceUrls from references when available."
    )


async def _generate_with_reference_retry(
    generate: Callable[[str], Awaitable[Any]],
    query_text: str,
    language: str,
) -> tuple[Any, list[Reference]]:
    response = await generate(query_text)
    references = _grounding_references(response)
    if references:
        return response, references

    retry_response = await generate(_reference_retry_prompt(query_text, language))
    retry_references = _grounding_references(retry_response)
    if retry_references:
        return retry_response, retry_references
    return response, references


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
