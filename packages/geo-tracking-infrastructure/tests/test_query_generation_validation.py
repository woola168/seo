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
    query: str = "Which ERP fits a manufacturer?",
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
            "query": query,
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


def test_validation_accepts_own_brand_alias_when_rule_is_enabled() -> None:
    command = QueryGenerationCommand.model_validate(
        {
            **_command().model_dump(mode="json", by_alias=True),
            "brandName": "Acme GEO tracking project",
            "ownBrandAliases": [{"alias": "Acme", "matchType": "exact"}],
            "brandMentionRules": {
                "shouldMentionOwnBrand": True,
                "shouldMentionCompetitor": False,
            },
        }
    )
    draft = _draft(query="Which Acme ERP fits a manufacturer?").model_copy(
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

    drafts = validate_query_drafts(command, [draft])

    assert [item.query for item in drafts] == ["Which Acme ERP fits a manufacturer?"]


def test_validation_rejects_disallowed_competitor_alias() -> None:
    command = QueryGenerationCommand.model_validate(
        {
            **_command().model_dump(mode="json", by_alias=True),
            "competitorBrands": ["Competitor Incorporated"],
            "competitorAliases": [
                {"alias": "Rival", "matchType": "case_insensitive"}
            ],
        }
    )
    draft = _draft(query="How does Rival ERP work?")

    with pytest.raises(
        ProviderRequestError,
        match="query_generation_constraints_invalid",
    ):
        validate_query_drafts(command, [draft])


def test_validation_applies_contains_alias_without_word_boundaries() -> None:
    command = QueryGenerationCommand.model_validate(
        {
            **_command().model_dump(mode="json", by_alias=True),
            "brandName": "Acme GEO tracking project",
            "ownBrandAliases": [{"alias": "Acme", "matchType": "contains"}],
            "brandMentionRules": {
                "shouldMentionOwnBrand": True,
                "shouldMentionCompetitor": False,
            },
        }
    )
    draft = _draft(query="Which AcmeERP fits a manufacturer?").model_copy(
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

    drafts = validate_query_drafts(command, [draft])

    assert [item.query for item in drafts] == ["Which AcmeERP fits a manufacturer?"]


@pytest.mark.parametrize(
    ("match_type", "query"),
    [
        ("exact", "Which 沈Puma ERP fits a manufacturer?"),
        ("case_insensitive", "Which 沈puma ERP fits a manufacturer?"),
    ],
)
def test_validation_matches_mixed_script_alias_without_word_boundaries(
    match_type: str,
    query: str,
) -> None:
    command = QueryGenerationCommand.model_validate(
        {
            **_command().model_dump(mode="json", by_alias=True),
            "brandName": "Mayor election tracking project",
            "ownBrandAliases": [{"alias": "沈P", "matchType": match_type}],
            "brandMentionRules": {
                "shouldMentionOwnBrand": True,
                "shouldMentionCompetitor": False,
            },
        }
    )
    draft = _draft(query=query).model_copy(
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

    drafts = validate_query_drafts(command, [draft])

    assert [item.query for item in drafts] == [query]


def test_validation_matches_mixed_script_own_brand_name_without_word_boundaries() -> None:
    command = QueryGenerationCommand.model_validate(
        {
            **_command().model_dump(mode="json", by_alias=True),
            "brandName": "沈P",
            "brandMentionRules": {
                "shouldMentionOwnBrand": True,
                "shouldMentionCompetitor": False,
            },
        }
    )
    query = "Which 沈Puma ERP fits a manufacturer?"
    draft = _draft(query=query).model_copy(
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

    drafts = validate_query_drafts(command, [draft])

    assert [item.query for item in drafts] == [query]


def test_validation_rejects_mixed_script_disallowed_competitor_name() -> None:
    command = QueryGenerationCommand.model_validate(
        {
            **_command().model_dump(mode="json", by_alias=True),
            "competitorBrands": ["沈P"],
        }
    )
    draft = _draft(query="Which 沈Puma ERP fits a manufacturer?")

    with pytest.raises(
        ProviderRequestError,
        match="query_generation_constraints_invalid",
    ):
        validate_query_drafts(command, [draft])


def test_validation_ignores_domain_alias_for_text_mentions() -> None:
    command = QueryGenerationCommand.model_validate(
        {
            **_command().model_dump(mode="json", by_alias=True),
            "brandName": "Acme GEO tracking project",
            "ownBrandAliases": [
                {"alias": "acme.example.com", "matchType": "domain"}
            ],
            "brandMentionRules": {
                "shouldMentionOwnBrand": True,
                "shouldMentionCompetitor": False,
            },
        }
    )
    draft = _draft(query="Is acme.example.com an ERP site?")

    with pytest.raises(
        ProviderRequestError,
        match="query_generation_constraints_invalid",
    ):
        validate_query_drafts(command, [draft])
