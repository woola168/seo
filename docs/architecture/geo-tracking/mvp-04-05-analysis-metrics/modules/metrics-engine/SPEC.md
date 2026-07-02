# Metrics Engine Spec

## Use Case: CalculateGeoMetrics

Input：

- `project_id`
- `period_start`
- `period_end`
- optional `comparison_start`
- optional `comparison_end`
- optional filters: topic, query, provider, region, language
- optional `scope_types`

流程：

1. Validate period.
2. Load completed run results and facts.
3. Calculate current period metrics.
4. Calculate comparison period metrics.
5. Upsert `geo_metric_snapshot`。

## Use Case: DailyAggregationJob

MVP requirement calls for daily aggregation.

規則：

- Run daily for previous day.
- Calculate project + provider + region + language + topic/query/entity/citation/sentiment scopes.
- Do not hard-code "yesterday vs day before yesterday" as the only comparison model.
- `CalculateGeoMetrics` decides comparison range from the dashboard query period.

## Repository Port

```python
class GeoMetricsRepository(Protocol):
    async def load_metric_source(
        self,
        query: GeoMetricSourceQuery,
    ) -> GeoMetricSource:
        ...

    async def upsert_snapshots(
        self,
        snapshots: list[GeoMetricSnapshotRecord],
    ) -> None:
        ...

    async def query_snapshots(
        self,
        query: GeoMetricSnapshotQuery,
    ) -> list[GeoMetricSnapshotRecord]:
        ...
```

Repository 負責載入 facts 與保存 snapshots。它不應呼叫 KMindHub，也不應在 Metrics Engine use case 外重新計算公式。

## Formulas

### Mentions

```text
mentioned own brand response count / completed response count
```

- Numerator: distinct `run_result_id` where own brand `mentioned = true`.
- Denominator: completed distinct `run_result_id`.
- Display can be `729/862`.
- Same formula must support `entity` scope for competitor mentions.

### Visibility

```text
mentioned own brand response count / completed response count * 100
```

- Same numerator and denominator as Mentions.
- Same formula must support `entity` scope for competitor visibility.

### SOV

```text
own brand mention count / (own brand mention count + configured competitor mention count)
```

規則：

- Denominator only includes project-selected competitors.
- AI-mentioned but unconfigured brands are excluded.
- Same entity mentioned multiple times in one response counts once.

### Average Position

```text
average own brand first_mention_order
```

規則：

- Only responses where own brand is mentioned are included.
- `first_mention_order` is relative to own brand and configured competitors.
- Same entity mentioned multiple times uses first appearance only.

### Used %

```text
responses citing URL/domain / completed responses
```

規則：

- URL scope aggregates normalized URL.
- Domain scope aggregates normalized domain.
- Numerator uses distinct `run_result_id`.

### Citation Count

```text
citation row count for URL/domain
```

規則：

- URL scope aggregates normalized URL.
- Domain scope aggregates normalized domain.

### Share %

```text
URL/domain citation row count / all citation row count
```

規則：

- Numerator is citation rows for URL/domain.
- Denominator is all citation rows in the filtered period/scope.

### Sentiment Count

```text
positive / negative statement count
```

規則：

- MVP only counts `positive` and `negative`.
- 本階段不接受 `neutral`。
- Can be filtered by entity, topic, query, provider, region, language, period.

### Previous Period Comparison

Default:

```text
current query period vs previous equal-length period
```

Example: current period `2026-07-01T00:00:00Z` to `2026-07-08T00:00:00Z`; comparison period is `2026-06-24T00:00:00Z` to `2026-07-01T00:00:00Z`.

規則：

- Dashboard query may pass explicit `comparisonStart` / `comparisonEnd`.
- If omitted, use previous equal-length period.
- Delta unit is `pp`, `count`, or `rank`.

## Tests

- Visibility / Mentions formula.
- SOV only includes configured competitors.
- Average Position only includes own-brand-mentioned responses.
- Used % distinct response count.
- Citation Count row count.
- Share % citation row share.
- Sentiment Count positive / negative only.
- Previous equal-length comparison.
- Entity scope competitor visibility / mentions / position.
- Snapshot upsert is idempotent.
