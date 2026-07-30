from collections.abc import Iterable

from younilab_seo.geo_analysis.application.contracts import QueryIntent


STANDARD_QUERY_INTENT_ALIASES = {
    "導航型": "navigational",
    "navigational": "navigational",
    "資訊型": "informational",
    "informational": "informational",
    "商業評估": "commercial_investigation",
    "commercial": "commercial_investigation",
    "commercial_investigation": "commercial_investigation",
    "交易型": "transactional",
    "transactional": "transactional",
}


def normalize_standard_query_intent(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    return STANDARD_QUERY_INTENT_ALIASES.get(value.strip().lower())


def resolve_generated_query_intent(
    value: object,
    requested_intents: Iterable[QueryIntent],
) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    raw_category = value.strip()
    requested_categories = [intent.category.strip() for intent in requested_intents]
    requested_standard_categories = {
        normalized
        for category in requested_categories
        if (normalized := normalize_standard_query_intent(category)) is not None
    }
    normalized = normalize_standard_query_intent(raw_category)
    if normalized in requested_standard_categories:
        return normalized
    if raw_category in requested_categories:
        return raw_category
    return None


def generated_query_intent_metadata(
    metadata: dict,
    raw_category: object,
    resolved_category: str | None,
) -> dict:
    result = dict(metadata)
    if isinstance(raw_category, str) and raw_category.strip() and resolved_category is None:
        result["rawIntentCategory"] = raw_category.strip()
    return result
