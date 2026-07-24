from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from uuid import UUID

from younilab_seo.geo_analysis.application.contracts import (
    GeoEntityAliasRecord,
    GeoEntityMentionDetectionItem,
    GeoEntityRecord,
    GeoRunResultEntityDetection,
)

ENTITY_MENTION_DETECTOR_VERSION = "explicit_alias:v1"
_SUPPORTED_ALIAS_MATCH_TYPES = frozenset({"exact", "case_insensitive", "contains"})


@dataclass(frozen=True)
class _NormalizedText:
    value: str
    raw_spans: tuple[tuple[int, int], ...]


@dataclass(frozen=True)
class _Pattern:
    entity: GeoEntityRecord
    value: str
    matched_by: str
    match_type: str
    case_sensitive: bool
    word_boundaries: bool


@dataclass(frozen=True)
class _Match:
    pattern: _Pattern
    start: int
    end: int


def detect_entity_mentions(
    *,
    run_result_id: UUID,
    raw_response: str,
    entities: list[GeoEntityRecord],
    aliases: list[GeoEntityAliasRecord],
) -> GeoRunResultEntityDetection:
    """Detect explicit canonical-name and configured-alias mentions in one answer."""

    active_entities = [
        entity
        for entity in entities
        if entity.status == "active"
        and entity.entity_type in {"own_brand", "competitor"}
    ]
    entity_by_id = {entity.id: entity for entity in active_entities}
    patterns = _patterns(active_entities, aliases, entity_by_id)
    matches = _select_non_overlapping_matches(raw_response, patterns)
    first_by_entity: dict[UUID, _Match] = {}
    for match in sorted(matches, key=lambda item: (item.start, item.end)):
        first_by_entity.setdefault(match.pattern.entity.id, match)

    ordered_entity_ids = {
        entity_id: order
        for order, (entity_id, _match) in enumerate(
            sorted(
                first_by_entity.items(),
                key=lambda item: (item[1].start, str(item[0])),
            ),
            start=1,
        )
    }
    items: list[GeoEntityMentionDetectionItem] = []
    for entity in active_entities:
        match = first_by_entity.get(entity.id)
        if match is None:
            items.append(
                GeoEntityMentionDetectionItem(
                    entity_id=entity.id,
                    entity_role=entity.entity_type,
                    entity_name=entity.name,
                    mentioned=False,
                )
            )
            continue
        items.append(
            GeoEntityMentionDetectionItem(
                entity_id=entity.id,
                entity_role=entity.entity_type,
                entity_name=entity.name,
                mentioned=True,
                first_mention_order=ordered_entity_ids[entity.id],
                evidence_text=raw_response[match.start : match.end],
                matched_by=match.pattern.matched_by,
                matched_value=match.pattern.value,
                match_type=match.pattern.match_type,
            )
        )
    return GeoRunResultEntityDetection(
        run_result_id=run_result_id,
        detector_version=ENTITY_MENTION_DETECTOR_VERSION,
        status="completed",
        items=items,
    )


def _patterns(
    entities: list[GeoEntityRecord],
    aliases: list[GeoEntityAliasRecord],
    entity_by_id: dict[UUID, GeoEntityRecord],
) -> list[_Pattern]:
    patterns = [
        _Pattern(
            entity=entity,
            value=entity.name,
            matched_by="canonical",
            match_type="canonical",
            case_sensitive=False,
            word_boundaries=_is_ascii(entity.name),
        )
        for entity in entities
        if entity.name.strip()
    ]
    for alias in aliases:
        entity = entity_by_id.get(alias.entity_id)
        if (
            entity is None
            or alias.match_type not in _SUPPORTED_ALIAS_MATCH_TYPES
            or not alias.alias.strip()
        ):
            continue
        patterns.append(
            _Pattern(
                entity=entity,
                value=alias.alias,
                matched_by="alias",
                match_type=alias.match_type,
                case_sensitive=alias.match_type == "exact",
                word_boundaries=(
                    alias.match_type != "contains" and _is_ascii(alias.alias)
                ),
            )
        )
    return patterns


def _select_non_overlapping_matches(
    raw_response: str,
    patterns: list[_Pattern],
) -> list[_Match]:
    sensitive = _normalize_with_offsets(raw_response, casefold=False)
    insensitive = _normalize_with_offsets(raw_response, casefold=True)
    candidates: list[_Match] = []
    for pattern in patterns:
        source = sensitive if pattern.case_sensitive else insensitive
        needle = _normalize(pattern.value, casefold=not pattern.case_sensitive)
        if not needle:
            continue
        offset = 0
        while (index := source.value.find(needle, offset)) >= 0:
            end_index = index + len(needle)
            offset = index + 1
            if pattern.word_boundaries and not _has_word_boundaries(
                source.value,
                index,
                end_index,
                needle,
            ):
                continue
            candidates.append(
                _Match(
                    pattern=pattern,
                    start=source.raw_spans[index][0],
                    end=source.raw_spans[end_index - 1][1],
                )
            )

    unambiguous: list[_Match] = []
    by_span: dict[tuple[int, int], list[_Match]] = {}
    for candidate in candidates:
        by_span.setdefault((candidate.start, candidate.end), []).append(candidate)
    for span_matches in by_span.values():
        if len({match.pattern.entity.id for match in span_matches}) != 1:
            continue
        unambiguous.append(
            min(
                span_matches,
                key=lambda match: (
                    0 if match.pattern.matched_by == "canonical" else 1,
                    match.pattern.value,
                ),
            )
        )

    selected: list[_Match] = []
    for candidate in sorted(
        unambiguous,
        key=lambda match: (-(match.end - match.start), match.start, match.end),
    ):
        if any(
            candidate.start < existing.end and existing.start < candidate.end
            for existing in selected
        ):
            continue
        selected.append(candidate)
    return selected


def _normalize_with_offsets(value: str, *, casefold: bool) -> _NormalizedText:
    normalized_parts: list[str] = []
    raw_spans: list[tuple[int, int]] = []
    for start, end in _unicode_clusters(value):
        normalized = _normalize(value[start:end], casefold=casefold)
        normalized_parts.append(normalized)
        raw_spans.extend((start, end) for _character in normalized)
    return _NormalizedText("".join(normalized_parts), tuple(raw_spans))


def _unicode_clusters(value: str) -> list[tuple[int, int]]:
    clusters: list[tuple[int, int]] = []
    start = 0
    for index in range(1, len(value)):
        if unicodedata.combining(value[index]) == 0:
            clusters.append((start, index))
            start = index
    if value:
        clusters.append((start, len(value)))
    return clusters


def _normalize(value: str, *, casefold: bool) -> str:
    normalized = unicodedata.normalize("NFKC", value)
    return normalized.casefold() if casefold else normalized


def _has_word_boundaries(
    source: str,
    start: int,
    end: int,
    needle: str,
) -> bool:
    if needle[0].isascii() and _is_ascii_word_character(needle[0]):
        if start > 0 and _is_ascii_word_character(source[start - 1]):
            return False
    if needle[-1].isascii() and _is_ascii_word_character(needle[-1]):
        if end < len(source) and _is_ascii_word_character(source[end]):
            return False
    return True


def _is_ascii(value: str) -> bool:
    return bool(value) and value.isascii()


def _is_ascii_word_character(value: str) -> bool:
    return value.isascii() and (value.isalnum() or value == "_")
