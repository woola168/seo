# GEO Queue / Worker 與基礎設定資料表規劃

本文件僅作為 Phase 1 規劃用途，尚未代表已實作的 migration 或正式資料庫契約。

Phase 1 邊界：

- 本模組負責 GEO 基礎設定、前端 CRUD、Query 管理、週期排程、Queue / Worker orchestration、外部跑題模組回報狀態、run raw result 與 references 保存。
- 本模組不負責實際打 AI API、不解析 mention / citation / sentiment、不計算 Visibility / SOV / Position 等 GEO 指標。
- Queue 工具尚未決定，程式與資料表命名需保持中性，不綁死 GCP Pub/Sub、RabbitMQ、NATS 或其他 broker。

規劃依據：

- `20260617開會簡報.pdf` 的 Phase 1 MVP 功能。
- `docs/geo-analysis-requirements.md` 的需求整理。
- 根目錄 `AGENTS.md` 與 `references/younilab-kmindhub-main` 的 bounded context 分層參考。

## 架構摘要

GEO 需獨立成一個 bounded context，不混入既有 `access-control` 或 `resource-catalog`。

建議未來實作目錄：

```text
apps/geo-analysis-api
packages/younilab-seo/src/younilab_seo/geo_analysis/domain
packages/younilab-seo/src/younilab_seo/geo_analysis/application
packages/younilab-seo/src/younilab_seo/geo_analysis/infrastructure
```

依賴方向：

```text
geo-analysis-api
→ younilab_seo.geo_analysis.application
→ younilab_seo.geo_analysis.domain

younilab_seo.geo_analysis.infrastructure
→ younilab_seo.geo_analysis.application
→ younilab_seo.geo_analysis.domain
```

Queue 抽象：

```text
Application use case
→ MessagePublisher port
→ RabbitMqMessagePublisher infrastructure adapter
```

第三批已加入 RabbitMQ publisher adapter，dispatch API 會依 provider 發布到不同 queue。第四批已加入 Gemini worker skeleton。第五批加入 run result storage；result parser 與 metrics pipeline 仍是後續批次。

目前 queue 命名：

- `geo.query-runs.gemini`
- `geo.query-runs.google_aio`
- `geo.query-runs.{provider}`

## 主要資料流

```text
前端 CRUD
→ geo_project / geo_entity / geo_topic / geo_query / geo_query_schedule
→ scheduler 產生 geo_query_run_job
→ dispatch use case 透過 MessagePublisher 發布 message
→ geo_message_dispatch_log 記錄派發狀態
→ 外部跑題模組接收 message 並執行
→ 外部 callback 回報 accepted / running / succeeded / failed
→ geo_external_run_reference 保存外部 run reference
→ geo_run_result / geo_run_result_reference 保存 raw answer 與 references
```

## 主要關聯

```mermaid
erDiagram
    customer ..o{ geo_project : owns
    seo_task ..o{ geo_project : optional_source

    geo_project ||--o{ geo_market : configures
    geo_project ||--o{ geo_entity : tracks
    geo_entity ||--o{ geo_entity_alias : has
    geo_project ||--o{ geo_topic : groups
    geo_topic ||--o{ geo_query : contains
    geo_query ||--o{ geo_query_keyword : has
    geo_query ||--o{ geo_query_platform : tracks
    geo_ai_platform ||--o{ geo_query_platform : selected
    geo_query ||--o{ geo_query_schedule : schedules

    geo_query_schedule ||--o{ geo_query_run_job : creates
    geo_query_run_job ||--o{ geo_message_dispatch_log : dispatches
    geo_query_run_job ||--o{ geo_worker_lease : leases
    geo_query_run_job ||--o{ geo_job_dispatch_event : audits
    geo_query_run_job ||--o{ geo_external_run_reference : references
    geo_query_run_job ||--o{ geo_run_request : runs
    geo_run_request ||--o{ geo_run_result : contains
    geo_run_result ||--o{ geo_run_result_reference : cites
```

## 共用資料規則

- `id`：所有新增表預設使用 `uuid` primary key。
- 時間欄位：使用 `timestamptz`。
- 狀態與類型：Phase 1 先使用 `varchar`，避免過早綁死 PostgreSQL enum。
- JSON metadata：使用 `jsonb`。
- `customer_id`：沿用既有 `customer.id`，代表客戶。
- `seo_task_id`：可選，若 GEO 分析要掛在既有 SEO 任務底下才填。
- API response JSON 欄位使用 `camelCase`；Python 與資料庫內部維持 `snake_case`。

## 基礎設定資料表

### `geo_project`

GEO 分析專案。每個客戶可有多個 GEO project。

| 欄位 | 型態 | 必填 | 關聯 / 約束 | 說明 |
|---|---|---:|---|---|
| `id` | `uuid` | 是 | PK | GEO project ID |
| `customer_id` | `uuid` | 是 |  | 所屬客戶 |
| `seo_task_id` | `uuid` | 否 |  | 若掛在既有 SEO 任務底下則填 |
| `name` | `varchar(200)` | 是 |  | 專案名稱 |
| `default_region` | `varchar(16)` | 是 | default `'TW'` | 預設地區，例如 `TW`、`US` |
| `default_language` | `varchar(16)` | 是 | default `'zh-TW'` | 預設語言 |
| `status` | `varchar(32)` | 是 |  | `active`、`paused`、`archived` |
| `daily_run_budget` | `integer` | 是 | default `0` | 每日最多 query job 數；`0` 代表未設定 |
| `daily_cost_budget` | `numeric(12,6)` | 否 |  | 每日 API 預算上限，僅作規劃或外部回填參考 |
| `created_at` | `timestamptz` | 是 |  | 建立時間 |
| `updated_at` | `timestamptz` | 是 |  | 更新時間 |
| `archived_at` | `timestamptz` | 否 |  | 封存時間 |

建議索引：

```sql
CREATE INDEX ix_geo_project_customer_id ON geo_project (customer_id);
CREATE INDEX ix_geo_project_status ON geo_project (status);
```

### `geo_market`

專案可追蹤的市場設定，例如台灣、美國。

| 欄位 | 型態 | 必填 | 關聯 / 約束 | 說明 |
|---|---|---:|---|---|
| `id` | `uuid` | 是 | PK | 市場設定 ID |
| `project_id` | `uuid` | 是 | FK → `geo_project.id` | 所屬專案 |
| `region` | `varchar(16)` | 是 |  | `TW`、`US` |
| `language` | `varchar(16)` | 是 |  | `zh-TW`、`en-US` |
| `market_name` | `varchar(100)` | 是 |  | 顯示名稱 |
| `prompt_locale_hint` | `text` | 是 | default `''` | 給外部跑題模組的地區語境 |
| `serp_gl` | `varchar(16)` | 否 |  | SERP API `gl` 參數參考 |
| `serp_hl` | `varchar(16)` | 否 |  | SERP API `hl` 參數參考 |
| `serp_location` | `varchar(200)` | 否 |  | SERP API location 參數參考 |
| `status` | `varchar(32)` | 是 |  | `active`、`paused` |
| `created_at` | `timestamptz` | 是 |  | 建立時間 |
| `updated_at` | `timestamptz` | 是 |  | 更新時間 |

約束：

```sql
UNIQUE (project_id, region, language)
```

### `geo_entity`

被追蹤的品牌、競品或其他實體。

| 欄位 | 型態 | 必填 | 關聯 / 約束 | 說明 |
|---|---|---:|---|---|
| `id` | `uuid` | 是 | PK | Entity ID |
| `project_id` | `uuid` | 是 | FK → `geo_project.id` | 所屬專案 |
| `entity_type` | `varchar(32)` | 是 |  | `primary_brand`、`competitor`、`other` |
| `name` | `varchar(200)` | 是 |  | 品牌或競品名稱 |
| `website_url` | `text` | 否 |  | 官方網站 |
| `description` | `text` | 是 | default `''` | 補充描述 |
| `status` | `varchar(32)` | 是 |  | `active`、`paused`、`archived` |
| `created_at` | `timestamptz` | 是 |  | 建立時間 |
| `updated_at` | `timestamptz` | 是 |  | 更新時間 |

約束：

```sql
UNIQUE (project_id, entity_type, name)
```

### `geo_entity_alias`

品牌或競品別名，供外部跑題 / 解析模組參考。

| 欄位 | 型態 | 必填 | 關聯 / 約束 | 說明 |
|---|---|---:|---|---|
| `id` | `uuid` | 是 | PK | Alias ID |
| `entity_id` | `uuid` | 是 | FK → `geo_entity.id` | 所屬 entity |
| `alias` | `varchar(200)` | 是 |  | 別名、英文名、縮寫 |
| `match_type` | `varchar(32)` | 是 | default `'exact'` | `exact`、`case_insensitive`、`contains` |
| `created_at` | `timestamptz` | 是 |  | 建立時間 |

約束：

```sql
UNIQUE (entity_id, alias)
```

### `geo_topic`

Query 分組維度。

| 欄位 | 型態 | 必填 | 關聯 / 約束 | 說明 |
|---|---|---:|---|---|
| `id` | `uuid` | 是 | PK | Topic ID |
| `project_id` | `uuid` | 是 | FK → `geo_project.id` | 所屬專案 |
| `name` | `varchar(200)` | 是 |  | Topic 名稱 |
| `description` | `text` | 是 | default `''` | 說明 |
| `status` | `varchar(32)` | 是 |  | `active`、`archived` |
| `created_at` | `timestamptz` | 是 |  | 建立時間 |
| `updated_at` | `timestamptz` | 是 |  | 更新時間 |

約束：

```sql
UNIQUE (project_id, name)
```

### `geo_query`

要定期交給外部跑題模組的自然語言問題。

| 欄位 | 型態 | 必填 | 關聯 / 約束 | 說明 |
|---|---|---:|---|---|
| `id` | `uuid` | 是 | PK | Query ID |
| `project_id` | `uuid` | 是 | FK → `geo_project.id` | 所屬專案 |
| `topic_id` | `uuid` | 否 | FK → `geo_topic.id` | 所屬 Topic |
| `query_text` | `text` | 是 |  | 問句內容 |
| `region` | `varchar(16)` | 是 |  | `TW`、`US` |
| `language` | `varchar(16)` | 是 |  | `zh-TW`、`en-US` |
| `market_type` | `varchar(32)` | 是 | default `'b2b_procurement'`；`b2c` / `b2b_procurement` | 使用者選擇的市場語境，會傳給 GEO Tracking runner |
| `intent` | `varchar(32)` | 否 |  | `navigational`、`informational`、`commercial`、`transactional` |
| `buyer_stage` | `varchar(32)` | 否 |  | B2B 場景，如 `supplier_evaluation`、`comparison`、`alternative` |
| `is_branded` | `boolean` | 是 | default `false` | 是否品牌字 query |
| `priority` | `varchar(32)` | 是 | default `'normal'` | `high`、`normal`、`low` |
| `status` | `varchar(32)` | 是 |  | `active`、`paused`、`archived` |
| `metadata` | `jsonb` | 是 | default `'{}'::jsonb` | 自訂 metadata |
| `created_at` | `timestamptz` | 是 |  | 建立時間 |
| `updated_at` | `timestamptz` | 是 |  | 更新時間 |
| `archived_at` | `timestamptz` | 否 |  | 封存時間 |

建議索引：

```sql
CREATE INDEX ix_geo_query_project_status ON geo_query (project_id, status);
CREATE INDEX ix_geo_query_topic_id ON geo_query (topic_id);
CREATE INDEX ix_geo_query_region_language ON geo_query (region, language);
```

### `geo_query_keyword`

Query Research 輸入與生成 query 的關鍵字來源。

| 欄位 | 型態 | 必填 | 關聯 / 約束 | 說明 |
|---|---|---:|---|---|
| `id` | `uuid` | 是 | PK | Keyword ID |
| `query_id` | `uuid` | 是 | FK → `geo_query.id` | 所屬 Query |
| `keyword` | `varchar(200)` | 是 |  | 原始關鍵字 |
| `search_volume` | `integer` | 否 |  | Google Ads / Keyword Planner 搜尋量 |
| `region` | `varchar(16)` | 是 |  | 搜尋量地區 |
| `language` | `varchar(16)` | 是 |  | 搜尋量語言 |
| `source` | `varchar(64)` | 是 | default `'manual'` | `manual`、`google_ads`、`gsc` |
| `metadata` | `jsonb` | 是 | default `'{}'::jsonb` | 原始資料 |
| `created_at` | `timestamptz` | 是 |  | 建立時間 |

### `geo_ai_platform`

可選的 AI / SERP 平台設定。僅保存平台設定，不負責實際 API 呼叫。

| 欄位 | 型態 | 必填 | 關聯 / 約束 | 說明 |
|---|---|---:|---|---|
| `id` | `uuid` | 是 | PK | Platform ID |
| `code` | `varchar(64)` | 是 | Unique | `openai`、`gemini`、`claude`、`perplexity`、`google_aio` |
| `display_name` | `varchar(100)` | 是 |  | 顯示名稱 |
| `provider_type` | `varchar(32)` | 是 |  | `llm_api`、`serp_api` |
| `default_model` | `varchar(100)` | 否 |  | 預設模型 |
| `supports_citations` | `boolean` | 是 | default `false` | 是否支援引用 |
| `supports_grounding` | `boolean` | 是 | default `false` | 是否支援搜尋 grounding |
| `status` | `varchar(32)` | 是 |  | `active`、`paused` |
| `created_at` | `timestamptz` | 是 |  | 建立時間 |
| `updated_at` | `timestamptz` | 是 |  | 更新時間 |

### `geo_query_platform`

Query 要派發到哪些平台。

| 欄位 | 型態 | 必填 | 關聯 / 約束 | 說明 |
|---|---|---:|---|---|
| `id` | `uuid` | 是 | PK | Query-platform ID |
| `query_id` | `uuid` | 是 | FK → `geo_query.id` | 所屬 Query |
| `platform_id` | `uuid` | 是 | FK → `geo_ai_platform.id` | 追蹤平台 |
| `model` | `varchar(100)` | 否 |  | 指定模型；空值用平台預設 |
| `status` | `varchar(32)` | 是 |  | `active`、`paused` |
| `created_at` | `timestamptz` | 是 |  | 建立時間 |
| `updated_at` | `timestamptz` | 是 |  | 更新時間 |

約束：

```sql
UNIQUE (query_id, platform_id)
```

## Queue / Worker Orchestration 資料表

### `geo_query_schedule`

保存 query / platform 的週期性排程規則。

| 欄位 | 型態 | 必填 | 關聯 / 約束 | 說明 |
|---|---|---:|---|---|
| `id` | `uuid` | 是 | PK | Schedule ID |
| `query_id` | `uuid` | 是 | FK → `geo_query.id` | 要排程的 Query |
| `platform_id` | `uuid` | 是 | FK → `geo_ai_platform.id` | 要派發的平台 |
| `frequency` | `varchar(32)` | 是 |  | `daily`、`weekly`、`manual` |
| `priority` | `varchar(32)` | 是 | default `'normal'` | `high`、`normal`、`low` |
| `timezone` | `varchar(64)` | 是 | default `'Asia/Taipei'` | 排程時區 |
| `next_run_at` | `timestamptz` | 否 |  | 下次應產生 job 的時間 |
| `last_scheduled_at` | `timestamptz` | 否 |  | 上次產生 job 的時間 |
| `status` | `varchar(32)` | 是 |  | `active`、`paused`、`archived` |
| `created_at` | `timestamptz` | 是 |  | 建立時間 |
| `updated_at` | `timestamptz` | 是 |  | 更新時間 |

約束：

```sql
UNIQUE (query_id, platform_id)
```

### `geo_query_run_job`

應用層 job 狀態來源。Queue 只負責派發，job 狀態以此表為準。

| 欄位 | 型態 | 必填 | 關聯 / 約束 | 說明 |
|---|---|---:|---|---|
| `id` | `uuid` | 是 | PK | Job ID |
| `project_id` | `uuid` | 是 | FK → `geo_project.id` | 所屬專案 |
| `query_id` | `uuid` | 是 | FK → `geo_query.id` | 要派發的 Query |
| `platform_id` | `uuid` | 是 | FK → `geo_ai_platform.id` | 要派發的平台 |
| `schedule_id` | `uuid` | 否 | FK → `geo_query_schedule.id` | 來源 schedule |
| `job_type` | `varchar(32)` | 是 | default `'scheduled_run'` | `scheduled_run`、`manual_run`、`report_backfill` |
| `priority` | `varchar(32)` | 是 | default `'normal'` | `high`、`normal`、`low` |
| `scheduled_for` | `timestamptz` | 是 |  | 預計派發時間 |
| `status` | `varchar(32)` | 是 |  | `pending`、`publishing`、`published`、`running_external`、`succeeded`、`failed`、`delayed`、`cancelled` |
| `attempt_count` | `integer` | 是 | default `0` | 已嘗試派發次數 |
| `max_attempts` | `integer` | 是 | default `3` | 最大派發重試次數 |
| `next_retry_at` | `timestamptz` | 否 |  | 下次重試時間 |
| `dedupe_key` | `varchar(200)` | 是 | Unique | 避免同一 query / platform / time window 重複派發 |
| `dispatch_backend` | `varchar(32)` | 否 |  | `gcp_pubsub`、`rabbitmq`、`nats`、`database` 等 |
| `dispatch_message_id` | `varchar(200)` | 否 |  | broker 回傳 message ID |
| `external_run_id` | `varchar(200)` | 否 |  | 外部跑題模組 run ID |
| `last_error_code` | `varchar(100)` | 否 |  | 最後錯誤代碼 |
| `last_error_message` | `text` | 否 |  | 最後錯誤訊息 |
| `created_at` | `timestamptz` | 是 |  | 建立時間 |
| `updated_at` | `timestamptz` | 是 |  | 更新時間 |

建議索引：

```sql
CREATE INDEX ix_geo_query_run_job_pickup
ON geo_query_run_job (status, scheduled_for, priority);

CREATE INDEX ix_geo_query_run_job_query_platform
ON geo_query_run_job (query_id, platform_id);
```

### `geo_message_dispatch_log`

保存 message 派發紀錄。命名保持中性，不綁定特定 queue 工具。

| 欄位 | 型態 | 必填 | 關聯 / 約束 | 說明 |
|---|---|---:|---|---|
| `id` | `uuid` | 是 | PK | Dispatch log ID |
| `job_id` | `uuid` | 是 | FK → `geo_query_run_job.id` | 對應 job |
| `message_backend` | `varchar(32)` | 是 |  | `gcp_pubsub`、`rabbitmq`、`nats`、`database` |
| `destination` | `varchar(200)` | 是 |  | topic / queue / subject / table |
| `message_id` | `varchar(200)` | 否 |  | broker 回傳 message ID |
| `payload` | `jsonb` | 是 |  | 派發 payload |
| `publish_status` | `varchar(32)` | 是 |  | `pending`、`published`、`failed` |
| `published_at` | `timestamptz` | 否 |  | 成功派發時間 |
| `error_message` | `text` | 否 |  | 錯誤訊息 |
| `created_at` | `timestamptz` | 是 |  | 建立時間 |

### `geo_worker_lease`

若本服務內有 worker 掃表或補償派發，用 lease 避免重複處理同一 job。

| 欄位 | 型態 | 必填 | 關聯 / 約束 | 說明 |
|---|---|---:|---|---|
| `id` | `uuid` | 是 | PK | Lease ID |
| `job_id` | `uuid` | 是 | FK → `geo_query_run_job.id` | 對應 job |
| `worker_id` | `varchar(100)` | 是 |  | Worker ID |
| `leased_at` | `timestamptz` | 是 |  | 取得 lease 時間 |
| `expires_at` | `timestamptz` | 是 |  | lease 到期時間 |
| `released_at` | `timestamptz` | 否 |  | 釋放時間 |
| `release_reason` | `varchar(64)` | 否 |  | 釋放原因 |

### `geo_job_dispatch_event`

保存 orchestration audit trail。

| 欄位 | 型態 | 必填 | 關聯 / 約束 | 說明 |
|---|---|---:|---|---|
| `id` | `uuid` | 是 | PK | Event ID |
| `job_id` | `uuid` | 是 | FK → `geo_query_run_job.id` | 對應 job |
| `event_type` | `varchar(64)` | 是 |  | `created`、`publish_started`、`published`、`publish_failed`、`accepted`、`callback_succeeded`、`callback_failed`、`retry_scheduled`、`cancelled` |
| `occurred_at` | `timestamptz` | 是 |  | 發生時間 |
| `actor` | `varchar(100)` | 是 |  | `scheduler`、`api`、`worker`、`broker`、`external_runner` |
| `metadata` | `jsonb` | 是 | default `'{}'::jsonb` | 補充資訊 |

### `geo_external_run_reference`

保存外部跑題模組回傳的 reference，不保存跑題內容。

| 欄位 | 型態 | 必填 | 關聯 / 約束 | 說明 |
|---|---|---:|---|---|
| `id` | `uuid` | 是 | PK | Reference ID |
| `job_id` | `uuid` | 是 | FK → `geo_query_run_job.id` | 對應 job |
| `external_system` | `varchar(100)` | 是 |  | 外部跑題模組名稱 |
| `external_run_id` | `varchar(200)` | 是 |  | 外部 run ID |
| `external_status` | `varchar(64)` | 是 |  | `accepted`、`running`、`succeeded`、`failed` |
| `callback_received_at` | `timestamptz` | 否 |  | 收到 callback 的時間 |
| `result_location` | `text` | 否 |  | 外部結果 URI / reference；不保存內容 |
| `metadata` | `jsonb` | 是 | default `'{}'::jsonb` | 外部模組補充資訊 |
| `created_at` | `timestamptz` | 是 |  | 建立時間 |
| `updated_at` | `timestamptz` | 是 |  | 更新時間 |

### `geo_run_request`

保存 worker 對 `geo-tracking /run-requests` 的一次呼叫與整體狀態。

| 欄位 | 型態 | 必填 | 關聯 / 約束 | 說明 |
|---|---|---:|---|---|
| `id` | `uuid` | 是 | PK | Analysis 端 run request ID |
| `job_id` | `uuid` | 是 | FK → `geo_query_run_job.id` | 對應 job |
| `tracking_run_request_id` | `varchar(200)` | 是 |  | geo-tracking 回傳的 request id |
| `seo_task_id` | `uuid` | 是 |  | 呼叫 tracking 使用的 SEO task id |
| `provider` | `varchar(64)` | 是 |  | `gemini`、`openai` 等 |
| `timing` | `varchar(32)` | 是 |  | `run_now`、`next_cycle` |
| `status` | `varchar(32)` | 是 |  | `succeeded`、`failed` |
| `error_code` | `varchar(100)` | 否 |  | worker 或 tracking error code |
| `error_message` | `text` | 否 |  | worker 或 tracking error message |
| `request_payload` | `jsonb` | 是 | default `'{}'::jsonb` | 實際送往 `geo-tracking /run-requests` 的 JSON；worker 前置拒絕時保存拒絕 evidence |
| `created_at` | `timestamptz` | 是 |  | 建立時間 |
| `completed_at` | `timestamptz` | 否 |  | 完成時間 |

### `geo_run_result`

保存 geo-tracking 對單一 query 回傳的 raw answer。

| 欄位 | 型態 | 必填 | 關聯 / 約束 | 說明 |
|---|---|---:|---|---|
| `id` | `uuid` | 是 | PK | Analysis 端 result ID |
| `run_request_id` | `uuid` | 是 | FK → `geo_run_request.id` | 所屬 run request |
| `job_id` | `uuid` | 是 | FK → `geo_query_run_job.id` | 對應 job |
| `tracking_result_id` | `varchar(200)` | 是 |  | geo-tracking 回傳的 result id |
| `query_id` | `uuid` | 是 | FK → `geo_query.id` | 對應 query |
| `provider` | `varchar(64)` | 是 |  | provider |
| `surface` | `varchar(100)` | 是 |  | provider surface |
| `model` | `varchar(100)` | 是 |  | provider model |
| `region` | `varchar(16)` | 是 |  | query region |
| `language` | `varchar(16)` | 是 |  | query language |
| `status` | `varchar(32)` | 是 |  | `completed`、`failed` |
| `raw_response` | `text` | 是 | default `''` | AI 原始回答 |
| `error` | `text` | 否 |  | 單筆 result error |
| `run_at` | `timestamptz` | 是 |  | tracking 執行時間 |
| `created_at` | `timestamptz` | 是 |  | 保存時間 |

### `geo_run_result_reference`

保存 provider 回傳的 references/citations raw data；這不是 metrics pipeline 的 citation 計算結果。

| 欄位 | 型態 | 必填 | 關聯 / 約束 | 說明 |
|---|---|---:|---|---|
| `id` | `uuid` | 是 | PK | Reference ID |
| `run_result_id` | `uuid` | 是 | FK → `geo_run_result.id` | 所屬 raw result |
| `url` | `text` | 是 |  | Reference URL |
| `title` | `text` | 否 |  | Provider 回傳 title |
| `domain` | `varchar(255)` | 否 |  | 從 URL 解析出的 domain |
| `position` | `integer` | 是 |  | Result 內 reference 順序 |

## Message Publisher Port

Application 層只定義抽象介面；RabbitMQ 實作放在 infrastructure adapter。

```python
class MessagePublisher(Protocol):
    """Publishes GEO query run jobs through the configured message broker."""

    async def publish(self, message: QueryRunJobMessage) -> PublishResult:
        ...
```

目前已實作：

```text
RabbitMqMessagePublisher
```

其他 broker adapter 如 GCP Pub/Sub、NATS 或 database queue 可在未來依部署決策新增。

## Message Payload

派發給外部跑題模組的最小 payload：

```json
{
  "jobId": "uuid",
  "projectId": "uuid",
  "queryId": "uuid",
  "queryText": "string",
  "platform": "openai | gemini | claude | perplexity | google_aio",
  "model": "string or null",
  "region": "TW | US",
  "language": "zh-TW | en-US",
  "scheduledFor": "datetime",
  "callbackUrl": "string"
}
```

外部跑題模組 callback 的最小 payload：

```json
{
  "jobId": "uuid",
  "externalRunId": "string",
  "status": "accepted | running | succeeded | failed",
  "resultLocation": "string or null",
  "errorCode": "string or null",
  "errorMessage": "string or null"
}
```

## 前端可用 API 草案

以下 endpoint 供後台前端管理基礎設定與 job 狀態。實際路徑可在 API 設計階段微調，但需維持 REST、lowercase plural nouns、kebab-case segments。

### GEO Project

```text
GET    /api/geo/projects
POST   /api/geo/projects
GET    /api/geo/projects/{projectId}
PATCH  /api/geo/projects/{projectId}
DELETE /api/geo/projects/{projectId}
```

用途：

- 建立與管理 GEO workspace / project。
- 前端可依 `customerId` 篩選。

### Markets

```text
GET    /api/geo/projects/{projectId}/markets
POST   /api/geo/projects/{projectId}/markets
PATCH  /api/geo/markets/{marketId}
DELETE /api/geo/markets/{marketId}
```

### Entities and Aliases

```text
GET    /api/geo/projects/{projectId}/entities
POST   /api/geo/projects/{projectId}/entities
GET    /api/geo/entities/{entityId}
PATCH  /api/geo/entities/{entityId}
DELETE /api/geo/entities/{entityId}

GET    /api/geo/entities/{entityId}/aliases
POST   /api/geo/entities/{entityId}/aliases
PATCH  /api/geo/entity-aliases/{aliasId}
DELETE /api/geo/entity-aliases/{aliasId}
```

用途：

- 管理 primary brand、competitor、alias。
- 不在本模組做 mention 解析。

### Topics and Queries

```text
GET    /api/geo/projects/{projectId}/topics
POST   /api/geo/projects/{projectId}/topics
PATCH  /api/geo/topics/{topicId}
DELETE /api/geo/topics/{topicId}

GET    /api/geo/projects/{projectId}/queries
POST   /api/geo/projects/{projectId}/queries
GET    /api/geo/queries/{queryId}
PATCH  /api/geo/queries/{queryId}
DELETE /api/geo/queries/{queryId}
```

用途：

- 管理前端 Query / Topic。
- Query 可帶 region、language、marketType、intent、buyerStage、metadata。

### Query Platforms and Schedules

```text
GET    /api/geo/queries/{queryId}/platforms
PUT    /api/geo/queries/{queryId}/platforms

GET    /api/geo/queries/{queryId}/schedules
POST   /api/geo/queries/{queryId}/schedules
PATCH  /api/geo/schedules/{scheduleId}
DELETE /api/geo/schedules/{scheduleId}
```

用途：

- 設定 query 要派發的平台。
- 設定週期性排程與 priority。

### Jobs

```text
GET   /api/geo/projects/{projectId}/jobs
POST  /api/geo/queries/{queryId}/jobs
GET   /api/geo/jobs/{jobId}
POST  /api/geo/jobs/{jobId}/dispatch
POST  /api/geo/jobs/{jobId}/cancel
```

用途：

- 前端查看 pending / published / running_external / failed job。
- 手動建立一次性 job。
- 手動派發或取消 job。

### External Callback

```text
POST /api/geo/jobs/{jobId}/external-callbacks
```

用途：

- 外部跑題模組回報 `accepted`、`running`、`succeeded`、`failed`。
- 只更新 orchestration 狀態與 external reference。

## Application Boundary 後續實作備註

Phase 1 API 仍使用 in-memory store 作為前端串接 stub，因此 `cancel_job` 與 `receive_external_callback`
可暫時直接操作 domain entity。後續接 PostgreSQL repository、正式 worker 或 audit trail 時需調整：

- API route 應改呼叫 application use case，不長期直接 mutate domain entity。
- `receive_external_callback` 應透過 `ReceiveExternalRunCallback`，確保 `record_external_callback`
  與 external reference / audit event 不漏記。
- `cancel_job` 應新增 application use case，統一處理狀態轉換、儲存與事件紀錄。
- repository adapter 應負責 transaction boundary，確保 job 狀態與 dispatch / callback evidence 一致寫入。

## 不在本模組定義的資料

以下資料由外部跑題 / 分析模組擁有，不在本 schema 定義：

```text
AI raw response
AI normalized response
response mention
response citation
sentiment statement
Visibility / SOV / Position metrics
AI API token usage detail
AI API cost detail
content optimization recommendation
```

若前端需要顯示上述內容，應透過外部分析模組 API 或彙整 API 取得，不直接從本模組資料表讀取。

## 驗收情境

- 前端可 CRUD GEO project、market、entity、alias、topic、query、schedule。
- Query 可設定平台與排程。
- Scheduler 可根據 `geo_query_schedule.next_run_at` 建立 `geo_query_run_job`。
- 同一 query / platform / scheduled window 不會重複建立 job。
- Dispatch use case 可透過 `MessagePublisher` port 派發 message。
- Publisher adapter 未實作時，測試可使用 fake publisher 驗證 use case。
- 派發成功或失敗會寫入 `geo_message_dispatch_log` 與 `geo_job_dispatch_event`。
- 外部 callback 可更新 job 狀態與 `geo_external_run_reference`。
- 文件與未來程式碼不出現綁死特定 queue 工具的 table/class 命名。

## 假設與預設

- 實際跑題模組不由本 bounded context 實作。
- Queue 工具未決定前，只定義 `MessagePublisher` port 與中性 message dispatch 資料表。
- 正式環境若採 GCP，可新增 GCP Pub/Sub adapter；若採自有 VM，可新增 RabbitMQ 或 NATS adapter。
- `access-control` 不改 schema；GEO API 後續只透過既有 authorization 機制授權。
- `resource-catalog` 不改 schema；GEO 只透過 `customer_id` / `seo_task_id` reference 既有主資料。
- 共用抽象延後到後續重構，不在 Phase 1 先建立 shared queue framework。

