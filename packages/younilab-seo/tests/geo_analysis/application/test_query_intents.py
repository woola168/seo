from younilab_seo.geo_analysis.application import (
    QueryIntent,
    generated_query_intent_metadata,
    normalize_standard_query_intent,
    resolve_generated_query_intent,
)


def test_normalize_standard_query_intent_accepts_legacy_aliases() -> None:
    assert normalize_standard_query_intent("商業評估") == "commercial_investigation"
    assert normalize_standard_query_intent("commercial") == "commercial_investigation"
    assert normalize_standard_query_intent("TRANSACTIONAL") == "transactional"
    assert normalize_standard_query_intent("custom") is None


def test_resolve_generated_intent_requires_selected_standard_category() -> None:
    requested = [QueryIntent(category="informational", description="Learn")]

    assert resolve_generated_query_intent("資訊型", requested) == "informational"
    assert resolve_generated_query_intent("transactional", requested) is None
    assert resolve_generated_query_intent("unknown", requested) is None


def test_resolve_generated_intent_preserves_requested_custom_category() -> None:
    requested = [QueryIntent(category="custom-category", description="Custom")]

    assert resolve_generated_query_intent("custom-category", requested) == "custom-category"
    assert resolve_generated_query_intent("another-category", requested) is None


def test_unclassified_intent_metadata_retains_raw_category() -> None:
    assert generated_query_intent_metadata({"source": "model"}, "unexpected", None) == {
        "source": "model",
        "rawIntentCategory": "unexpected",
    }
