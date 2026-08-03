import re
from collections.abc import Iterable
from typing import Any

from younilab_geo_tracking_application import (
    ProviderRequestError,
    QueryDraft,
    QueryGenerationCommand,
    QueryIntent,
    TopicInput,
)
from younilab_geo_tracking_domain import MarketType


def validate_query_drafts(
    command: QueryGenerationCommand,
    items: Iterable[Any],
) -> list[QueryDraft]:
    drafts: list[QueryDraft] = []
    for item in items:
        try:
            drafts.append(_validate_query_draft(command, item))
        except ValueError:
            continue

    if not drafts:
        raise ProviderRequestError("query_generation_constraints_invalid")
    return drafts[: command.max_queries]


def validated_query_drafts_or_empty(
    command: QueryGenerationCommand,
    items: Iterable[Any],
) -> list[QueryDraft]:
    try:
        return validate_query_drafts(command, items)
    except ProviderRequestError as exc:
        if exc.code == "query_generation_constraints_invalid":
            return []
        raise


def missing_query_intents(
    command: QueryGenerationCommand,
    drafts: list[QueryDraft],
) -> list[QueryIntent]:
    if command.max_queries < len(command.intents):
        return []
    generated_categories = {draft.attributes.intent.category for draft in drafts}
    missing: list[QueryIntent] = []
    for intent in command.intents:
        if intent.category not in generated_categories and all(
            item.category != intent.category for item in missing
        ):
            missing.append(intent)
    return missing


def merge_intent_coverage_drafts(
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
    if any(category not in drafts_by_category for category in selected_categories):
        raise ProviderRequestError("query_intent_coverage_failed")

    required = [drafts_by_category[category] for category in selected_categories]
    required_ids = {id(draft) for draft in required}
    extras = [draft for draft in initial_drafts if id(draft) not in required_ids]
    return [*required, *extras][: command.max_queries]


def _validate_query_draft(
    command: QueryGenerationCommand,
    item: Any,
) -> QueryDraft:
    attributes = item.attributes
    query = item.query.strip()
    if not query:
        raise ValueError("query must not be empty")
    if _mentions_disallowed_competitor(command, query):
        raise ValueError("query must not mention a disallowed competitor")
    if (
        command.brand_mention_rules.should_mention_own_brand
        and not _contains_brand_name(query, command.brand_name)
    ):
        raise ValueError("query must mention the own brand")

    intent = next(
        (
            candidate
            for candidate in command.intents
            if candidate.category == attributes.intent.category
            and candidate.description == attributes.intent.description
        ),
        None,
    )
    if intent is None:
        raise ValueError("intent must be copied from the command")

    if attributes.keyword not in command.keywords:
        raise ValueError("keyword must be copied from the command")

    topic = next(
        (
            candidate
            for candidate in _command_topics(command)
            if candidate.name == attributes.topicName
            and candidate.description == attributes.topicDescription
        ),
        None,
    )
    if topic is None:
        raise ValueError("topic must be copied from the command")

    if (
        attributes.audience.name != command.audience.name
        or attributes.audience.description != command.audience.description
    ):
        raise ValueError("audience must be copied from the command")
    if (
        attributes.brandMentionRules.shouldMentionOwnBrand
        != command.brand_mention_rules.should_mention_own_brand
        or attributes.brandMentionRules.shouldMentionCompetitor
        != command.brand_mention_rules.should_mention_competitor
    ):
        raise ValueError("brand mention rules must be copied from the command")

    keywords = _validate_keywords(
        item.keywords,
        command.keywords,
        query,
        attributes.keyword,
    )
    return QueryDraft(
        attributes={
            "intent": intent,
            "keyword": attributes.keyword,
            "topicName": topic.name,
            "topicDescription": topic.description,
            "audience": command.audience,
            "brandMentionRules": command.brand_mention_rules,
        },
        query=query,
        keywords=keywords,
    )


def _validate_keywords(
    values: list[str],
    allowed_values: list[str],
    query: str,
    primary_keyword: str,
) -> list[str]:
    if not values or len(values) != len(set(values)):
        raise ValueError("keywords must be a non-empty unique list")
    if any(value not in allowed_values for value in values):
        raise ValueError("keywords must come from the command")
    if primary_keyword not in values:
        raise ValueError("keywords must include the primary keyword")
    normalized_query = query.casefold()
    if any(value.casefold() not in normalized_query for value in values):
        raise ValueError("keywords must occur in the query")
    return values


def _command_topics(command: QueryGenerationCommand) -> list[TopicInput]:
    if command.topics:
        return command.topics
    names = command.topic_names or _default_topic_names(command.market_type)
    return [TopicInput(name=name) for name in names]


def _default_topic_names(market_type: MarketType) -> list[str]:
    if market_type == MarketType.B2B_PROCUREMENT:
        return ["品牌型", "產品型", "採購評估"]
    return ["品牌型", "產品型", "資訊型"]


def _mentions_disallowed_competitor(
    command: QueryGenerationCommand,
    query: str,
) -> bool:
    if command.brand_mention_rules.should_mention_competitor:
        return False
    return any(
        _contains_brand_name(query, competitor)
        for competitor in command.competitor_brands
    )


def _contains_brand_name(query: str, brand_name: str) -> bool:
    brand_name = brand_name.strip()
    if not brand_name:
        return False
    if any(not character.isascii() for character in brand_name):
        return brand_name.casefold() in query.casefold()
    return bool(
        re.search(
            rf"(?<![A-Za-z0-9]){re.escape(brand_name)}(?![A-Za-z0-9])",
            query,
            flags=re.IGNORECASE,
        )
    )
