# Resource Catalog API

提供客戶與 SEO 任務主檔 CRUD，開發環境預設使用 `8001`。

```powershell
$env:RESOURCE_CATALOG_DATABASE_URL="postgresql+asyncpg://resource_catalog:resource_catalog@localhost:5433/resource_catalog"
uv run uvicorn younilab_resource_catalog_api.main:app --port 8001 --reload
```

所有 `/api/v1` 端點會將 Bearer Token 交給 Access Control API 判斷
`customers.*` 或 `tasks.*` Permission。Access Control 無法使用時採 fail closed。

刪除客戶或任務會將狀態改為 `archived`，不會實體刪除資料。
