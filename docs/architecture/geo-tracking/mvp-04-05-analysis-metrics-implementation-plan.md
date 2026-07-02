# GEO MVP 第 4、5 點 High Level Plan

本文只保留高層計畫、module 分工、跨 module 決策與 rollout。詳細 interface、schema、API、測試規格拆到各 module 底下，避免 plan 和 spec/schema 混在同一層。

完整文件樹：

```text
docs/architecture/geo-tracking/
├─ mvp-04-05-analysis-metrics-implementation-plan.md
└─ mvp-04-05-analysis-metrics/
   ├─ README.md
   ├─ COVERAGE.md
   └─ modules/
      ├─ semantic-analysis/
      │  ├─ PLAN.md
      │  ├─ SPEC.md
      │  └─ SCHEMA.md
      ├─ citation-normalization/
      │  ├─ PLAN.md
      │  ├─ SPEC.md
      │  └─ SCHEMA.md
      ├─ metrics-engine/
      │  ├─ PLAN.md
      │  ├─ SPEC.md
      │  └─ SCHEMA.md
      ├─ dashboard-read-model/
      │  ├─ PLAN.md
      │  ├─ SPEC.md
      │  └─ SCHEMA.md
      └─ worker-integration/
         ├─ PLAN.md
         ├─ SPEC.md
         └─ SCHEMA.md
```

## 1. Goal

MVP 第 4 點「解析成結構化資料」：

- 從 AI / SERP runner 保存的 `rawResponse` 解析品牌與競品提及。
- 解析整個 raw response 中自有品牌與競品第一次出現順序，作為平均排名來源。
- 從 runner references deterministic normalize citation facts，不送 KMindHub。
- 解析正面 / 負面輿情。
- 解析產品、服務、主題與常見陳述，供 response detail 與後續優化建議使用。

MVP 第 5 點「核心指標與前期比較」：

- Visibility 能見度。
- SOV 聲量佔比。
- Position 平均排名。
- Mentions 品牌提及。
- Citation Count 引用數。
- Used % 引用採用率。
- Share % 引用份額。
- Sentiment Count 正負面數量。
- Daily metric snapshot 與前期比較 delta。

## 2. Non Goals

- 不在本輪做 alias table matching；品牌與競品判斷先交給 KMindHub semantic analysis 依品牌 knowledge 與輸入 entity 名稱判斷。
- 不把 SERP intent 判斷混入 query generation 或 runner。
- 不把 metrics formula 放進 KMindHub。
- 不把 runner 已提供的 references 送進 KMindHub 做 URL 指標或 citation 指標計算。
- 不用 KMindHub 計算或判斷 Used %、Share %、By URL、By Domain、owned citation share。
- 不在 KMindHub 內保存 GEO dashboard snapshot。
- 不實作優化行動建議、文案 Brief、報告匯出或 Phase 2 文案系統。
- 不改 `geo-tracking` 的 Query Generation / Runner ADR 邊界。

## 3. Architecture Decision

第 3 層解析層解耦到 `younilab-kmindhub`；第 4 層指標引擎留在 `younilab-seo / geo-analysis`。

```text
geo-tracking runner
  -> rawResponse + references + provider metadata
  -> geo-analysis 保存 geo_run_result / geo_run_result_reference
  -> geo-analysis deterministic normalizes citation facts from references
  -> geo-analysis 呼叫 KMindHub semantic analysis interface
  -> KMindHub 回傳 mention / position / sentiment / semantic facts
  -> geo-analysis 保存 citation + semantic facts
  -> geo-analysis deterministic 計算 metrics snapshot
  -> geo-analysis API 提供 dashboard / report 查詢
```

本文使用的 `seam` 指可替換接縫點：caller 只依賴穩定 interface，不知道背後 adapter 的具體實作。以本計畫來說，`geo-analysis` 只呼叫 `GeoRunResultAnalyzer`，背後可以接 KMindHub HTTP adapter、fake analyzer，或未來改接其他 analysis runtime。

## 4. Module Map

| Module | 責任 | 詳細文件 |
| --- | --- | --- |
| Semantic Analysis | 呼叫 KMindHub，從 raw response 產生 mention / position / sentiment / semantic facts | [PLAN](mvp-04-05-analysis-metrics/modules/semantic-analysis/PLAN.md)、[SPEC](mvp-04-05-analysis-metrics/modules/semantic-analysis/SPEC.md)、[SCHEMA](mvp-04-05-analysis-metrics/modules/semantic-analysis/SCHEMA.md) |
| Citation Normalization | 從 runner references 產生 normalized citation facts；不呼叫 KMindHub | [PLAN](mvp-04-05-analysis-metrics/modules/citation-normalization/PLAN.md)、[SPEC](mvp-04-05-analysis-metrics/modules/citation-normalization/SPEC.md)、[SCHEMA](mvp-04-05-analysis-metrics/modules/citation-normalization/SCHEMA.md) |
| Metrics Engine | 從 facts deterministic 計算核心 KPI、daily snapshots、前期比較 | [PLAN](mvp-04-05-analysis-metrics/modules/metrics-engine/PLAN.md)、[SPEC](mvp-04-05-analysis-metrics/modules/metrics-engine/SPEC.md)、[SCHEMA](mvp-04-05-analysis-metrics/modules/metrics-engine/SCHEMA.md) |
| Dashboard Read Model | 提供 overview / query / topic / citation / sentiment / run detail read APIs | [PLAN](mvp-04-05-analysis-metrics/modules/dashboard-read-model/PLAN.md)、[SPEC](mvp-04-05-analysis-metrics/modules/dashboard-read-model/SPEC.md)、[SCHEMA](mvp-04-05-analysis-metrics/modules/dashboard-read-model/SCHEMA.md) |
| Worker Integration | 在 runner result 保存後觸發 semantic analysis、citation normalization、metric refresh | [PLAN](mvp-04-05-analysis-metrics/modules/worker-integration/PLAN.md)、[SPEC](mvp-04-05-analysis-metrics/modules/worker-integration/SPEC.md)、[SCHEMA](mvp-04-05-analysis-metrics/modules/worker-integration/SCHEMA.md) |

## 5. Coverage Matrix

| Requirement | Owning module |
| --- | --- |
| 品牌是否被提及 | Semantic Analysis |
| 品牌在回答中相對排名 | Semantic Analysis |
| 同一回應同一品牌多次提及只計 1 次 | Semantic Analysis + Metrics Engine |
| 競品提及 | Semantic Analysis |
| 引用 URL / domain | Citation Normalization |
| 引用是否為自有網站 | Citation Normalization |
| 產品、服務、主題與常見陳述 | Semantic Analysis |
| 正負面輿情 | Semantic Analysis |
| Visibility / SOV / Position / Mentions | Metrics Engine |
| Citation Count / Used % / Share % | Metrics Engine |
| Sentiment Count | Metrics Engine |
| 每日聚合與前期比較 | Metrics Engine |
| Dashboard query filters | Dashboard Read Model |
| 跑題完成後自動產生 facts / metrics | Worker Integration |

## 6. Rollout

1. Contracts and ports：新增 analysis command/result contracts 與 `GeoRunResultAnalyzer` port。
2. Semantic facts schema：新增 analysis、mention、sentiment、semantic fact persistence。
3. Citation normalization：新增 citation normalization schema 與 deterministic normalization use case。
4. Metrics engine：新增 metric snapshot schema、formula calculator、daily aggregation job。
5. Dashboard read APIs：新增 overview / topics / queries / citations / sentiments / run detail endpoints。
6. Worker integration：runner result 保存後觸發 analysis、citation normalization、metrics invalidation / aggregation。
7. Optional live smoke：使用已保存 Gemini 或 Google AIO result 呼叫 KMindHub analysis，只驗證 semantic facts；citation facts 不由 KMindHub 回傳。

## 7. Open Decisions

- Semantic Analysis：KMindHub endpoint 名稱與正式 API shape。
- Semantic Analysis：KMindHub 是否直接支援 nested mention/sentiment/semantic structured output，或先回多個 item facts。
- Citation Normalization：`owned_domains` 是否只從 primary brand website_url 推導，或新增 project-level explicit owned domains table。
- Citation Normalization：`source_type` 第一版 allowlist 要由誰維護；若沒有維護者，MVP 應只保留 `owned_site` / `unknown`。
- Metrics Engine：Metric snapshot 是否先用 generic `geo_metric_snapshot`，或直接拆成 query/citation/sentiment snapshots。
- Worker Integration：Analysis trigger 第一版採 worker 同步或獨立 analysis queue。
- Dashboard Read Model：Query 層級 Better Performer 的排序規則是否只比較 Visibility，其次 SOV / Position，或需產品另定權重。
- Dashboard Read Model：Dashboard 的「缺口與機會點」是否在第 4/5 計畫中只提供資料來源，實際 recommendation 文案仍由後續優化行動建議模組負責。

## 8. Acceptance Criteria

- `geo-analysis` 能對已保存的 completed run result 產生 structured facts。
- Structured facts 可回溯 `run_result_id` 與 evidence text。
- Mention facts 可支援 Visibility、SOV、Mentions、Position 計算。
- Citation facts 由 `geo-analysis` 從 runner references deterministic 產生，不送 KMindHub，並可支援 Citation Count、Used %、Share %、By URL、By Domain。
- Sentiment facts MVP 僅包含 positive / negative，並可聚合 positive / negative count。
- Semantic facts 可支援 response detail 顯示產品、服務、主題與常見陳述。
- Metrics engine 使用 deterministic code 計算，不使用 LLM 直接輸出 KPI。
- SOV 分母只包含 project 設定的 competitor entities。
- Entity scope metrics 可支援自有品牌與競品比較。
- 前期比較預設使用同長前期，且可由 request 覆寫 comparison range。
- Dashboard read API 可依 project、topic、query、provider、region、language、date range 查詢。
- Dashboard read API 可依 entity、ownership、source type 查詢相關 analysis/metrics read model。
- Default test suite 不需要 live KMindHub / live LLM。
