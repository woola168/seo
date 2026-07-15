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

GEO Analysis API 會透過 Access Control `/api/me/capabilities` 取得目前使用者 `tenantId`，request 不需要也不允許自行指定 tenant。`customer_id` / `seo_task_id` 仍是 reference-only 欄位，但建立或更新 project 時會透過 Resource Catalog 驗證 reference 屬於同一個 tenant。

Queue 依 provider 拆分：

- `geo.query-runs.gemini`
- `geo.query-runs.openai`
- `geo.query-runs.perplexity`

## GEO Analysis Worker

`geo-analysis-worker-gemini` 只消費 Gemini queue：

```env
GEO_ANALYSIS_WORKER_PROVIDER=gemini
GEO_ANALYSIS_WORKER_QUEUE=geo.query-runs.gemini
GEO_ANALYSIS_WORKER_PREFETCH=1
GEO_TRACKING_BASE_URL=http://geo-tracking-api:8003
GEO_TRACKING_TIMEOUT_SECONDS=60
```

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
