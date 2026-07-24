# 部署設定

## 環境檔

GitHub Actions 會依分支選用部署環境檔：

- `develop` 使用 `deploy/.env.develop`
- `main` 使用 `deploy/.env.prod`

遠端 PostgreSQL schema 與 seed 仍由人工執行；CI/CD 不會自動跑 DB migration。

## 對外 Port

Compose 將服務綁定在 `127.0.0.1`，可搭配 SSH tunnel 對外測試：

- Admin Portal: `http://127.0.0.1:18080`
- Access Control API: `http://127.0.0.1:18004`
- Resource Catalog API: `http://127.0.0.1:18001`
- GEO Analysis API: `http://127.0.0.1:18002`
- GEO Tracking API: `http://127.0.0.1:18003`
- RabbitMQ AMQP: `127.0.0.1:5672`
- RabbitMQ Management UI: `http://127.0.0.1:15672`

RabbitMQ dashboard 可用 SSH tunnel 查看：

```powershell
ssh -L 15672:127.0.0.1:15672 user@server
```

登入帳密使用 `RABBITMQ_DEFAULT_USER` 與 `RABBITMQ_DEFAULT_PASS`。

## Compose Env File Path

`DEPLOY_ENV_FILE` is consumed by `deploy/docker-compose.yml` `env_file` entries.
Use `.env.develop` or `.env.prod` because Docker Compose resolves the path from
the `deploy/` directory when running with `-f deploy/docker-compose.yml`.

## GEO Analysis

`GEO_ANALYSIS_DATABASE_URL` 指向 GEO Analysis PostgreSQL database。`geo_ai_platform` 資料目前仍由人工 seed，例如 Gemini、ChatGPT 等 platform。

KMindHub Insight workspace mapping 使用下列設定：

```env
KMINDHUB_INSIGHT_BASE_URL=http://kmindhub-insight-api:8000
KMINDHUB_INSIGHT_TIMEOUT_SECONDS=30
```

tenant 第一次使用後續 analysis extraction 前，需先透過 GEO Analysis API 手動綁定既有 KMindHub workspace，或明確呼叫 provision endpoint 建立 workspace。Worker 不會在首次執行時自動建立 workspace；若 mapping 缺失，後續 extraction pipeline 應 fail closed，不可使用 default workspace。

RabbitMQ publisher 設定：

```env
GEO_ANALYSIS_PUBLISHER_BACKEND=rabbitmq
GEO_ANALYSIS_RABBITMQ_URL=amqp://geo_worker:CHANGE_ME@rabbitmq:5672/
GEO_ANALYSIS_RABBITMQ_EXCHANGE=geo.query-runs
GEO_ANALYSIS_RABBITMQ_QUEUE_PREFIX=geo.query-runs
GEO_ANALYSIS_RABBITMQ_ROUTING_KEY_PREFIX=geo.query-runs
GEO_ANALYSIS_CALLBACK_BASE_URL=http://geo-analysis-api:8002
GEO_ANALYSIS_ACCESS_CONTROL_URL=http://access-control-api:8000
GEO_ANALYSIS_RESOURCE_CATALOG_URL=http://resource-catalog-api:8001
```

GEO Analysis API 會透過 Access Control `/api/me/capabilities` 取得目前使用者 `tenantId`，request 不需要也不允許自行指定 tenant。`customer_id` 是 reference-only 欄位，建立或更新 Project 時會透過 Resource Catalog 驗證 reference 屬於同一個 tenant。過渡期間仍接受舊版 request 的 `seoTaskId`，但會忽略該值，Scheduler 與 Worker 都不再使用它。

Queue 依 provider 拆分：

- `geo.query-runs.gemini`
- `geo.query-runs.openai`
- `geo.query-runs.perplexity`

## GEO Analysis Scheduler

`geo-analysis-scheduler` 是單一 instance 的常駐服務，每 60 秒檢查一次，並在每日 `03:00 Asia/Taipei` 依 active Project × active Query × active Platform 建立當日 job snapshot。任何非 active Platform 都不參與排程；既有 query-platform assignment 不影響 daily scheduler。它不回補歷史日期，正確性由 daily batch 與 scheduled job 的資料庫唯一索引保證。

```env
GEO_SCHEDULER_TIMEZONE=Asia/Taipei
GEO_SCHEDULER_DAILY_TIME=03:00
GEO_SCHEDULER_POLL_SECONDS=60
```

部署前需執行 expand migration `deploy/local/postgresql/015_geo_analysis_daily_scheduler.sql`，建立每日 batch、scheduled job 欄位與索引。此 migration 不再依賴 SEO Task。確認所有舊版 API 與 worker replicas 下線後，才手動執行 contract migration `016_geo_analysis_remove_seo_task_contract.sql`。Resource Catalog 與 GEO Analysis 使用不同 database，無法在 migration 內直接 join `seo_task`；執行 `016` 前必須先補齊 Project 的 `customer_id`，仍有缺漏時 migration 會中止且不會刪除 `seo_task_id`。

部署每日 Query／Platform 唯一執行限制時，不可讓舊版 Job writers 與 `020_geo_query_daily_run_uniqueness.sql` 的唯一索引同時運作。需先停止 Admin Portal 即時執行、GEO API create-job 流量與 scheduler，確認 writers 已停止後執行 migration，再部署新版 GEO API／scheduler；完成同日重複 create-job 回傳既有 Job、scheduler 不重複建立及 first-run pickup smoke test 後才恢復 writers，最後部署 Admin Portal。若維護期間無法完整停止 writers，不可執行 migration。

部署 provider request 稽核功能前，需先執行 `deploy/local/postgresql/018_provider_request_audit.sql`。`geo-tracking-api`、`geo-analysis-api` 與 GEO worker 會在呼叫 Gemini 或 SerpApi 前先寫入 `provider_request`；若 migration 尚未套用，provider request 會依 fail-closed 規則停止，不會在沒有稽核紀錄的情況下繼續呼叫。

部署 provider usage 與牌價成本估算前，需先執行 `deploy/local/postgresql/023_provider_request_usage_cost_estimate.sql`，再部署新版 Tracking API 與 GEO worker。此 migration 會擴充 `provider_request`、建立版本化費率表及成本 views；舊 Gemini request 的 usage 標記為 `unavailable`，其他 provider 標記為 `not_applicable`，不回填 token 或成本。

部署 deterministic entity mention detection 前，需先執行 `deploy/local/postgresql/022_geo_run_result_entity_detection.sql`，再部署新版 GEO API 與 worker。新分析會將 mention 寫入獨立 detection tables；既有、尚未建立 detection 的 run result 仍讀取 KMindHub legacy mention。回滾應用程式版本時可保留新增資料表，不需刪除 detection 資料。

Provider credential 只注入實際執行 Provider 的服務，不提供給 scheduler。缺少必要 credential 的 Platform 應維持非 active；以 Google AIO 為例，部署順序為注入 `SERPAPI_API_KEY`、執行 smoke test，再將 Platform 改為 active。

Provider 已執行但結果保存失敗時，Worker 只記錄 structured exception 並 ack message；Job 後續由 reconciliation 標記為 `execution_outcome_unknown`，不會重新呼叫 Provider 或送入 DLQ。DLQ 僅保留給 Provider 尚未開始前且超過 delivery 次數的 message。

## GEO Analysis Worker

`geo-analysis-worker-gemini` 只消費 Gemini queue：

```env
GEO_ANALYSIS_WORKER_PROVIDER=gemini
GEO_ANALYSIS_WORKER_QUEUE=geo.query-runs.gemini
GEO_ANALYSIS_WORKER_PREFETCH=1
GEO_TRACKING_BASE_URL=http://geo-tracking-api:8003
```

Scheduler Worker 對單次 geo-tracking run request 使用固定 210 秒 timeout，涵蓋最多三次、每次 60 秒的 Gemini API 呼叫與 backoff；不讀取 `GEO_TRACKING_TIMEOUT_SECONDS`。該環境設定仍供 `geo-analysis-api` 的互動式 planning request 使用。

`geo-analysis-worker-google-aio` 使用同一個 worker image，設定為：

```env
GEO_ANALYSIS_WORKER_PROVIDER=google_aio
GEO_ANALYSIS_WORKER_QUEUE=geo.query-runs.google_aio
```

`geo-tracking-api` 的部署環境必須注入 `SERPAPI_API_KEY`；此 key 不應寫入 repo。

### GEO Analysis Worker Result Storage

GEO Analysis provider worker 會把 RabbitMQ message 轉成 `geo-tracking-api` 的 `/api/v1/geo-tracking/run-requests` payload。Tracking completed 時會保存 `geo_run_request`、`geo_run_result`、`geo_run_result_reference`，並把 GEO job 標記為 `succeeded`；tracking failed、HTTP timeout、unsupported provider 時會保存失敗 evidence 並把 job 標記為 `failed`。

目前 raw response 存在 PostgreSQL `text` 欄位，references 存在 `geo_run_result_reference`。Worker 保存 raw result 後會用 KMindHub `geo_semantic_analysis` v4 產生 mention、position、positive / negative sentiment 與 semantic facts；references 則由獨立 citation normalization pipeline 處理。Dashboard report API 讀取這兩類 normalized facts 即時計算 visibility、mentions、SOV、average position 與 citation 指標。

## GEO Tracking

`geo-tracking-api` 與 GEO focused evidence repair 都使用 Google Vertex AI service account JSON。請放在 VM 上並透過 Compose volume 唯讀掛載到 geo-tracking API、geo-analysis API 與兩個 provider worker，不要提交到 source control。

```env
GCP_CREDENTIALS_FILE_HOST=/root/kmind/deploy/credentials/dev-gcp-key.json
GOOGLE_APPLICATION_CREDENTIALS=/app/config/gcp-key.json
```

Focused repair 預設沿用 `GEMINI_MODEL` / `GEMINI_THINKING_LEVEL`，也可獨立覆寫：

```env
GEO_EVIDENCE_REPAIR_MODEL=gemini-3.1-flash-lite
GEO_EVIDENCE_REPAIR_TEMPERATURE=0
GEO_EVIDENCE_REPAIR_THINKING_LEVEL=medium
GEO_EVIDENCE_REPAIR_TIMEOUT_SECONDS=60
```

Google AIO 使用 SerpApi，正式環境需設定 `SERPAPI_API_KEY`。

## 本機 PostgreSQL

```powershell
docker compose -f deploy/local/docker-compose.postgresql.yml up -d
```

本機 PostgreSQL：

- Access Control PostgreSQL: `localhost:5432/access_control`
- Resource Catalog PostgreSQL: `localhost:5433/resource_catalog`

## Access Control Tenant DB Patch

既有 Access Control PostgreSQL 若已套用舊 schema，需手動執行 tenant patch：

```powershell
psql "postgresql://USER:PASSWORD@HOST:PORT/DB_NAME" -f deploy/local/postgresql/006_access_control_tenant_patch.sql
```

這份 patch 會建立 `tenant` 表、seed `code='default'` 的 default tenant，並將既有 `user_account`、`role`、`department` 回填到 default tenant。第一批 tenant foundation 仍維持 `user_account.email` 全系統唯一；若資料庫已存在重複 email，patch 會在建立 global unique constraint 時失敗，需先人工清理。新環境可直接使用更新後的 `deploy/local/postgresql/001_access_control_schema.sql` 初始化。

## GEO分析-RD Admin 權限 Patch

既有 Access Control PostgreSQL 需為 system admin role 補上 Portal 的 RD 入口權限：

```powershell
psql "postgresql://USER:PASSWORD@HOST:PORT/DB_NAME" -f deploy/local/postgresql/017_access_control_geo_admin_access_patch.sql
```

此 patch 可重複執行，只會為 `is_system = true` 且名稱為 `admin` 的角色加入 `geo.admin.access`，不會修改其他角色。可於執行前後查詢確認：

```sql
SELECT id, name, permissions
FROM role
WHERE is_system = true AND lower(name) = 'admin';
```

## Resource Catalog Tenant DB Patch

第二批 tenant scope 需同時更新 Resource Catalog DB 與 Access Control DB 的 resource grants。既有遠端 DB 請依序手動執行：

```powershell
psql "postgresql://USER:PASSWORD@HOST:PORT/RESOURCE_CATALOG_DB" -f deploy/local/postgresql/007_resource_catalog_tenant_patch.sql
psql "postgresql://USER:PASSWORD@HOST:PORT/ACCESS_CONTROL_DB" -f deploy/local/postgresql/008_access_control_resource_grant_tenant_patch.sql
```

`007_resource_catalog_tenant_patch.sql` 會替 `customer` 與 `seo_task` 新增 `tenant_id`，既有資料回填 default tenant，並將 customer name unique 改為 `(tenant_id, name)`。

`008_access_control_resource_grant_tenant_patch.sql` 會替 `customer_access_grant` 與 `task_access_grant` 新增 `tenant_id`，依 user tenant 回填既有 grants，並將 unique constraint 改為 tenant-scoped。

新環境初始化已同步更新 `001_resource_catalog_schema.sql` 與 `001_access_control_schema.sql`；CI/CD 仍不會自動執行 DB migration。

## GEO Analysis 手動 DB Patch

遠端 PostgreSQL schema 與 seed 仍由人工執行，CI/CD 不會自動跑 migration。若環境已套用舊版 `004_geo_analysis_schema.sql`，升級 Query Planning 前需手動執行：

```powershell
psql "postgresql://USER:PASSWORD@HOST:PORT/DB_NAME" -f deploy/local/postgresql/005_geo_analysis_query_planning_patch.sql
psql "postgresql://USER:PASSWORD@HOST:PORT/DB_NAME" -f deploy/local/postgresql/009_geo_analysis_tenant_patch.sql
psql "postgresql://USER:PASSWORD@HOST:PORT/DB_NAME" -f deploy/local/postgresql/010_kmindhub_workspace_mapping_patch.sql
psql "postgresql://USER:PASSWORD@HOST:PORT/DB_NAME" -f deploy/local/postgresql/011_geo_analysis_kmindhub_extraction_patch.sql
psql "postgresql://USER:PASSWORD@HOST:PORT/DB_NAME" -f deploy/local/postgresql/014_geo_analysis_gemini_model_alignment.sql
```

這份 patch 會移除 `geo_project.customer_id` 的 `NOT NULL`，並建立 `geo_query_research_run`、`geo_query_generation_run`、`geo_query_draft`、`geo_query_draft_selection` 與必要 indexes。新環境可直接使用更新後的 `deploy/local/postgresql/004_geo_analysis_schema.sql` 初始化 schema。

`009_geo_analysis_tenant_patch.sql` 會替 `geo_project` 新增 `tenant_id`，既有資料回填 default tenant，並建立 tenant 查詢 index。建議先完成 Access Control tenant patch、Resource Catalog tenant patch，再執行 GEO Analysis tenant patch。

`010_kmindhub_workspace_mapping_patch.sql` 會建立 `tenant_kmindhub_workspace_mapping`，保存 tenant 到 KMindHub workspace 的 reference-only mapping。新環境可直接使用更新後的 `004_geo_analysis_schema.sql`。

`011_geo_analysis_kmindhub_extraction_patch.sql` 會建立 KMindHub extraction task mapping 與 GEO run result analysis / mention / statement / citation classification tables。完整串接流程與欄位定義請參考 `docs/integrations/geo-analysis-kmindhub-insight-extraction.md`。

`014_geo_analysis_gemini_model_alignment.sql` 只會將 `code='gemini'` 的
`default_model` 對齊為 `gemini-3.1-flash-lite`，可重複執行且不修改歷史 run result。
套用 Titan develop 前後應執行下列查詢，確認 DB snapshot 與 deployment 的
`GEMINI_MODEL` 一致：

```sql
SELECT code, default_model
FROM geo_ai_platform
WHERE code = 'gemini';
```

### Provider request 牌價成本估算

逐 request 與每日彙總可直接查詢：

```sql
SELECT id, use_case, request_kind, estimation_status,
       estimated_list_cost_usd
FROM provider_request_cost_estimate
ORDER BY started_at DESC;

SELECT *
FROM provider_request_daily_cost_estimate
ORDER BY usage_date DESC, provider_code, model;
```

`estimated_list_cost_usd` 只代表 USD 公開牌價估算，不扣免費額度、credits、合約折扣、稅與匯率，不能視為 GCP 正式帳單。`usage_unavailable`、`rate_missing`、`not_supported` 與 `billing_uncertain` 不會產生估算金額；明確 HTTP 4xx／5xx 失敗則顯示 `not_billable` 與零成本。

費率異動時只新增較晚 `effective_from` 的版本，不覆寫舊列。查詢 view 會依 request 的 `started_at`、model、region class、traffic type 與 meter 選取當時有效且最新的費率：

```sql
-- 以下 UUID、價格與生效日期僅為新增版本範例，執行前必須替換。
INSERT INTO provider_pricing_rate (
    id, platform_code, provider_code, model, provider_region_class,
    traffic_type, meter_code, unit_quantity, unit_price_usd,
    effective_from, source_url, source_checked_at
) VALUES (
    '00000000-0000-4000-8000-000000000000',
    'gemini', 'google_vertex_ai', 'gemini-3.1-flash-lite',
    'global', 'ON_DEMAND', 'input_token', 1000000, 0.30,
    '2027-01-01T00:00:00Z',
    'https://cloud.google.com/gemini-enterprise-agent-platform/generative-ai/pricing',
    '2026-12-31'
);
```
