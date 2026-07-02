# Dashboard Read Model Spec

## Dashboard Endpoints

```text
GET /api/geo/projects/{projectId}/metrics/overview
GET /api/geo/projects/{projectId}/metrics/topics
GET /api/geo/projects/{projectId}/metrics/queries
GET /api/geo/projects/{projectId}/citations
GET /api/geo/projects/{projectId}/sentiments
GET /api/geo/run-results/{runResultId}/analysis
```

## Shared Query Parameters

- `periodStart`
- `periodEnd`
- `comparisonStart`
- `comparisonEnd`
- `topicId`
- `queryId`
- `provider`
- `region`
- `language`
- `entityId`
- `ownership`
- `sourceType`

## Overview Output

回傳：

- KPI cards: Visibility, SOV, Position, Mentions, Used %, Share %.
- Delta for each KPI.
- Entity comparison: own brand and configured competitors.
- Optional summary of low visibility topics and negative sentiment themes.

## Topics / Queries Output

Returns per topic/query:

- Visibility.
- SOV.
- Mentions.
- Average Position.
- Best / better performer fields if product decision defines ranking rule.
- Provider/region/language breakdown if requested.

## Citations Output

Supports URL and domain grouping.

回傳：

- URL or domain.
- Title snapshot when URL scoped.
- Citation Count.
- Used %.
- Share %.
- Ownership.
- Source type.

Filters：

- `ownership`
- `sourceType`
- shared project/topic/query/provider/region/language/date filters.

## Sentiments Output

回傳：

- Entity.
- Sentiment: `positive` / `negative`.
- Theme.
- Statement count.
- Example statements or evidence excerpts, if requested.

MVP 不回傳 neutral sentiment。

## Run Result Analysis Detail Output

回傳：

- Raw prompt / query text.
- Provider / surface / model.
- Region / language.
- Raw response.
- Mention facts。
- Ranking facts。
- Citation facts。
- Sentiment statements。
- Semantic facts：product、service、topic、common_statement。

## Open Decisions

- Query 層級 Better Performer 的排序規則是否只比較 Visibility，其次 SOV / Position，或需產品另定權重。
- Dashboard 的「缺口與機會點」是否在第 4/5 計畫中只提供資料來源，實際 recommendation 文案仍由後續優化行動建議模組負責。

## Tests

- Overview endpoint returns KPI cards and deltas.
- Topic and query endpoints honor filters.
- Citations endpoint supports By URL / By Domain.
- Citations endpoint supports ownership and source type filters.
- Sentiments endpoint returns positive / negative only.
- Run result analysis endpoint returns facts and raw response context.
