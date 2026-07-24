from datetime import UTC, datetime
from uuid import UUID, uuid4

from younilab_seo.geo_analysis.application import (
    GeoEntityAliasRecord,
    GeoEntityRecord,
)
from younilab_seo.geo_analysis.application.entity_mention_detection import (
    detect_entity_mentions,
)

NOW = datetime(2026, 7, 23, tzinfo=UTC)


def test_detection_uses_canonical_name_and_preserves_raw_nfkc_evidence() -> None:
    own_brand = _entity("own_brand", "ACME")

    detection = detect_entity_mentions(
        run_result_id=uuid4(),
        raw_response="XACME 不算，但 ＡＣＭＥ 算。",
        entities=[own_brand],
        aliases=[],
    )

    assert detection.status == "completed"
    assert detection.items[0].mentioned is True
    assert detection.items[0].first_mention_order == 1
    assert detection.items[0].evidence_text == "ＡＣＭＥ"
    assert detection.items[0].matched_by == "canonical"


def test_detection_honors_alias_match_types_and_excludes_domain() -> None:
    own_brand = _entity("own_brand", "未出現品牌")
    aliases = [
        _alias(own_brand.id, "CaseExact", "exact"),
        _alias(own_brand.id, "CASELESS", "case_insensitive"),
        _alias(own_brand.id, "產品", "contains"),
        _alias(own_brand.id, "brand.example", "domain"),
    ]

    case_sensitive_miss = detect_entity_mentions(
        run_result_id=uuid4(),
        raw_response="caseexact 與 brand.example",
        entities=[own_brand],
        aliases=aliases,
    )
    case_insensitive_hit = detect_entity_mentions(
        run_result_id=uuid4(),
        raw_response="caseless",
        entities=[own_brand],
        aliases=aliases,
    )
    exact_hit = detect_entity_mentions(
        run_result_id=uuid4(),
        raw_response="CaseExact",
        entities=[own_brand],
        aliases=aliases,
    )
    contains_hit = detect_entity_mentions(
        run_result_id=uuid4(),
        raw_response="新產品線",
        entities=[own_brand],
        aliases=aliases,
    )

    assert case_sensitive_miss.items[0].mentioned is False
    assert exact_hit.items[0].match_type == "exact"
    assert case_insensitive_hit.items[0].match_type == "case_insensitive"
    assert contains_hit.items[0].evidence_text == "產品"
    assert contains_hit.items[0].match_type == "contains"


def test_detection_prefers_longer_overlapping_entity_name() -> None:
    short = _entity("own_brand", "Acme")
    long = _entity("competitor", "Acme ERP")

    detection = detect_entity_mentions(
        run_result_id=uuid4(),
        raw_response="Acme ERP 適合製造業。",
        entities=[short, long],
        aliases=[],
    )

    by_id = {item.entity_id: item for item in detection.items}
    assert by_id[short.id].mentioned is False
    assert by_id[long.id].mentioned is True
    assert by_id[long.id].evidence_text == "Acme ERP"


def test_detection_does_not_assign_ambiguous_alias_and_orders_first_mentions() -> None:
    own_brand = _entity("own_brand", "Own")
    competitor = _entity("competitor", "Rival")
    aliases = [
        _alias(own_brand.id, "Shared", "case_insensitive"),
        _alias(competitor.id, "Shared", "case_insensitive"),
    ]

    ambiguous = detect_entity_mentions(
        run_result_id=uuid4(),
        raw_response="shared",
        entities=[own_brand, competitor],
        aliases=aliases,
    )
    ordered = detect_entity_mentions(
        run_result_id=uuid4(),
        raw_response="Rival 與 Own",
        entities=[own_brand, competitor],
        aliases=aliases,
    )

    assert all(item.mentioned is False for item in ambiguous.items)
    by_id = {item.entity_id: item for item in ordered.items}
    assert by_id[competitor.id].first_mention_order == 1
    assert by_id[own_brand.id].first_mention_order == 2


def _entity(entity_type: str, name: str) -> GeoEntityRecord:
    return GeoEntityRecord(
        id=uuid4(),
        project_id=uuid4(),
        entity_type=entity_type,
        name=name,
        status="active",
        created_at=NOW,
        updated_at=NOW,
    )


def _alias(
    entity_id: UUID,
    value: str,
    match_type: str,
) -> GeoEntityAliasRecord:
    return GeoEntityAliasRecord(
        id=uuid4(),
        entity_id=entity_id,
        alias=value,
        match_type=match_type,
        created_at=NOW,
    )
