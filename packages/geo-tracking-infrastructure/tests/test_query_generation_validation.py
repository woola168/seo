import pytest
from younilab_geo_tracking_application import (
    ProviderRequestError,
    QueryGenerationCommand,
)
from younilab_geo_tracking_infrastructure.providers import (
    _GeminiQueryDraft,
    _GeminiQueryDraftList,
)
from younilab_geo_tracking_infrastructure.query_generation_validation import (
    validate_query_drafts,
)


def _command() -> QueryGenerationCommand:
    return QueryGenerationCommand.model_validate(
        {
            "brandName": "Acme",
            "keywords": ["erp", "crm"],
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


def _draft(
    *,
    intent_description: str = "Learn",
    keyword: str = "erp",
    keywords: list[str] | None = None,
) -> _GeminiQueryDraft:
    return _GeminiQueryDraft.model_validate(
        {
            "attributes": {
                "intent": {
                    "category": "informational",
                    "description": intent_description,
                },
                "keyword": keyword,
                "topicName": "ERP",
                "topicDescription": "ERP selection",
                "audience": {"name": "Buyer", "description": "Software buyer"},
                "brandMentionRules": {
                    "shouldMentionOwnBrand": False,
                    "shouldMentionCompetitor": False,
                },
            },
            "query": "Which ERP fits a manufacturer?",
            "keywords": keywords or ["erp"],
        }
    )


def test_validation_copies_selected_attributes_instead_of_rewriting_them() -> None:
    drafts = validate_query_drafts(
        _command(),
        _GeminiQueryDraftList(items=[_draft()]).items,
    )

    assert drafts[0].attributes.intent.description == "Learn"
    assert drafts[0].attributes.keyword == "erp"
    assert drafts[0].keywords == ["erp"]


@pytest.mark.parametrize(
    "draft",
    [
        _draft(intent_description="Learn about ERP"),
        _draft(keyword="erp comparison"),
        _draft(keywords=["erp", "invented keyword"]),
    ],
)
def test_validation_discards_model_outputs_that_break_input_constraints(
    draft: _GeminiQueryDraft,
) -> None:
    with pytest.raises(
        ProviderRequestError, match="query_generation_constraints_invalid"
    ):
        validate_query_drafts(_command(), [draft])


def test_validation_requires_each_keyword_to_appear_in_the_query() -> None:
    draft = _draft(keywords=["crm"])

    with pytest.raises(
        ProviderRequestError, match="query_generation_constraints_invalid"
    ):
        validate_query_drafts(_command(), [draft])


def test_validation_accepts_legacy_topic_names() -> None:
    command = _command().model_copy(
        update={
            "topics": [],
            "topic_names": ["ERP"],
        }
    )
    draft = _draft().model_copy(
        update={
            "attributes": _draft().attributes.model_copy(
                update={"topicDescription": ""}
            )
        }
    )

    drafts = validate_query_drafts(command, [draft])

    assert drafts[0].attributes.topic_name == "ERP"
    assert drafts[0].attributes.topic_description == ""


def test_validation_requires_own_brand_when_rule_is_enabled() -> None:
    command = _command().model_copy(
        update={
            "brand_mention_rules": _command().brand_mention_rules.model_copy(
                update={"should_mention_own_brand": True}
            )
        }
    )
    draft = _draft().model_copy(
        update={
            "attributes": _draft().attributes.model_copy(
                update={
                    "brandMentionRules": _draft().attributes.brandMentionRules.model_copy(
                        update={"shouldMentionOwnBrand": True}
                    )
                }
            )
        }
    )

    with pytest.raises(
        ProviderRequestError,
        match="query_generation_constraints_invalid",
    ):
        validate_query_drafts(command, [draft])
