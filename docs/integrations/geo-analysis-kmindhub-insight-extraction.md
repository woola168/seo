# GEO Analysis 與 KMindHub Insight Extraction 串接流程

本文說明 GEO Analysis 如何把已保存的 AI raw answer 串接到 KMindHub Insight API，產生報表需要的結構化資料。此流程只處理資料擷取與保存，不負責正式報表聚合 API。

## 整體資料流

1. 使用者 dispatch GEO job。
2. `geo-analysis-worker` 呼叫 `geo-tracking-api /run-requests`。
3. worker 保存 `geo_run_request`、`geo_run_result`、`geo_run_result_reference`。
4. tracking 結果成功時，worker 立即觸發 KMindHub analysis extraction。此版本仍在 query-run worker 內同步執行；大量資料或 KMindHub latency 較高時，後續應拆成 `geo.analysis-extractions` queue。
5. worker 用 job message 的 `tenantId` 解析 `tenant_kmindhub_workspace_mapping`。
6. worker 確認 tenant 是否已有 `tenant_kmindhub_extraction_task_mapping`。
7. 若沒有 mapping，GEO Analysis 依程式碼中的 schema version 建立 KMindHub extraction task。
8. worker 呼叫 `POST /extractions` 做 preview。
9. GEO application 驗證 preview 結果。
10. 驗證通過後呼叫 `POST /extractions/commit`。
11. GEO Analysis 保存 `geo_run_result_analysis` 與 mention、statement、citation classification rows。

Insight API 失敗不會把 GEO job 改成 failed。job 仍代表跑題是否成功；analysis 狀態另外存在 `geo_run_result_analysis.status`。

## Preview 與 Commit

KMindHub `POST /extractions` 是 preview，不會把資料寫入 KMindHub MongoDB。GEO Analysis 會先使用 preview 結果做驗證，例如 enum、型別、evidence text 是否合理。

驗證通過後才呼叫 `POST /extractions/commit`。commit 成功後，GEO Analysis 會保存 `kmindhub_commit_batch_id` 與 `kmindhub_item_id`，方便後續稽核與追蹤。

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
| `geo_answer_analysis` | `1` | 擷取單筆 AI answer 的摘要、情緒、主題、entity mention 與 statement。 |
| `geo_semantic_analysis` | `4` | 擷取 tracked entity mention、排名、正負面情緒與 semantic facts；evidence 必須保留 raw answer 的 Markdown delimiters。 |

若未來需要新增、刪除、改變欄位語意或改變會影響 extraction 結果的 instruction，請新增新的 `schema_version`。不要直接破壞舊 task，避免歷史 analysis rows 無法解讀。

## Field 定義

目前 task 使用 KMindHub 支援的基本欄位型別。多個 mention 或 statement 會以多個 extraction item 表示，不用 JSON/list 欄位。

| name | fieldType | lookupRole | displayName | 說明 | normalization | 範例 | GEO 驗證 | 報表用途 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `summary` | `string` | `ignored` | 答案摘要 | 用繁中摘要 AI answer 的主要結論。 | 1 到 3 句，不新增原文沒有的資訊。 | `AI 建議優先評估具備在地服務能力的供應商。` | 可為空；若有值需為字串。 | AI answer analysis、run detail。 |
| `overallSentiment` | `string` | `ignored` | 整體情緒 | AI answer 的整體情緒。 | 只能回 `positive / neutral / negative / mixed / unknown`。 | `neutral` | 必須符合 allowlist。 | Overview KPI、sentiment summary。 |
| `theme` | `string` | `ignored` | 主題 | 答案主要討論的主題或評估面向。 | 回傳短詞。 | `售後服務` | 可為空；若有值需為字串。 | Topic performance、AI answer analysis。 |
| `entityName` | `string` | `ignored` | 提及對象 | 答案中被提及的品牌、競品或其他公司/產品。 | 只回傳原文中明確出現或可由別名對應的名稱。 | `Acme` | 有值時才建立 mention row。 | Competitor/SOV、mentions。 |
| `entityType` | `string` | `ignored` | 提及類型 | 提及對象的類型。 | 只能回 `own_brand / competitor / other`。 | `competitor` | 必須符合 allowlist。 | SOV、競品比較。 |
| `mentionCount` | `int` | `ignored` | 提及次數 | entity 在答案中被提及的次數。 | 只回傳 0 或正整數。 | `2` | 必須是 0 或正整數。 | mention count、SOV。 |
| `statementText` | `string` | `ignored` | 重要陳述 | 可供報表觀察的關鍵陳述。 | 必須忠實來自原文，不創造新陳述。 | `Acme 在售後服務上較具優勢。` | 有值時才建立 statement row。 | AI answer analysis。 |
| `statementSentiment` | `string` | `ignored` | 陳述情緒 | 單一 statement 的情緒或評價方向。 | 只能回 `positive / neutral / negative / mixed / unknown`。 | `positive` | 必須符合 allowlist。 | statement 分析、情緒 drill-down。 |
| `subjectEntityName` | `string` | `ignored` | 陳述對象 | statement 主要描述的品牌或競品。 | 沒有特定對象可留空。 | `Acme` | 可為空；若有值需為字串。 | statement 與 entity 對應。 |
| `evidenceText` | `string` | `ignored` | 證據文字 | 支持 mention 或 statement 的原文片段。 | 必須能在 raw answer 中找到。 | `Acme 在售後服務上較具優勢。` | 會先做 Unicode NFKC 與 whitespace normalization；若仍找不到才視為失敗。 | 人工稽核、報表引用。 |

## GEO 端驗證規則

KMindHub 的 `normalization.instruction` 是第一層約束，但 GEO application 仍會做最終驗證：

- `overallSentiment`、`statementSentiment` 必須是 `positive / neutral / negative / mixed / unknown`。
- `entityType` 必須是 `own_brand / competitor / other`。
- `mentionCount` 必須是 0 或正整數。
- `evidenceText` 若有值，會先做 Unicode NFKC 與 whitespace normalization，再確認是否出現在 raw response。
- preview `verification.passed = false` 時，不 commit。

驗證失敗時：

- `geo_run_result_analysis.status = failed`
- 保存 `error_code` / `error_message`
- 不呼叫 KMindHub commit
- 可透過 retry endpoint 重新分析

## Citation Classification

Citation URL 來源以 `geo_run_result_reference` 為準，不讓 KMindHub 重新產生 URL。GEO Analysis 會在 analysis 階段建立 `geo_run_result_citation_classification`。

第一版 classification 先保守寫入 `unknown`，並保留：

- `run_result_reference_id`
- `classification`
- `matched_domain`
- `confidence`
- `source`

後續可在不改 raw reference 的前提下，補上 own / competitor / third_party 的 rule-based 或 domain mapping 分類。

## Retry 與失敗處理

正式 worker 會在 raw result 保存完成後自動觸發 analysis extraction。若後續需要手動補跑，可呼叫：

```http
POST /api/geo/run-results/{resultId}/analysis-extractions
```

這個 endpoint 會套用目前登入者的 tenant 與 GEO resource grant 邊界。跨 tenant 或 grant 外 result 會回 404。

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
