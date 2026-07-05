# GEO MVP 第 4、5 點分階段開發計畫

本文記錄可逐步實作的細分計畫，目標是避免一次跨越 contracts、schema、repository、use case、API、worker 多個邊界。

## 開發原則

- 一次只改一個主要邊界。
- 以 `packages/younilab-seo/src/younilab_seo/geo_analysis` 為核心實作位置。
- API app 與 worker app 只負責 thin transport / composition / orchestration，不放公式、semantic parsing 或 URL normalization。
- 採 additive migration 演進既有 analysis tables，不重建既有 `011_geo_analysis_kmindhub_extraction_patch.sql` 資料結構。
- Semantic Analysis 第一版沿用既有 KMindHub extraction API，但必須包在新的 `GeoRunResultAnalyzer` port 後面。
- Citation Normalization 與 Metrics Engine 不呼叫 KMindHub。

## Phase 0：Baseline Audit

目的：先確認現況與缺口，不改功能程式碼。

已確認現況：

- 既有 analysis schema 同時存在於 `deploy/local/postgresql/004_geo_analysis_schema.sql` 與 `deploy/local/postgresql/011_geo_analysis_kmindhub_extraction_patch.sql`。
- 目前已有：
  - `geo_run_result_analysis`
  - `geo_run_result_entity_mention`
  - `geo_run_result_statement`
  - `geo_run_result_citation_classification`
- 目前尚未有：
  - `geo_response_semantic_fact`
  - `geo_run_result_citation_normalization`
  - `geo_run_result_citation`
  - `geo_metric_snapshot`
- 既有 KMindHub integration 由 `RunKMindHubAnalysisExtraction` 使用 `KMindHubWorkspaceClient.preview_text_extraction` 與 `commit_extraction_items` 完成。
- Worker 目前在 successful tracking result 後可呼叫 `analysis_extractor.execute(...)`。
- API 目前已有相容入口 `POST /api/geo/run-results/{resultId}/analysis-extractions`。
- API test fake repository 是 `GeoApiStore`，後續 persistence 變更必須同步支援 Postgres repository 與 fake store。

Phase 0 後續檢查表：

- 確認 `004_geo_analysis_schema.sql` 與 patch migrations 的重複 schema 是否為本 repo 慣例。
- 確認現有 `GeoRunResultAnalysisRecord` 是否只保留 lifecycle 狀態，facts 另外用 read model 查詢。
- 確認 legacy citation classification 是否保留唯讀相容，新的 citation facts 以 `geo_run_result_citation` 為準。

## Phase 1：Semantic Contracts Only

只新增 semantic analysis 的 application contracts 與 port，不接 DB、不接 KMindHub。

預期變更：

- 新增 `AnalyzeGeoRunResultCommand`。
- 新增 `GeoAnalysisEntityContext` / `GeoAnalysisEntityInput`。
- 新增 `GeoRunResultAnalysis`。
- 新增 `GeoEntityMentionFact`。
- 新增 `GeoSentimentFact`。
- 新增 `GeoResponseSemanticFact`。
- 新增 `GeoRunResultAnalyzer` port。

驗證：

- Contract JSON shape tests。
- Enum validation tests：entity role、sentiment、semantic fact type。
- Position / confidence 基本驗證。

## Phase 2：Semantic Persistence Schema

只做 semantic facts 的 migration、SQLModel、repository method skeleton。

預期變更：

- 新增 patch migration，例如 `012_geo_analysis_analysis_metrics_patch.sql`。
- 以 additive 方式擴充既有 analysis / mention / statement schema。
- 新增 `geo_response_semantic_fact`。
- 更新 Postgres SQLModel rows。
- 新增 repository save/query semantic facts 的 method。
- 更新 `GeoApiStore` 對應 fake persistence。

驗證：

- Postgres model structure tests。
- Repository save/query tests。
- Fake store 與 Postgres repository contract 行為一致。

## Phase 3：Semantic Use Case with Fake Analyzer

只實作 `AnalyzeRunResult`，先使用 fake analyzer。

預期變更：

- 載入 run result、query、topic、project、active own brand、active competitors。
- completed run result 才呼叫 analyzer。
- failed 或 empty raw response 保存 failed analysis，不呼叫 analyzer。
- analyzer exception 保存 failed analysis。
- mention / sentiment / semantic facts 與 lifecycle 在同一個 transaction 保存。

驗證：

- completed run result succeeds with fake analyzer。
- failed run result does not call analyzer。
- analyzer failure persists failed analysis。
- facts trace back to `run_result_id` and evidence。

## Phase 4：KMindHub Adapter Wrapper

只把既有 KMindHub extraction flow 包成 `GeoRunResultAnalyzer` adapter。

預期變更：

- 沿用 `KMindHubWorkspaceClient`。
- Adapter 負責把 `AnalyzeGeoRunResultCommand` map 到既有 extraction task call。
- Adapter 負責把 KMindHub preview / commit result map 回 semantic facts。
- 保留 legacy `RunKMindHubAnalysisExtraction` 相容入口，內部逐步轉呼叫新 use case。

驗證：

- Adapter request mapping tests。
- Adapter response mapping tests。
- timeout / unavailable / validation error mapping tests。
- 既有 analysis extraction tests 繼續通過。

## Phase 5：Citation Contracts + Normalizer

只做 citation normalization 的純 application 邏輯，不碰 metrics。

預期變更：

- 新增 citation normalization contracts。
- 實作 URL/domain normalizer。
- 實作 ownership rule。
- MVP source type 只輸出 `owned_site` / `unknown`。
- 不新增 explicit owned domains table。

驗證：

- normalized URL/domain tests。
- own brand website domain -> `owned` / `owned_site`。
- unmatched domain -> `other` / `unknown`。
- missing references returns zero facts。

## Phase 6：Citation Persistence

只做 citation normalization lifecycle 與 citation facts persistence。

預期變更：

- 新增 `geo_run_result_citation_normalization`。
- 新增 `geo_run_result_citation`。
- 新增 repository save/query methods。
- 同 normalizer version 重跑需 idempotent。
- 更新 `GeoApiStore` fake persistence。

驗證：

- Repository save/query tests。
- Idempotent rerun tests。
- Every citation fact links to original `reference_id`。

## Phase 7：Metrics Formula Core

只做 metrics calculator，完全 in-memory，不碰 DB/API。

預期公式：

- Visibility。
- Mentions。
- SOV。
- Average Position。
- Citation Count。
- Used %。
- Share %。
- Sentiment Count。
- Previous equal-length comparison。

驗證：

- Formula unit tests 覆蓋所有 MVP metrics。
- SOV denominator only includes configured competitors。
- Used % numerator uses distinct `run_result_id`。
- Share % numerator and denominator use citation row count。

## Phase 8：Metrics Persistence

只做 `geo_metric_snapshot`。

預期變更：

- 新增 `geo_metric_snapshot` migration 與 SQLModel row。
- 實作 snapshot upsert。
- 實作 snapshot query。
- 明確 nullable unique strategy：優先使用 generated key 或 partial unique indexes，避免 PostgreSQL nullable unique 語意誤判。

驗證：

- Snapshot repository tests。
- Idempotent upsert tests。
- Filtered snapshot query tests。

## Phase 9：CalculateGeoMetrics Use Case

把 formula core 接到 repository source query。

預期變更：

- `CalculateGeoMetrics` 載入 completed run results + semantic facts + citation facts。
- 計算 current period。
- 計算 comparison period。
- upsert metric snapshots。
- 不接 API、不接 worker。

驗證：

- Application integration-style tests。
- Period validation tests。
- Explicit comparison range override tests。

## Phase 10：Dashboard Read Models

只做 application read use cases，不先開 HTTP routes。

預期 read models：

- overview。
- topics。
- queries。
- citations。
- sentiments。
- run result analysis detail。

驗證：

- Read model tests with fake repository。
- Filters: project/topic/query/provider/region/language/date/entity/ownership/source type。

## Phase 11：Dashboard HTTP API

只加 API DTO / routes / composition。

預期 endpoints：

- `GET /api/geo/projects/{projectId}/metrics/overview`
- `GET /api/geo/projects/{projectId}/metrics/topics`
- `GET /api/geo/projects/{projectId}/metrics/queries`
- `GET /api/geo/projects/{projectId}/citations`
- `GET /api/geo/projects/{projectId}/sentiments`
- `GET /api/geo/run-results/{runResultId}/analysis`

驗證：

- API route tests。
- Permission / tenant / resource grant scoping tests。
- Problem Details error behavior。

## Phase 12：Worker Hook

只把 completed result 後續 pipeline 接進 worker。

預期變更：

- tracking result 保存成功後呼叫 semantic analysis。
- semantic analysis 後呼叫 citation normalization。
- facts 保存後觸發 metrics calculation。
- 單筆 result 失敗要 log 並繼續，不讓整個 worker message 因單筆 analysis 失敗而失敗。

驗證：

- Completed result triggers semantic / citation / metrics。
- Failed result skips analysis pipeline。
- Per-result failure is logged and isolated。

## Phase 13：Backfill + Internal Operations

最後才做補償與手動觸發。

預期變更：

- 新增 `AnalyzePendingRunResults`。
- 新增 analysis backfill endpoint。
- 新增 metrics calculate endpoint。
- Batch per-result failure isolation。

驗證：

- Compensation job processes missing analysis / citation normalization。
- Batch continues after one result fails。
- Internal endpoint API tests。

## Phase 14：Cleanup + Compatibility Pass

最後整理舊命名與相容層。

預期變更：

- 確認 legacy `analysis-extractions` 行為仍可用。
- 移除不再使用的 helper。
- 文件補上實際資料流與 phase 對照。
- 跑 package / API / worker 測試。

驗證：

```powershell
uv run --package younilab-seo pytest packages/younilab-seo/tests/geo_analysis
uv run --package younilab-geo-analysis-api pytest apps/geo-analysis-api/tests
uv run --package younilab-geo-analysis-worker pytest apps/geo-analysis-worker/tests
```

