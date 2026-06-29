# 部署設定

## 環境檔

GitHub Actions 依分支選擇部署環境檔：

- `develop` 使用 `deploy/.env.develop`
- `main` 使用 `deploy/.env.prod`

遠端 PostgreSQL schema 與 seed 仍由人工執行；CI/CD 不會自動跑 migration。

## 對外 Port

Compose 內的服務預設只綁定 `127.0.0.1`，需要從外部查看時請透過 SSH tunnel 或反向代理開放。

- Admin Portal: `http://127.0.0.1:18080`
- Access Control API: `http://127.0.0.1:18004`
- Resource Catalog API: `http://127.0.0.1:18001`
- GEO Analysis API: `http://127.0.0.1:18002`
- GEO Tracking API: `http://127.0.0.1:18003`
- RabbitMQ AMQP: `127.0.0.1:5672`
- RabbitMQ Management UI: `http://127.0.0.1:15672`

RabbitMQ dashboard 範例：

```powershell
ssh -L 15672:127.0.0.1:15672 user@server
```

登入帳密使用 `RABBITMQ_DEFAULT_USER` 與 `RABBITMQ_DEFAULT_PASS`。

## Compose env file path

`DEPLOY_ENV_FILE` is consumed by `deploy/docker-compose.yml` `env_file` entries.
Use `.env.develop` or `.env.prod` because Docker Compose resolves the path from
the `deploy/` directory when running with `-f deploy/docker-compose.yml`.

## GEO Analysis

`GEO_ANALYSIS_DATABASE_URL` 指向 GEO Analysis PostgreSQL database。`geo_ai_platform` 資料目前仍由人工 seed，例如 Gemini、ChatGPT 等 platform。

RabbitMQ publisher 設定：

```env
GEO_ANALYSIS_PUBLISHER_BACKEND=rabbitmq
GEO_ANALYSIS_RABBITMQ_URL=amqp://geo_worker:CHANGE_ME@rabbitmq:5672/
GEO_ANALYSIS_RABBITMQ_EXCHANGE=geo.query-runs
GEO_ANALYSIS_RABBITMQ_QUEUE_PREFIX=geo.query-runs
GEO_ANALYSIS_RABBITMQ_ROUTING_KEY_PREFIX=geo.query-runs
GEO_ANALYSIS_CALLBACK_BASE_URL=http://geo-analysis-api:8002
```

Queue 依 provider 拆分，常見命名如下：

- `geo.query-runs.gemini`
- `geo.query-runs.openai`
- `geo.query-runs.perplexity`

## GEO Analysis Worker

本批新增 `geo-analysis-worker-gemini`，只消費 Gemini queue：

```env
GEO_ANALYSIS_WORKER_PROVIDER=gemini
GEO_ANALYSIS_WORKER_QUEUE=geo.query-runs.gemini
GEO_ANALYSIS_WORKER_PREFETCH=1
GEO_TRACKING_BASE_URL=http://geo-tracking-api:8003
GEO_TRACKING_TIMEOUT_SECONDS=60
```

`geo-analysis-worker-google-aio` 會使用同一個 worker image，並覆寫
`GEO_ANALYSIS_WORKER_PROVIDER=google_aio` 與
`GEO_ANALYSIS_WORKER_QUEUE=geo.query-runs.google_aio`。正式跑 Google AIO 前，
`geo-tracking-api` 的部署環境必須注入 `SERPAPI_API_KEY`；此 key 不應寫入 repo。

### GEO Analysis Worker result storage

GEO Analysis provider worker 會把 RabbitMQ message 轉成 `geo-tracking-api` 的 `/api/v1/geo-tracking/run-requests` payload。Tracking completed 時會保存 `geo_run_request`、`geo_run_result`、`geo_run_result_reference`，並把 GEO job 標記為 `succeeded`；tracking failed、HTTP timeout、unsupported provider 時會保存失敗 evidence 並把 job 標記為 `failed`。

目前 raw response 存在 PostgreSQL `text` 欄位，references 存在 `geo_run_result_reference`。Mention、citation normalization、sentiment、visibility/SOV 與報表 metrics 尚未實作。

## GEO Tracking

`geo-tracking-api` 需要 Google Vertex AI service account JSON，請放在 VM 上並透過 Compose volume 掛載，不要提交到 source control。

```env
GCP_CREDENTIALS_FILE_HOST=/root/kmind/deploy/credentials/dev-gcp-key.json
GOOGLE_APPLICATION_CREDENTIALS=/app/config/gcp-key.json
```

Google AIO 會使用 SerpApi，請在需要時設定 `SERPAPI_API_KEY`。

## 本機 PostgreSQL

```powershell
docker compose -f deploy/local/docker-compose.postgresql.yml up -d
```

本機 PostgreSQL：

- Access Control PostgreSQL: `localhost:5432/access_control`
- Resource Catalog PostgreSQL: `localhost:5433/resource_catalog`

## GEO Analysis 手動 DB Patch

遠端 PostgreSQL schema 與 seed 仍由人工執行，CI/CD 不會自動跑 migration。若環境已套用舊版 `004_geo_analysis_schema.sql`，升級 Query Planning 前需手動執行：

```powershell
psql "postgresql://USER:PASSWORD@HOST:PORT/DB_NAME" -f deploy/local/postgresql/005_geo_analysis_query_planning_patch.sql
```

這份 patch 會解除 `geo_project.customer_id` 的 `NOT NULL` 限制，並建立 `geo_query_research_run`、`geo_query_generation_run`、`geo_query_draft`、`geo_query_draft_selection` 與必要 indexes。新環境仍可直接使用 `deploy/local/postgresql/004_geo_analysis_schema.sql` 初始化完整 schema。
