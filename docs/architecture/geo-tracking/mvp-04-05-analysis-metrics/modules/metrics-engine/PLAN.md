# Metrics Engine Plan

## Responsibility

Metrics Engine 從 semantic facts 與 citation facts deterministic 計算 dashboard 指標與前期比較。

Owned metrics:

- Visibility。
- SOV。
- Average Position。
- Mentions。
- Citation Count。
- Used %。
- Share %。
- Sentiment Count。
- Daily metric snapshot。
- Previous period comparison。

此 module 不呼叫 KMindHub，不讀外部 runner API，不解析 raw response。

## Architecture

```text
CalculateGeoMetrics
  -> load completed run results + semantic facts + citation facts
  -> calculate current period metrics
  -> calculate comparison period metrics
  -> upsert geo_metric_snapshot
```

Daily job:

```text
daily aggregation schedule
  -> project/provider/region/language/topic/query/entity/citation/sentiment scopes
  -> previous day snapshots
```

Dashboard query can merge daily snapshots. If a requested period has no snapshot, the application may fallback to facts calculation and backfill snapshots.

## Rollout Slice

1. Add metric snapshot schema.
2. Implement formula calculator with in-memory facts for tests.
3. Implement repository source query.
4. Implement snapshot upsert.
5. Implement daily aggregation job.
6. Add API/read model integration in dashboard module.

## Acceptance

- Formula tests cover all MVP metrics.
- SOV denominator includes own brand and project-selected competitors only.
- Position averages only responses where own brand is mentioned.
- Used % uses distinct `run_result_id`.
- Share % uses citation row count.
- Previous period default is equal-length previous period.
- Metrics are deterministic and do not depend on LLM output percentages.
