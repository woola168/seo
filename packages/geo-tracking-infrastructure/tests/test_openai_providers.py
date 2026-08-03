import json
from typing import Any

import pytest
from younilab_geo_tracking_application import (
    ProviderRequestError,
    QueryGenerationCommand,
    QueryResearchCommand,
)
from younilab_geo_tracking_infrastructure import (
    GeoTrackingSettings,
    OpenAIClientManager,
    OpenAIQueryGenerationProvider,
    OpenAIQueryResearchProvider,
)
from younilab_geo_tracking_infrastructure.openai_providers import (
    _query_draft_schema,
    _research_schema,
)
from younilab_provider_request_audit import MemoryProviderRequestRecorder


def _generation_command() -> QueryGenerationCommand:
    return QueryGenerationCommand.model_validate(
        {
            "provider": "openai",
            "brandName": "Acme",
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
            "brandMentionRules": {
                "shouldMentionOwnBrand": False,
                "shouldMentionCompetitor": False,
            },
            "maxQueries": 2,
        }
    )


def _research_command() -> QueryResearchCommand:
    return QueryResearchCommand.model_validate(
        {
            "provider": "openai",
            "brandName": "Acme",
            "keywords": ["erp"],
            "region": "TW",
            "language": "en-US",
            "marketType": "b2b_procurement",
        }
    )


def _draft(category: str, description: str) -> dict[str, Any]:
    return {
        "attributes": {
            "intent": {"category": category, "description": description},
            "keyword": "erp",
            "topicName": "ERP",
            "topicDescription": "ERP selection",
            "audience": {"name": "Buyer", "description": "Software buyer"},
            "brandMentionRules": {
                "shouldMentionOwnBrand": False,
                "shouldMentionCompetitor": False,
            },
        },
        "query": "Which ERP fits a manufacturer?",
        "keywords": ["erp"],
    }


def _message(text: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "message",
        "content": [{"type": "output_text", "text": json.dumps(text)}],
    }


class FakeResponses:
    def __init__(self, responses: list[dict[str, Any]]) -> None:
        self.calls: list[dict[str, Any]] = []
        self._responses = iter(responses)

    async def create(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(kwargs)
        return next(self._responses)


class FakeClient:
    def __init__(self, responses: list[dict[str, Any]]) -> None:
        self.responses = FakeResponses(responses)
        self.closed = False

    async def close(self) -> None:
        self.closed = True


@pytest.mark.anyio
async def test_openai_generation_repairs_invalid_drafts_without_search() -> None:
    client = FakeClient(
        [
            {
                "output": [
                    _message(
                        {
                            "items": [_draft("informational", "rewritten")],
                        }
                    )
                ],
                "usage": {"input_tokens": 10, "output_tokens": 20, "total_tokens": 30},
            },
            {
                "output": [
                    _message(
                        {
                            "items": [
                                _draft("informational", "Learn"),
                                _draft("transactional", "Act"),
                            ],
                        }
                    )
                ],
                "usage": {"input_tokens": 10, "output_tokens": 20, "total_tokens": 30},
            },
        ]
    )
    manager = OpenAIClientManager(
        GeoTrackingSettings(openai_api_key="test"),
        client_factory=lambda _: client,
    )
    provider = OpenAIQueryGenerationProvider(
        GeoTrackingSettings(openai_query_generation_model="gpt-5.6-luna"),
        MemoryProviderRequestRecorder(),
        manager,
    )

    drafts = await provider.generate_drafts(_generation_command())

    assert [draft.attributes.intent.category for draft in drafts] == [
        "informational",
        "transactional",
    ]
    assert len(client.responses.calls) == 2
    assert "tools" not in client.responses.calls[0]
    assert client.responses.calls[1]["text"]["format"]["name"] == (
        "geo_query_draft_list"
    )


@pytest.mark.anyio
async def test_openai_generation_fails_when_intent_repair_is_still_incomplete() -> None:
    client = FakeClient(
        [
            {"output": [_message({"items": [_draft("informational", "Learn")]})]},
            {
                "output": [
                    _message({"items": [_draft("transactional", "Rewritten by model")]})
                ]
            },
        ]
    )
    manager = OpenAIClientManager(
        GeoTrackingSettings(openai_api_key="test"),
        client_factory=lambda _: client,
    )
    provider = OpenAIQueryGenerationProvider(
        GeoTrackingSettings(openai_query_generation_model="gpt-5.6-luna"),
        MemoryProviderRequestRecorder(),
        manager,
    )

    with pytest.raises(ProviderRequestError, match="query_intent_coverage_failed"):
        await provider.generate_drafts(_generation_command())

    assert len(client.responses.calls) == 2


@pytest.mark.anyio
async def test_openai_generation_does_not_repair_impossible_intent_coverage() -> None:
    client = FakeClient(
        [
            {"output": [_message({"items": [_draft("informational", "Learn")]})]},
        ]
    )
    manager = OpenAIClientManager(
        GeoTrackingSettings(openai_api_key="test"),
        client_factory=lambda _: client,
    )
    provider = OpenAIQueryGenerationProvider(
        GeoTrackingSettings(openai_query_generation_model="gpt-5.6-luna"),
        MemoryProviderRequestRecorder(),
        manager,
    )

    drafts = await provider.generate_drafts(
        _generation_command().model_copy(update={"max_queries": 1})
    )

    assert [draft.attributes.intent.category for draft in drafts] == ["informational"]
    assert len(client.responses.calls) == 1


@pytest.mark.anyio
async def test_openai_research_uses_web_search_and_structured_output() -> None:
    client = FakeClient(
        [
            {
                "output": [
                    {
                        "type": "web_search_call",
                        "action": {
                            "type": "search",
                            "queries": ["ERP suppliers Taiwan"],
                            "sources": [{"url": "https://example.com/erp"}],
                        },
                    },
                    {
                        "type": "web_search_call",
                        "action": {
                            "type": "search",
                            "query": "ERP procurement checklist Taiwan",
                            "sources": [{"url": "https://example.com/checklist"}],
                        },
                    },
                    _message(
                        {
                            "researchContext": "ERP buyers compare suppliers.",
                            "searchedKeywords": ["model-generated search phrase"],
                            "sourceUrls": ["https://model.example/unverified"],
                        }
                    ),
                ],
                "usage": {"input_tokens": 10, "output_tokens": 20, "total_tokens": 30},
            }
        ]
    )
    manager = OpenAIClientManager(
        GeoTrackingSettings(openai_api_key="test"),
        client_factory=lambda _: client,
    )
    provider = OpenAIQueryResearchProvider(
        GeoTrackingSettings(openai_query_research_model="gpt-5.6-luna"),
        MemoryProviderRequestRecorder(),
        manager,
    )

    result = await provider.research(_research_command())

    assert result.research_context == "ERP buyers compare suppliers."
    assert result.searched_keywords == [
        "ERP suppliers Taiwan",
        "ERP procurement checklist Taiwan",
    ]
    assert result.source_urls == [
        "https://example.com/erp",
        "https://example.com/checklist",
    ]
    assert client.responses.calls[0]["tools"] == [{"type": "web_search"}]
    assert client.responses.calls[0]["include"] == ["web_search_call.action.sources"]
    assert client.responses.calls[0]["text"]["format"]["name"] == (
        "geo_query_research_output"
    )


@pytest.mark.anyio
async def test_openai_client_manager_reuses_and_closes_client() -> None:
    client = FakeClient([])
    manager = OpenAIClientManager(
        GeoTrackingSettings(openai_api_key="test"),
        client_factory=lambda _: client,
    )

    assert await manager.get_client() is client
    assert await manager.get_client() is client

    await manager.close()

    assert client.closed is True


@pytest.mark.anyio
async def test_openai_client_manager_rejects_missing_api_key() -> None:
    manager = OpenAIClientManager(GeoTrackingSettings(openai_api_key=""))

    with pytest.raises(ProviderRequestError, match="openai_api_key_missing"):
        await manager.get_client()


@pytest.mark.anyio
async def test_openai_generation_maps_invalid_structured_output() -> None:
    client = FakeClient(
        [
            {
                "output": [
                    {
                        "type": "message",
                        "content": [{"type": "output_text", "text": "not-json"}],
                    }
                ]
            }
        ]
    )
    manager = OpenAIClientManager(
        GeoTrackingSettings(openai_api_key="test"),
        client_factory=lambda _: client,
    )
    provider = OpenAIQueryGenerationProvider(
        GeoTrackingSettings(openai_query_generation_model="gpt-5.6-luna"),
        MemoryProviderRequestRecorder(),
        manager,
    )

    with pytest.raises(ProviderRequestError, match="openai_structured_output_invalid"):
        await provider.generate_drafts(_generation_command())


@pytest.mark.parametrize("schema", [_query_draft_schema(), _research_schema()])
def test_openai_structured_output_schema_forbids_additional_properties(
    schema: dict[str, Any],
) -> None:
    object_schemas = _object_schemas(schema)

    assert object_schemas
    assert all(item.get("additionalProperties") is False for item in object_schemas)
    assert all(
        set(item.get("required", [])) == set(item.get("properties", {}))
        for item in object_schemas
    )


def _object_schemas(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        current = [value] if value.get("type") == "object" else []
        return current + [
            item for child in value.values() for item in _object_schemas(child)
        ]
    if isinstance(value, list):
        return [item for child in value for item in _object_schemas(child)]
    return []
