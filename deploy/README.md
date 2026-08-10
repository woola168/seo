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

每日排程、daily slot uniqueness、provider request audit／usage cost、entity mention detection 與 Overview preparation index 均已納入穩定 baseline。全新資料庫只套用 baseline 與必要 seed；既有穩定資料庫不可重跑 baseline。舊版 migration 與當時 rollout 注意事項保留在 `deploy/local/postgresql/archive/pre-stable-baseline/`。

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

## PostgreSQL 穩定 Baseline

全新空白 database 依服務套用一份完整 baseline；CI/CD 不會自動執行：

```powershell
psql "postgresql://USER:PASSWORD@HOST:PORT/ACCESS_CONTROL_DB" -f deploy/local/postgresql/baseline/access_control.sql
psql "postgresql://USER:PASSWORD@HOST:PORT/RESOURCE_CATALOG_DB" -f deploy/local/postgresql/baseline/resource_catalog.sql
psql "postgresql://USER:PASSWORD@HOST:PORT/GEO_ANALYSIS_DB" -f deploy/local/postgresql/baseline/geo_analysis.sql
psql "postgresql://USER:PASSWORD@HOST:PORT/GEO_ANALYSIS_DB" -f deploy/local/postgresql/seed/provider_pricing_rates.sql
```

本機 Compose 為節省資源，GEO Analysis 與 Resource Catalog 共用 `resource_catalog` database，因此會依序套用兩份 baseline 與 provider pricing seed。正式環境若使用獨立 database，則分別套用。

Baseline 僅供全新空白 database 初始化，不是可重複執行的 migration。既有穩定環境不可重跑；舊版 `001` 至 `026` scripts 已移至 `deploy/local/postgresql/archive/pre-stable-baseline/`。後續 schema 變更由 repository root 的 `027_*.sql` 起新增 patch，再於下一次穩定整理時合併。

Demo 帳號資料僅供本機開發，可另外執行 `deploy/local/postgresql/seed/002_access_control_demo_seed.sql`。Provider pricing 是成本 views 的必要系統 seed，使用 `ON CONFLICT DO NOTHING`，可安全補齊缺少的固定費率版本。

OpenAI Query Research／Generation Provider 已包含在 GEO baseline 的 `research_provider` constraint。部署時仍需透過 GitHub Actions Secret 注入
`OPENAI_API_KEY`，不可將 key 寫入環境檔、Compose 或 repository。Compose 只將該值
提供給實際呼叫 OpenAI 的 `geo-tracking-api`：

```powershell
$openAiKey = Read-Host "OpenAI API key" -AsSecureString
$pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($openAiKey)
try {
    $plainText = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer)
    $plainText | gh secret set OPENAI_API_KEY --repo younilab/younilab-seo
} finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer)
    Remove-Variable plainText, openAiKey, pointer -ErrorAction SilentlyContinue
}
```

設定完成後可用 `gh secret list --repo younilab/younilab-seo` 確認 secret 名稱存在；
GitHub 不會回傳 secret 值。部署後只檢查變數是否存在，不可輸出內容：

```bash
docker exec geo-tracking-api sh -lc \
  'printenv OPENAI_API_KEY >/dev/null 2>&1 && echo configured || echo missing'
```

GEO baseline 已包含 Query Planning、tenant scope 與 KMindHub mapping／extraction schema。`geo_ai_platform` 資料仍由各環境 provisioning；部署後應執行下列查詢，確認 DB 與 deployment 的 `GEMINI_MODEL` 一致：

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
