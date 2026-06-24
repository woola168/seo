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

## 本機 PostgreSQL

```powershell
docker compose -f deploy/local/docker-compose.postgresql.yml up -d
```

本機 PostgreSQL：

- Access Control PostgreSQL: `localhost:5432/access_control`
- Resource Catalog PostgreSQL: `localhost:5433/resource_catalog`

若已建立過 volume，新增或修改 `docker-entrypoint-initdb.d` SQL 不會自動重跑；需要重建
本機 volume 或手動套用 SQL。
