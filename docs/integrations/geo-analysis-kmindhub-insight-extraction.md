# GEO Analysis 與 KMindHub Insight Extraction 串接流程

本文說明 GEO Analysis 如何把已保存的 AI raw answer 串接到 KMindHub Insight API，產生報表需要的結構化資料。正式 dashboard 主線使用 `geo_semantic_analysis` v4；舊 `geo_answer_analysis` 與手動 analysis-extractions endpoint 已停止作為報表來源。完整報表流程見 `geo-analysis-kmindhub-report-pipeline.md`。

## 整體資料流

1. 使用者 dispatch GEO job。
2. `geo-analysis-worker` 呼叫 `geo-tracking-api /run-requests`。
3. worker 保存 `geo_run_request`、`geo_run_result`、`geo_run_result_reference`。
4. tracking 結果成功時，worker 立即觸發 KMindHub analysis extraction。此版本仍在 query-run worker 內同步執行；大量資料或 KMindHub latency 較高時，後續應拆成 `geo.analysis-extractions` queue。
5. worker 用 job message 的 `tenantId` 解析 `tenant_kmindhub_workspace_mapping`。
6. worker 確認 tenant 是否已有 `tenant_kmindhub_extraction_task_mapping`。
7. 若沒有 mapping，GEO Analysis 依程式碼中的 schema version 建立 KMindHub extraction task。
8. worker 呼叫 `POST /extractions` 做 preview。
9. GEO application 先保留 KMindHub verification 判定，再驗證 `evidenceText` 是否可逐字回溯。
10. 只有 invalid evidence 時，由 SEO Gemini block-ID adapter 定位 untouched raw text；不重跑 KMindHub extraction。
11. 驗證通過後呼叫 `POST /extractions/commit`。
12. GEO Analysis 保存 semantic analysis、entity mention、sentiment statement 與 semantic fact rows；citation 由獨立 normalization pipeline 處理。

Insight API 失敗不會把 GEO job 改成 failed。job 仍代表跑題是否成功；analysis 狀態另外存在 `geo_run_result_analysis.status`。

## Preview 與 Commit

KMindHub `POST /extractions` 是 preview，不會把資料寫入 KMindHub MongoDB。GEO Analysis 會先使用 preview 結果做驗證，例如 enum、型別、evidence text 是否合理。

驗證通過後才呼叫 `POST /extractions/commit`。目前 GEO dashboard 不依賴 KMindHub commit item ID，而是讀取 GEO 自己保存的 normalized semantic facts。

若 preview 驗證失敗，GEO Analysis 不會 commit，並把 analysis 標記為 `failed`。

## Workspace Mapping

KMindHub Insight API 使用 `X-Workspace-Id` 隔離資料。GEO Analysis 透過 `tenant_kmindhub_workspace_mapping` 管理 tenant 對 workspace 的關係。

每個 tenant 在進行 analysis extraction 前必須先完成 workspace mapping：

- 手動綁定既有 workspace：`PUT /api/geo/integrations/kmindhub/workspace`
- 手動建立並綁定新 workspace：`POST /api/geo/integrations/kmindhub/workspace/provision`

worker 不會在第一次跑 analysis 時自動建立 workspace。若 mapping 不存在或 disabled，analysis 會 fail closed。

## Extraction Task 版本策略

GEO Analysis 的 KMindHub task schema 由程式碼定義，不由使用者在前端任意設定。每個 schema 使用：

- `task_key`
- `schema_version`
- `kmindhub_task_id`

目前使用的 task 版本：

| task_key | schema_version | 用途 |
| --- | ---: | --- |
| `geo_answer_analysis` | `1` | Legacy extraction；不再作為 dashboard 正式資料來源。 |
| `geo_semantic_analysis` | `4` | 擷取 tracked entity mention、排名、正負面情緒與 semantic facts；evidence 必須保留 raw answer 的 Markdown delimiters。 |

若未來需要新增、刪除、改變欄位語意或改變會影響 extraction 結果的 instruction，請新增新的 `schema_version`。不要直接破壞舊 task，避免歷史 analysis rows 無法解讀。

## Field 定義

目前 v4 task 使用 KMindHub 支援的基本欄位型別。多個 mention、statement 或 semantic fact 會以多個 extraction item 表示，不用 JSON/list 欄位。

| name | fieldType | lookupRole | displayName | 說明 | normalization | 範例 | GEO 驗證 | 報表用途 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `entityId` | `string` | `ignored` | Entity ID | 從 GEO entity context 複製 UUID。 | 不得自行產生。 | `00000000-...` | 必須是 context 內 UUID。 | Entity comparison、sentiment。 |
| `entityRole` | `string` | `ignored` | Entity role | `own_brand` 或 `competitor`。 | allowlist。 | `own_brand` | 必須符合 allowlist。 | Visibility、SOV。 |
| `entityName` | `string` | `ignored` | Entity name | Tracked entity 顯示名稱。 | 與 entity context 一致。 | `Acme` | 有 entity fact 時使用。 | Entity comparison。 |
| `mentioned` | `boolean` | `ignored` | 是否提及 | Answer 是否提及 tracked entity。 | boolean。 | `true` | `false` 時不得有 position / evidence。 | Visibility、mentions。 |
| `firstMentionOrder` | `int` | `ignored` | 首次順序 | Tracked entities 在整個 answer 的首次出現順序。 | 1-based。 | `1` | 必須大於等於 1。 | Average position。 |
| `sentiment` | `string` | `ignored` | 情緒 | Statement 對 tracked entity 的評價方向。 | `positive` / `negative`。 | `positive` | 必須符合 MVP allowlist。 | Sentiment breakdown。 |
| `theme` | `string` | `ignored` | 主題 | Sentiment statement 主題。 | 短詞。 | `售後服務` | sentiment fact 使用。 | Statement detail。 |
| `statement` | `string` | `ignored` | 陳述 | 品牌相關 statement。 | 忠實描述 answer。 | `Acme 售後服務完整。` | sentiment fact 使用。 | Statement detail。 |
| `factType` | `string` | `ignored` | Fact type | Semantic fact 類型。 | `product` / `service` / `topic` / `common_statement`。 | `service` | 必須符合 allowlist。 | Response detail。 |
| `value` | `string` | `ignored` | Fact value | Semantic fact 的值。 | 不新增 answer 外資訊。 | `售後服務` | semantic fact 使用。 | Response detail。 |
| `evidenceText` | `string` | `ignored` | 證據文字 | 支持 fact 的原文片段。 | 必須來自 raw answer。 | `**Acme** 售後服務完整。` | exact metadata excerpt 或 SEO source-block selection 後仍須是 normalized substring。 | Provenance、人工稽核。 |

## GEO 端驗證規則

KMindHub 的 `normalization.instruction` 是第一層約束，但 GEO application 仍會做最終驗證：

- `entityRole` 必須是 `own_brand / competitor`。
- `sentiment` 必須是 `positive / negative`。
- `factType` 必須是 `product / service / topic / common_statement`。
- `evidenceText` 若有值，會先做 Unicode NFKC 與 whitespace normalization，再確認是否出現在 raw response。
- preview `verification.passed = false` 時直接拒絕，不進 focused repair。
- 只有 invalid evidence 可交給 SEO `EvidenceTextRepairer`；它會以第二次 Gemini LLM 呼叫選擇 request-scoped source block，不重跑 extraction、不改寫文字，也不處理其他欄位錯誤。

驗證失敗時：

- `geo_run_result_analysis.status = failed`
- 保存 `error_code` / `error_message`
- 不呼叫 KMindHub commit
- 目前沒有正式手動 reanalyze endpoint；需後續補 admin-only backfill / reanalyze 工具

## Citation Boundary

Citation URL 來源以 `geo_run_result_reference` 為準，不讓 KMindHub 或 evidence repair 重新產生 URL。URL resolve、normalization、ownership 與 report aggregation 都由獨立 citation normalization module 處理。

## Retry 與失敗處理

正式 worker 會在 raw result 保存完成後自動觸發 semantic analysis。Legacy `POST /api/geo/run-results/{resultId}/analysis-extractions` 已回 `410 Gone`，不能用來補跑目前的 `geo_semantic_analysis`；手動 reanalyze / backfill 仍是後續開發項目。

## 未來欄位調整方式

新增欄位時：

1. 新增 schema version，例如 `geo_answer_analysis` v2。
2. 更新 task definition 與文件欄位表。
3. 新增 normalized table 欄位或新 table。
4. 新 run result 使用最新 version。
5. 舊資料維持原 version，不強制重算。

刪除或改變欄位語意時：

1. 不覆蓋舊 KMindHub task。
2. 新增 schema version。
3. 報表查詢依 `task_key + schema_version` 做相容處理。

這樣可以避免歷史報表資料因欄位語意改變而失真。
