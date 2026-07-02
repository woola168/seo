# High Level Plan Coverage

本文用來驗證 [High Level Plan](../mvp-04-05-analysis-metrics-implementation-plan.md) 的內容都有被 module 文件承接。

## Goal Coverage

| High-level item | Covered by |
| --- | --- |
| 從 `rawResponse` 解析品牌與競品提及 | `modules/semantic-analysis/PLAN.md` responsibility；`SPEC.md` `GeoEntityMentionFact`；`SCHEMA.md` `geo_run_result_entity_mention` |
| 解析自有品牌與競品第一次出現順序 | `modules/semantic-analysis/SPEC.md` mention rules；`SCHEMA.md` `first_mention_order` |
| 從 runner references normalize citation facts，不送 KMindHub | `modules/citation-normalization/PLAN.md` responsibility；`SPEC.md` use case；`SCHEMA.md` citation tables |
| 解析正面 / 負面輿情 | `modules/semantic-analysis/SPEC.md` `GeoSentimentFact`；`SCHEMA.md` `geo_sentiment_statement` |
| 解析產品、服務、主題與常見陳述 | `modules/semantic-analysis/SPEC.md` `GeoResponseSemanticFact`；`SCHEMA.md` `geo_response_semantic_fact` |
| Visibility / SOV / Position / Mentions | `modules/metrics-engine/SPEC.md` formulas；`SCHEMA.md` `geo_metric_snapshot` |
| Citation Count / Used % / Share % | `modules/metrics-engine/SPEC.md` formulas；citation source facts from `modules/citation-normalization` |
| Sentiment Count | `modules/metrics-engine/SPEC.md` formula；semantic source facts from `modules/semantic-analysis` |
| Daily metric snapshot 與前期比較 | `modules/metrics-engine/PLAN.md` architecture；`SPEC.md` `DailyAggregationJob` and previous period comparison；`SCHEMA.md` `geo_metric_snapshot` |

## Non-goal Coverage

| High-level non-goal | Covered by |
| --- | --- |
| 不做 alias table matching | `modules/semantic-analysis/PLAN.md` 只接收 entity names；所有 module schema 都沒有新增 alias matching table |
| 不把 SERP intent 混入 query generation 或 runner | 所有 module 都沒有新增 SERP intent 行為；runner / query generation 維持在本計畫外 |
| 不把 metrics formula 放進 KMindHub | `modules/semantic-analysis/PLAN.md` KMindHub 不應；`modules/metrics-engine/PLAN.md` owns formulas |
| 不把 references 送進 KMindHub | `modules/semantic-analysis/PLAN.md` KMindHub 不應；`modules/citation-normalization/PLAN.md` stays in `geo-analysis` |
| 不用 KMindHub 計算 URL/citation metrics | `modules/citation-normalization/PLAN.md`; `modules/metrics-engine/PLAN.md` |
| 不在 KMindHub 保存 dashboard snapshot | `modules/semantic-analysis/PLAN.md` KMindHub 不應；`modules/metrics-engine/SCHEMA.md` owns snapshot |
| 不實作優化行動建議、文案 Brief、報告匯出 | 所有 module 都沒有定義 recommendation / report generation；dashboard module 只提供 read models |
| 不改 Query Generation / Runner ADR 邊界 | Worker Integration starts after raw result persistence; no module changes query generation or runner contracts |

## Architecture Decision Coverage

| Decision | Covered by |
| --- | --- |
| Semantic analysis seam to KMindHub | `modules/semantic-analysis/SPEC.md` `GeoRunResultAnalyzer` |
| Citation normalization remains deterministic in `geo-analysis` | `modules/citation-normalization/PLAN.md` and `SPEC.md` |
| Metrics remain deterministic in `geo-analysis` | `modules/metrics-engine/PLAN.md` and `SPEC.md` |
| Dashboard reads are read-model composition, not formula ownership | `modules/dashboard-read-model/PLAN.md` and `SCHEMA.md` |
| Worker only orchestrates module use cases | `modules/worker-integration/PLAN.md` and `SCHEMA.md` |

## Rollout Coverage

| Rollout item | Covered by |
| --- | --- |
| Contracts and ports | `modules/semantic-analysis/SPEC.md` interface and repository port |
| Semantic facts schema | `modules/semantic-analysis/SCHEMA.md` |
| Citation normalization schema and use case | `modules/citation-normalization/SPEC.md` and `SCHEMA.md` |
| Metrics schema, calculator, daily job | `modules/metrics-engine/SPEC.md` and `SCHEMA.md` |
| Dashboard read APIs | `modules/dashboard-read-model/SPEC.md` |
| Worker trigger | `modules/worker-integration/SPEC.md` |
| Optional live smoke | `modules/semantic-analysis/PLAN.md` |

## Open Decision Coverage

| Open decision | Owning module |
| --- | --- |
| KMindHub endpoint 名稱與 API shape | Semantic Analysis |
| Nested structured output vs multi item facts | Semantic Analysis |
| Owned domains source | Citation Normalization |
| Source type allowlist owner | Citation Normalization |
| Generic vs split metric snapshot | Metrics Engine |
| Worker synchronous trigger vs analysis queue | Worker Integration |
| Better Performer ranking rule | Dashboard Read Model |
| 缺口與機會點是否只提供資料來源 | Dashboard Read Model |

## Acceptance Coverage

| Acceptance criterion | Covered by |
| --- | --- |
| completed run result can produce structured facts | Semantic Analysis + Citation Normalization + Worker Integration |
| facts trace back to `run_result_id` and evidence | Semantic Analysis schemas and specs; Citation schema links `reference_id` |
| mention facts support Visibility/SOV/Mentions/Position | Semantic Analysis schema + Metrics formulas |
| citation facts support Citation Count/Used%/Share%/By URL/By Domain | Citation schema + Metrics formulas |
| sentiment facts positive/negative and count | Semantic Analysis spec + Metrics formula |
| semantic facts support response detail | Semantic Analysis spec/schema + Dashboard detail output |
| metrics are deterministic | Metrics Engine plan/spec |
| SOV denominator only configured competitors | Metrics Engine SOV formula |
| entity scope metrics support competitor comparison | Metrics Engine spec + Dashboard read model |
| previous equal-length comparison and override | Metrics Engine spec + Dashboard shared query params |
| dashboard filters by project/topic/query/provider/region/language/date | Dashboard Read Model spec |
| dashboard filters by entity/ownership/source type | Dashboard Read Model spec |
| default tests do not call live KMindHub / live LLM | Worker Integration plan; Semantic Analysis fake analyzer rollout |
