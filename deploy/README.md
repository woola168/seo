# 部署說明

## 部署環境

GitHub Actions 依分支使用不同環境檔：

- `develop` 使用 `deploy/.env.develop`
- `main` 使用 `deploy/.env.prod`

部署流程會 build 並重啟 `deploy/docker-compose.yml` 中的服務，之後透過各服務的 `/health` 做基本檢查。

## 對外 Port

所有服務目前都只綁定在主機的 `127.0.0.1`，外部連線請透過反向代理或 SSH tunnel。

- Admin Portal: `http://127.0.0.1:18080`
- Access Control API: `http://127.0.0.1:18000`
- Resource Catalog API: `http://127.0.0.1:18001`
- GEO Analysis API: `http://127.0.0.1:18002`
- GEO Tracking API: `http://127.0.0.1:18003`
- RabbitMQ AMQP: `127.0.0.1:5672`
- RabbitMQ Management UI: `http://127.0.0.1:15672`

遠端查看 RabbitMQ dashboard 可使用：

```powershell
ssh -L 15672:127.0.0.1:15672 user@server
```

登入帳號密碼由環境檔的 `RABBITMQ_DEFAULT_USER` 與 `RABBITMQ_DEFAULT_PASS` 決定。

## GEO Analysis

`GEO_ANALYSIS_DATABASE_URL` 指向 GEO Analysis 使用的 PostgreSQL database。遠端 DB schema 與 seed 目前不由 CI/CD 自動執行，仍需手動建立 schema，並手動在 `geo_ai_platform` 寫入 Gemini、ChatGPT 等平台資料。

RabbitMQ publisher 由以下設定啟用：

```env
GEO_ANALYSIS_PUBLISHER_BACKEND=rabbitmq
GEO_ANALYSIS_RABBITMQ_URL=amqp://geo_worker:CHANGE_ME@rabbitmq:5672/
GEO_ANALYSIS_RABBITMQ_EXCHANGE=geo.query-runs
GEO_ANALYSIS_RABBITMQ_QUEUE_PREFIX=geo.query-runs
GEO_ANALYSIS_RABBITMQ_ROUTING_KEY_PREFIX=geo.query-runs
GEO_ANALYSIS_CALLBACK_BASE_URL=http://geo-analysis-api:8002
```

Queue 依 provider 拆分，例如：

- `geo.query-runs.gemini`
- `geo.query-runs.openai`
- `geo.query-runs.perplexity`

第三批只包含 publisher 與 dispatch evidence，不包含 worker、AI result 儲存或 `resultLocation` 內容保存。

## GEO Tracking

`geo-tracking-api` 會讀取 Google Vertex AI credential。Service account JSON 不可放進 source control。

環境檔需設定 VM 上的 credential 檔案路徑，Docker Compose 會掛載到容器內的 `/app/config/gcp-key.json`：

```env
GCP_CREDENTIALS_FILE_HOST=/root/kmind/deploy/credentials/dev-gcp-key.json
GOOGLE_APPLICATION_CREDENTIALS=/app/config/gcp-key.json
```

Google AIO 使用 SerpApi，正式環境需設定 `SERPAPI_API_KEY`。

## 本機 PostgreSQL

```powershell
docker compose -f deploy/local/docker-compose.postgresql.yml up -d
```

本機 PostgreSQL：

- Access Control PostgreSQL: `localhost:5432/access_control`
- Resource Catalog PostgreSQL: `localhost:5433/resource_catalog`

初始化 SQL 只會在 volume 第一次建立時執行；若已存在 volume，更新 SQL 後需要手動套用或重建對應 volume。
