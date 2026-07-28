# GEO 分析後端 Workflow 規劃

> 已於 2026-07-27 封存。本文件保留早期後端規劃，其中多項「尚未實作」描述已過期；請改讀 [GEO Analysis 現況、架構與 Roadmap](../../../geo-analysis-current-state-and-roadmap.md)。

本文整理 GEO 功能從品牌與 query 設定、跑題、結果保存到報表計算的後端流程，並以目前既有 API 與資料表規劃評估可支援範圍與缺少的程式模組。

本文不盤點前端缺口，重點放在 `geo-analysis`、`geo-tracking`、資料表、queue、worker 與報表計算流程。

## 1. 系統責任切分

目前建議維持兩個服務的責任邊界：

| 服務 | 主要責任 |
| --- | --- |
| `geo-analysis` | GEO 主系統，負責專案、品牌、競品、topic、query、schedule、job、queue orchestration、結果保存、分析計算與報表 API。 |
| `geo-tracking` | 跑題引擎，負責 Query Research、Query Generation、實際呼叫 Gemini 或其他 AI provider，並回傳原始回答與 references。 |

`geo-tracking` 目前不負責資料庫寫入，正式資料保存與報表計算應由 `geo-analysis` 負責。

整體資料流如下：

```text
使用者設定品牌 / 競品 / query
        ↓
geo-analysis 保存設定
        ↓
手動或排程建立 run job
        ↓
queue / worker 派送任務
        ↓
worker 呼叫 geo-tracking 跑題
        ↓
geo-tracking 回傳 raw answer / references / status
        ↓
geo-analysis 保存結果
        ↓
geo-analysis 分析 mention / citation / sentiment / visibility / SOV
        ↓
報表 API 提供前端呈現
```

## 2. 使用者流程與後端動作

### 2.1 建立 GEO Project

使用者先建立一個 GEO project，用來對應客戶、SEO task、地區、語言、預算與後續分析範圍。

目前資料表規劃可對應：

| 資料表 | 用途 |
| --- | --- |
| `geo_project` | 保存 GEO project、客戶、SEO task、預設地區、語言、狀態與預算。 |
| `geo_market` | 保存同一 project 下不同地區與語言的市場設定。 |

此階段產生的是整個 GEO workflow 的 root context。後續品牌、競品、topic、query、schedule、job 都應掛在 project 底下。

### 2.2 設定品牌、競品與別名

使用者設定主要品牌、競品品牌、網站、產品名稱與常見別名。這些資料後續會用於判斷 AI answer 是否提及自己品牌、競品或相關產品。

目前資料表規劃可對應：

| 資料表 | 用途 |
| --- | --- |
| `geo_entity` | 保存品牌、競品、網站或其他追蹤對象。 |
| `geo_entity_alias` | 保存 entity 的別名、產品名、縮寫或常見寫法。 |

目前可透過 `geo_project_id` 加上 `geo_entity.type` 判斷某個競品屬於哪個 project。例如某筆 entity 是 `competitor`，且掛在某個 project 下，即代表它是該 project 主要品牌的競品。

若未來需要表達更細的競品關係，例如同一個 competitor 在不同品牌下有不同競爭權重、產品線或比較維度，可再新增類似 `geo_entity_relationship` 的關聯表。

### 2.3 設定 Topic、Keyword 與 Query

使用者建立 topic、keyword 與 query。query 是後續會定期拿去問 AI model 的自然語言問題。

目前資料表規劃可對應：

| 資料表 | 用途 |
| --- | --- |
| `geo_topic` | query 分組，例如「中藥保健食品推薦」。 |
| `geo_query` | 實際要跑題的自然語言問題。 |
| `geo_query_keyword` | query 相關 keyword、來源與搜尋量。 |

範例：

```text
Topic: 中藥保健食品推薦
Keyword: 中藥保健食品、黃連膏、港香蘭推薦
Query: 台灣有哪些中藥保健食品品牌推薦？
```

這一層是 GEO 分析的核心輸入資料。後續跑題、報表與趨勢都會以 query、topic、platform、時間為主要分析維度。

### 2.4 Query Research

Query Research 的用途是根據品牌、競品、keyword、市場與 audience，先研究適合產生哪些 query 方向。

目前 `geo-tracking` 已提供：

```http
POST /api/v1/geo-tracking/query-research
```

主要輸入包含：

| 欄位 | 說明 |
| --- | --- |
| `provider` | 使用的 provider，例如 `dummy` 或 `gemini`。 |
| `brandName` | 主要品牌名稱。 |
| `competitorBrands` | 競品品牌名稱。 |
| `keywords` | 使用者輸入或系統整理的 keyword。 |
| `region` | 目標地區，例如 `TW`。 |
| `language` | 目標語言，例如 `zh-TW`。 |
| `marketType` | 市場類型，例如 `b2c` 或 `b2b_procurement`。 |
| `audience` | 目標受眾。 |

主要輸出包含：

| 欄位 | 說明 |
| --- | --- |
| `researchContext` | Query Research 整理出的研究脈絡。 |
| `searchedKeywords` | 實際用於研究的 keyword。 |
| `sourceUrls` | 查詢或 grounding 參考來源。 |

目前缺口是 `geo-analysis` 尚未有完整的 Query Research 保存表。若 research 結果需要被保存、審核、重用或追蹤版本，建議補：

| 建議資料表 | 用途 |
| --- | --- |
| `geo_query_research_run` | 保存每次 Query Research 執行紀錄、輸入條件、provider、狀態與時間。 |
| `geo_query_research_result` | 保存 `researchContext`、`searchedKeywords`、`sourceUrls` 與錯誤資訊。 |

### 2.5 Query Generation 與 Shortlist

Query Generation 的用途是根據 project、品牌、競品、keyword、topic、intent、audience 與 research context 產生候選 query。

目前 `geo-tracking` 已提供：

```http
POST /api/v1/geo-tracking/query-generation
```

主要輸出是 generated query drafts，包含 query text、keywords、topic、intent、branded / non-branded、metadata 與 status。

建議後端流程：

```text
geo-analysis 呼叫 geo-tracking query-generation
        ↓
保存 generation run
        ↓
保存 query drafts
        ↓
使用者 shortlist / accept
        ↓
正式寫入 geo_query
```

目前 `geo_query` 可以保存正式 query，但缺少候選 query、草稿與 shortlist 的保存結構。若要支援使用者挑選 AI 產生的 query 後再保存，建議補：

| 建議資料表 | 用途 |
| --- | --- |
| `geo_query_generation_run` | 保存每次 Query Generation 執行紀錄與輸入條件。 |
| `geo_query_draft` | 保存 AI 產生但尚未正式啟用的 query draft。 |
| `geo_query_draft_keyword` | 保存 draft query 相關 keyword。 |
| `geo_query_draft_selection` | 保存 shortlist、accepted、rejected 等使用者選擇紀錄。 |

### 2.6 設定 AI Platform 與 Schedule

使用者選擇 query 要在哪些 AI platform 或 model 上執行，並設定執行頻率。

目前資料表規劃可對應：

| 資料表 | 用途 |
| --- | --- |
| `geo_ai_platform` | 保存 provider、platform、model、是否啟用等設定。 |
| `geo_query_platform` | 保存 query 與 platform 的派送關係。 |
| `geo_query_schedule` | 保存定期跑題規則、timezone、next run 等資訊。 |

這一層只決定「什麼 query 要在什麼 model、什麼時間跑」，不直接執行 AI 呼叫。

### 2.7 建立 Run Job

當使用者手動跑題，或排程時間到了，`geo-analysis` 會建立一筆 run job。

目前資料表規劃可對應：

| 資料表 | 用途 |
| --- | --- |
| `geo_query_run_job` | 保存每次 query run job 的狀態、dedupe key、dispatch 資訊、錯誤資訊與外部 run id。 |

建議流程：

```text
選定 query + platform + model
        ↓
檢查 schedule 或 manual run
        ↓
建立 geo_query_run_job
        ↓
產生 dedupe_key
        ↓
狀態為 pending
```

`dedupe_key` 的用途是避免同一個 query、platform、時間點被重複派送。

### 2.8 Queue 與 Worker 派送

這是目前已知缺少的主要部分。

正式流程應如下：

```text
scheduler 掃描 due schedules
        ↓
建立 geo_query_run_job
        ↓
publisher 發送 message 到 queue / Pub/Sub
        ↓
worker 消費 message
        ↓
worker 呼叫 geo-tracking /run-requests
        ↓
worker 回寫 job 狀態與結果
```

目前資料表規劃已包含部分 orchestration 表：

| 資料表 | 用途 |
| --- | --- |
| `geo_message_dispatch_log` | 保存 message publish 嘗試、broker message id、錯誤與重試資訊。 |
| `geo_worker_lease` | 保存 worker lease，避免多個 worker 重複處理同一批 job。 |
| `geo_job_dispatch_event` | 保存 job 狀態變化與 dispatch audit trail。 |
| `geo_external_run_reference` | 保存外部 runner 的 run id、callback status、result location 與錯誤資訊。 |

目前缺少的程式包含：

| 缺少程式 | 說明 |
| --- | --- |
| queue publisher adapter | 抽象化 queue 發送行為，避免綁死 GCP Pub/Sub 或自架 queue。 |
| queue backend implementation | 實作 GCP Pub/Sub、Redis Stream、RabbitMQ 或其他 queue backend。 |
| scheduler process | 掃描 due schedules 並建立 jobs。 |
| worker process | 消費 queue message 並呼叫 `geo-tracking`。 |
| lease manager | 控制 worker lease、避免重複處理。 |
| retry / dead-letter handling | 處理 provider timeout、quota、暫時性錯誤與不可重試錯誤。 |
| callback / ingestion handler | 接收外部 runner 結果或由 worker 回寫結果。 |

### 2.9 呼叫 geo-tracking 執行跑題

目前 `geo-tracking` 已提供：

```http
POST /api/v1/geo-tracking/run-requests
```

它可以接收多個 query，並回傳每個 query 的執行結果。

主要輸入包含：

| 欄位 | 說明 |
| --- | --- |
| `seoTaskId` | SEO task id。 |
| `provider` | provider，例如 `dummy` 或 `gemini`。 |
| `timing` | `run_now` 或 `next_cycle`。 |
| `queries` | 要執行的 query 清單。 |

主要輸出包含：

| 欄位 | 說明 |
| --- | --- |
| `runRequestId` | 這次 tracking request 的 id。 |
| `results` | 每個 query 的跑題結果。 |
| `provider` | 實際 provider。 |
| `model` | 實際 model。 |
| `status` | `completed` 或 `failed`。 |
| `rawResponse` | AI 原始回答。 |
| `referenceUrls` | 引用 URL 清單。 |
| `references` | 引用資料，包含 url 與 title。 |
| `error` | 錯誤資訊。 |
| `runAt` | 執行時間。 |

目前此 API 可支援 MVP 的同步跑題測試。正式架構中，應由 worker 呼叫此 API，不建議由前端或 `geo-analysis` route 直接同步等待跑題結果。

### 2.10 保存跑題結果

`geo-analysis` 若要做報表計算，必須保存每次跑題的原始結果與標準化後資料。

目前 `geo-analysis` schema 裡的 `geo_external_run_reference` 比較像保存外部任務參照，尚不足以支援完整報表計算。

建議補充資料表：

| 建議資料表 | 用途 |
| --- | --- |
| `geo_run_request` | 保存一次 worker 呼叫 `geo-tracking` 的 request。 |
| `geo_run_result` | 保存每個 query 的 raw answer、provider、model、status、error、run time。 |
| `geo_run_result_reference` | 保存 answer references、citation URL、title、domain、position。 |
| `geo_run_result_entity_mention` | 保存 answer 中提及的品牌、競品、alias、mention count 與位置。 |
| `geo_run_result_metric` | 保存單次 run 計算出的 visibility、mentions、citations、sentiment 等結果。 |

如果 raw response 體積很大，也可以只在 PostgreSQL 保存 metadata 與 object storage path，實際 raw response 放在 GCS 或其他物件儲存。不過 MVP 階段可以先存在 PostgreSQL，以降低系統複雜度。

### 2.11 結果分析與報表計算

保存 raw answer 後，`geo-analysis` 應進行分析與指標計算。

可能的分析項目：

| 分析項目 | 說明 |
| --- | --- |
| Mention extraction | 判斷 answer 是否提及自己品牌、競品、產品或 alias。 |
| Citation extraction | 整理 AI answer 引用的 URL、domain、title 與來源。 |
| Used URL detection | 判斷引用是否包含客戶自己的網站 URL。 |
| Sentiment analysis | 判斷 answer 對品牌是正向、中性或負向。 |
| Topic aggregation | 依 topic 彙總各 query 的曝光、提及、引用與情緒。 |
| Platform aggregation | 比較 Gemini、GPT、Claude 等不同 provider / model 的表現。 |

可能的報表指標：

| 指標 | 說明 |
| --- | --- |
| Visibility | 品牌是否出現在 AI answer 中，以及出現程度。 |
| SOV | 同一批 query 中，自己品牌與競品被提及的比例。 |
| Mentions | 品牌、競品、產品或 alias 被提及次數。 |
| Citations | AI answer 引用了哪些 URL 或 domain。 |
| Used URL Share | 自己網站 URL 在全部引用 URL 中的比例。 |
| Sentiment | 品牌在 AI answer 中的正向、中性、負向分布。 |
| Topic Performance | 不同 topic 的表現差異。 |
| Query Performance | 不同 query 的表現差異。 |

目前這些計算規則與儲存表尚未正式實作。`geo-analysis-schema.md` 也明確將 raw response、mention、citation、sentiment、visibility、SOV、position metrics 視為 Phase 1 尚未包含的內容。

## 3. 目前 API 與資料表支援度評估

### 3.1 目前已足夠支援的部分

| 範圍 | 評估 |
| --- | --- |
| Project / Market 規劃 | `geo_project`、`geo_market` 可支援。 |
| 品牌 / 競品 / 別名設定 | `geo_entity`、`geo_entity_alias` 可支援基本情境。 |
| Topic / Query / Keyword | `geo_topic`、`geo_query`、`geo_query_keyword` 可支援正式 query 管理。 |
| Platform / Schedule | `geo_ai_platform`、`geo_query_platform`、`geo_query_schedule` 可支援初版排程設定。 |
| Job 狀態管理 | `geo_query_run_job` 可作為跑題任務主表。 |
| Query Research | `geo-tracking` 已有 API，但 `geo-analysis` 尚未保存結果。 |
| Query Generation | `geo-tracking` 已有 API，但 `geo-analysis` 尚未保存 draft 與 shortlist。 |
| Gemini 跑題 | `geo-tracking` 已可透過 Gemini provider 取得 answer 與 references。 |

### 3.2 目前不足以支援正式 workflow 的部分

| 範圍 | 缺口 |
| --- | --- |
| PostgreSQL persistence | `geo-analysis` 目前仍偏 Phase 1 in-memory stub，尚未完成正式 repository 與 migration。 |
| Query Research persistence | 尚未有 research run / result 表。 |
| Query Generation persistence | 尚未有 generation run / query draft / shortlist 表。 |
| Queue / Worker | 尚未有 publisher、queue adapter、scheduler、worker 實作。 |
| Result persistence | 尚未有 raw answer、references、mentions、metrics 等結果表。 |
| Callback / ingestion | 尚未有正式結果回寫流程。 |
| Report calculation | 尚未有 visibility、SOV、citation、sentiment 等演算法與儲存策略。 |
| Provider operations | 尚未有 quota、retry、timeout、cost、token usage、credential 管理。 |
| Observability | 尚未有完整 run log、provider error taxonomy、worker metrics 與 tracing。 |

## 4. 建議後端實作順序

建議不要一次實作完整報表，應先把資料流打通，再補分析計算。

### Step 1：完成 geo-analysis 基礎 persistence

- 建立 PostgreSQL migrations。
- 實作 project、market、entity、alias、topic、query、platform、schedule 的 repository。
- 將目前 in-memory API route 改接 application use case 與 repository。

### Step 2：補 Query Research / Generation 保存能力

- 新增 `geo_query_research_run` 與 result 表。
- 新增 `geo_query_generation_run`、`geo_query_draft` 與 shortlist 表。
- 由 `geo-analysis` 呼叫 `geo-tracking`，並保存輸入與輸出。
- 使用者接受 draft 後，正式建立 `geo_query`。

### Step 3：完成 job 建立與 dedupe

- 手動 run 或 schedule due 時建立 `geo_query_run_job`。
- 統一 dedupe key 產生規則。
- 補 job 狀態轉換 use case。

### Step 4：實作 queue publisher 與 worker

- 先定義 publisher interface。
- 實作 queue backend adapter。
- 實作 scheduler。
- 實作 worker 消費 message。
- worker 呼叫 `geo-tracking /run-requests`。
- 補 retry、dead-letter 與 lease。

### Step 5：保存跑題結果

- 新增 run request / run result / reference 表。
- 保存 `rawResponse`、`references`、`provider`、`model`、`status`、`error`。
- 將 job 狀態更新為 `succeeded` 或 `failed`。

### Step 6：實作分析 pipeline

- 實作 mention extraction。
- 實作 citation normalization。
- 實作 used URL detection。
- 實作 sentiment analysis。
- 實作單次 run metrics。

### Step 7：實作報表計算與查詢 API

- 建立 metric snapshot 或 aggregate 表。
- 提供 Overview、Visibility、Competitors、Citations、Sentiments、Runs 等報表查詢 API。
- 支援依 project、topic、query、provider、model、時間範圍查詢。

## 5. 可能缺少的程式清單

以下是目前從完整 workflow 反推可能缺少的後端程式：

| 類別 | 缺少項目 |
| --- | --- |
| Persistence | `geo-analysis` PostgreSQL migrations、repositories、transaction handling。 |
| Application use cases | Project / Entity / Topic / Query / Schedule / Job 的正式 use case。 |
| Query Research integration | 呼叫 `geo-tracking /query-research` 並保存結果的 use case。 |
| Query Generation integration | 呼叫 `geo-tracking /query-generation` 並保存 draft / shortlist 的 use case。 |
| Queue abstraction | Publisher interface、message DTO、queue backend adapter。 |
| Worker | Scheduler、dispatcher、worker consumer、lease、retry、dead-letter。 |
| Tracking client | `geo-analysis` 對 `geo-tracking` 的 HTTP client、timeout、retry、error mapping。 |
| Result ingestion | 保存 run result、references、raw response、provider metadata 的 use case。 |
| Analysis pipeline | Mention extraction、citation extraction、sentiment analysis、metric calculation。 |
| Report API | Visibility、SOV、mentions、citations、sentiment、topic performance、run history 查詢 API。 |
| Provider operations | Credential config、quota control、cost tracking、token usage、provider error taxonomy。 |
| Observability | Worker logs、request tracing、job audit trail、provider latency metrics、failure dashboard。 |
| Tests | Domain state tests、repository tests、worker integration tests、tracking client tests、metric calculation tests。 |

## 6. 結論

目前架構方向是成立的：

- `geo-analysis` 作為 GEO 主系統，負責設定、job、資料保存、分析與報表。
- `geo-tracking` 作為跑題引擎，負責 Query Research、Query Generation 與實際 AI provider 呼叫。

但目前完整 workflow 尚未打通。最大的缺口不在前端，而是在後端資料管線：

```text
job 建立
→ queue 派送
→ worker 呼叫 geo-tracking
→ 結果保存
→ raw answer 分析
→ metric 計算
→ report API
```

若以 MVP 為目標，建議先完成「query 設定 → 建立 job → worker 跑 Gemini → 保存 raw result → 顯示 run history」這條最小閉環。等資料穩定進入 `geo-analysis` 後，再逐步補 visibility、SOV、citations、sentiment 與報表聚合。
