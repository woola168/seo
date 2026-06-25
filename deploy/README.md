# 部署說明

## 遠端部署

GitHub Actions 會依分支選擇環境檔：

- `develop` 使用 `deploy/.env.develop`
- `main` 使用 `deploy/.env.prod`

部署流程會 build 並啟動 `deploy/docker-compose.yml` 中的服務，接著檢查各服務
`/health`。

## 服務與 Port

- Admin Portal: `http://127.0.0.1:18080`
- Access Control API: `http://127.0.0.1:18000`
- Resource Catalog API: `http://127.0.0.1:18001`
- GEO Analysis API: `http://127.0.0.1:18002`
- GEO Tracking API: `http://127.0.0.1:18003`

## GEO Analysis 資料庫

`GEO_ANALYSIS_DATABASE_URL` 目前指向 `resource_catalog` database。遠端 DB schema
與 seed 不會由 CI/CD 自動執行，請手動在目標 database 建立 GEO Analysis schema，
並手動寫入 `geo_ai_platform` 的 Gemini、ChatGPT 等平台資料。

## GEO Tracking 憑證

`geo-tracking-api` 透過掛載檔案讀取 Google Vertex AI credential，不把 service
account JSON 放進 source control。

在部署環境檔設定 `GCP_CREDENTIALS_FILE_HOST` 為 VM 上的 Google service account
JSON 路徑。Docker Compose 會將該檔案掛載到容器內
`/app/config/gcp-key.json`，並讓 `GOOGLE_APPLICATION_CREDENTIALS` 指向該容器內路徑。

範例：

```env
GCP_CREDENTIALS_FILE_HOST=/root/kmind/deploy/credentials/dev-gcp-key.json
GOOGLE_APPLICATION_CREDENTIALS=/app/config/gcp-key.json
```

Google AIO 使用 SerpApi；若要執行 live `google_aio` 跑題，仍需在部署環境檔設定
`SERPAPI_API_KEY`。

## 本機 PostgreSQL

```powershell
docker compose -f deploy/local/docker-compose.postgresql.yml up -d
```

本機 PostgreSQL：

- Access Control PostgreSQL: `localhost:5432/access_control`
- Resource Catalog PostgreSQL: `localhost:5433/resource_catalog`

若已建立過 volume，新增或修改 `docker-entrypoint-initdb.d` SQL 不會自動重跑；需要重建
本機 volume 或手動套用 SQL。
