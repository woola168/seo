# Dashboard Read Model Plan

## Responsibility

Dashboard Read Model 負責把 metrics snapshots 與 analysis facts 組成前端可用 read APIs。

Owned reads:

- KPI overview。
- Topic performance。
- Query performance。
- Citation table。
- Sentiment table。
- Run result analysis detail。
- Entity comparison for own brand vs competitors。

此 module 不計算公式，不呼叫 KMindHub，不直接解析 raw response。若 period 尚未有 snapshot，可呼叫 Metrics Engine fallback 計算，但公式仍屬 Metrics Engine。

## Architecture

```text
Dashboard endpoint
  -> validate filters
  -> query metric snapshots and facts
  -> compose read model
  -> return API response
```

## Rollout Slice

1. Add overview endpoint.
2. Add citations endpoint with URL/domain grouping.
3. Add sentiments endpoint.
4. Add query/topic performance endpoints.
5. Add run result analysis detail endpoint.
6. Replace frontend mock data progressively.

## Acceptance

- Overview returns KPI cards and deltas.
- Citations support By URL / By Domain, ownership filter, source type filter.
- Sentiments return positive / negative counts only.
- Run result detail returns raw response plus mention, ranking, citation, sentiment, semantic facts.
- Read APIs support project/topic/query/provider/region/language/date range filters.
