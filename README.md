# Younilab SEO Access Control

本專案提供單一 SEO 後台使用的身分驗證與權限控管 API。

授權由兩部分組成：

- 角色所提供的功能權限，例如 `customers.read`、`tasks.update`。
- 使用者獲授權的客戶或單一 SEO 任務資料範圍。

`references/` 僅作為架構參考，不是 workspace 或 runtime dependency。

## 開發

```powershell
uv sync
uv run pytest
uv run uvicorn younilab_access_control_api.main:app --reload
```

API 預設使用 `ACCESS_CONTROL_DATABASE_URL` 連接 PostgreSQL。測試使用記憶體內的
repository，不需要啟動外部服務。

套用 `deploy/local/postgresql/001_access_control_schema.sql` 後，以互動方式建立
第一位管理員：

```powershell
uv run python -m younilab_access_control_api.bootstrap `
  --email admin@example.com `
  --display-name "SEO Admin"
```

## 本機資料庫測試

先在 PostgreSQL 執行：

1. `deploy/local/postgresql/001_access_control_schema.sql`
2. `deploy/local/postgresql/002_access_control_demo_seed.sql`

第二份 SQL 會建立兩個測試帳號：

- `admin@example.com`
- `specialist@example.com`
- 共用測試密碼：`DemoPassword123!`

設定資料庫連線並啟動 API：

```powershell
$env:ACCESS_CONTROL_DATABASE_URL="postgresql+asyncpg://access_control:access_control@localhost:5432/access_control"
uv run uvicorn younilab_access_control_api.main:app --reload
```

另一個終端啟動 Vue portal：

```powershell
npm install --cache .npm-cache
npm run dev:portal
```

開啟 `http://127.0.0.1:5173`，使用上述測試帳號登入。
