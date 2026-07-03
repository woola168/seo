# Resource Catalog API

提供客戶與 SEO 任務主檔 CRUD。前端可用此服務取得 access-control 以外的業務資源顯示名稱與狀態。

開發環境預設使用 `8001`：

```powershell
$env:RESOURCE_CATALOG_DATABASE_URL="postgresql+asyncpg://resource_catalog:resource_catalog@localhost:5433/resource_catalog"
uv run uvicorn younilab_resource_catalog_api.main:app --port 8001 --reload
```

## 前端介接共通規則

- JSON 欄位使用 `camelCase`。
- 所有 `/api` endpoint 需帶 `Authorization: Bearer <accessToken>`。
- API 會將 Bearer token 交給 Access Control API 判斷 `customers.*` 或 `tasks.*` permission。
- API 會使用 Access Control `/api/me/capabilities` 回傳的 `tenantId` 作為資料範圍；前端不可在 request 指定 tenant。
- 若 `hasGlobalResourceAccess` 為 `false`，API 會再依 `customerIds` / `taskIds` 收斂可見資料。
- `customer.name` 只在同一個 tenant 內唯一；不同 tenant 可使用相同 customer name。
- Task 建立或更新時，指定的 `customerId` 必須屬於同一個 tenant。
- Access Control 無法使用時採 fail closed。
- 刪除客戶或任務會將狀態改為 `archived`，不會實體刪除資料。
- 錯誤回應使用 `application/problem+json`。

Problem Details 格式：

```json
{
  "type": "about:blank",
  "title": "Request validation failed",
  "status": 422,
  "detail": "Request validation failed",
  "instance": "/api/customers",
  "invalidParams": [
    {
      "name": "body.name",
      "reason": "Value error, name must not be empty",
      "type": "value_error"
    }
  ]
}
```

## 共用 Response

清單 endpoint 回傳 `PageResponse`：

```json
{
  "items": [],
  "page": 1,
  "pageSize": 20,
  "total": 0,
  "totalPages": 0
}
```

分頁參數：

| Query | 型別 | 預設 | 說明 |
| --- | --- | --- | --- |
| `search` | `string` | `""` | 依名稱搜尋 |
| `status` | `active \| archived` 或空值 | `active` | 空值代表不依狀態過濾 |
| `page` | `number` | `1` | 最小 1 |
| `pageSize` | `number` | `20` | 1 到 100 |

## Customers

| Method | Path | Permission | Request | Response |
| --- | --- | --- | --- | --- |
| `GET` | `/api/customers` | `customers.read` | query params | `PageResponse<CustomerResponse>` |
| `POST` | `/api/customers` | `customers.create` | `SaveCustomerRequest` | `201 CustomerResponse` |
| `GET` | `/api/customers/{customerId}` | `customers.read` | 無 | `CustomerResponse` |
| `PATCH` | `/api/customers/{customerId}` | `customers.update` | `SaveCustomerRequest` | `CustomerResponse` |
| `DELETE` | `/api/customers/{customerId}` | `customers.delete` | 無 | `204` |

```json
// SaveCustomerRequest
{
  "name": "Acme"
}

// CustomerResponse
{
  "id": "uuid",
  "tenantId": "uuid",
  "name": "Acme",
  "status": "active",
  "createdAt": "2026-06-22T10:00:00Z",
  "updatedAt": "2026-06-22T10:00:00Z"
}
```

前端常用查詢：

```http
GET /api/customers?search=acme&status=active&page=1&pageSize=20
Authorization: Bearer <accessToken>
```

非 global resource access 使用者只會看見 `customerIds` 內的 customers；未授權 customer 的 detail、update、delete 會回 `404`。

## Tasks

| Method | Path | Permission | Request | Response |
| --- | --- | --- | --- | --- |
| `GET` | `/api/tasks` | `tasks.read` | query params | `PageResponse<TaskResponse>` |
| `POST` | `/api/tasks` | `tasks.create` | `SaveTaskRequest` | `201 TaskResponse` |
| `GET` | `/api/tasks/{taskId}` | `tasks.read` | 無 | `TaskResponse` |
| `PATCH` | `/api/tasks/{taskId}` | `tasks.update` | `SaveTaskRequest` | `TaskResponse` |
| `DELETE` | `/api/tasks/{taskId}` | `tasks.delete` | 無 | `204` |

Tasks 額外支援 `customerId` query filter：

```http
GET /api/tasks?customerId=<customerId>&search=audit&status=active&page=1&pageSize=20
Authorization: Bearer <accessToken>
```

非 global resource access 使用者只會看見：

- `taskIds` 內明確授權的 tasks。
- 或 `customerId` 屬於 `customerIds` 的 tasks。

建立 task 時，目標 `customerId` 必須在使用者的 `customerIds` 內；更新 task 若要移到另一個 customer，新的 `customerId` 也必須已授權。未授權 resource 會回 `404`。

```json
// SaveTaskRequest
{
  "customerId": "uuid",
  "name": "SEO audit"
}

// TaskResponse
{
  "id": "uuid",
  "tenantId": "uuid",
  "customerId": "uuid",
  "customerName": "Acme",
  "name": "SEO audit",
  "status": "active",
  "createdAt": "2026-06-22T10:00:00Z",
  "updatedAt": "2026-06-22T10:00:00Z"
}
```

## Health

| Method | Path | Auth | Response |
| --- | --- | --- | --- |
| `GET` | `/health` | 不需 Bearer | `{ "status": "ok" }` |
