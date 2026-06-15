# 本機部署

啟動 PostgreSQL：

```powershell
docker compose -f deploy/local/docker-compose.postgresql.yml up -d
```

此 compose 同時啟動：

- Access Control PostgreSQL：`localhost:5432/access_control`
- Resource Catalog PostgreSQL：`localhost:5433/resource_catalog`

既有 Access Control volume 必須手動套用
`local/postgresql/003_access_control_lifecycle.sql`；全新 volume 會由
`docker-entrypoint-initdb.d` 自動套用。

複製 `apps/access-control-api/.env.example` 的設定至 repo 根目錄 `.env.local`，
再啟動 API。正式環境不得使用範例密碼，且必須提供持久化的 RSA private/public
keys。

若資料庫已建立，可透過 DBeaver 手動執行
`local/postgresql/002_access_control_demo_seed.sql` 加入本機測試帳號與權限。
此 seed 僅供本機測試，不應套用至正式環境。
