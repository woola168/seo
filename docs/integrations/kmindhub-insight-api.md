# KMindHub Insight API 串接說明

本文依 `references/younilab-kmindhub-develop` 重新整理，不沿用舊版 `main` 內容。來源以 develop 版本的 FastAPI routes、DTO、測試、Postman collection 與 `.env.example` 為準。

## 服務可以做什麼

KMindHub Insight API 是一個 workspace-scoped 的知識資料抽取、儲存、查詢與 graph metadata 服務。對外 API 使用 `X-Workspace-Id` 區隔資料；目前程式實作會把 workspace id 直接映射為內部 tenant id。

主要能力：

- 建立 workspace。
- 建立、查詢、取代、刪除 extraction task 與欄位定義。
- 由文字或檔案產生 extraction task draft。
- 依 task schema 對文字或檔案執行 extraction preview。
- 將確認後的 extracted items commit 到 MongoDB。
- 對已 commit 的 extracted items 做 CRUD。
- 依自然語意或待比對 item 查詢候選 extracted items。
- 建立 graph domain，將多個 extraction tasks 綁定成 graph nodes。
- 建立 graph relation rules，用欄位對應規則描述 task items 之間的關係。
- 由 LLM 產生 graph domain draft 或既有 graph domain 的 patch draft。

## Runtime 依賴

| 依賴 | 用途 |
| --- | --- |
| PostgreSQL | workspace/tenant、extraction task、graph domain metadata。 |
| MongoDB | 已 commit 的 extracted items 與 retrieval 查詢資料來源。 |
| Neo4j | graph sync 的 graph store。未設定時 graph sync 可能是 no-op。 |
| Gemini / Vertex AI | task draft、extraction、retrieval planning、semantic matching、graph draft。 |

環境變數：

```text
VERTEX_PROJECT_ID=
VERTEX_LOCATION=global
GEMINI_MODEL=gemini-3.1-flash-lite
GEMINI_THINKING_LEVEL=minimal
GOOGLE_APPLICATION_CREDENTIALS=
POSTGRES_METADATA_DSN=
MONGODB_URI=
MONGODB_DATABASE=kmindhub
MONGODB_EXTRACTION_COLLECTION=extraction_items
NEO4J_URI=
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=
NEO4J_DATABASE=neo4j
```

本機預設：

```text
Base URL: http://127.0.0.1:8000
OpenAPI:  http://127.0.0.1:8000/docs
```

啟動 API：

```powershell
uv run --package younilab-kmindhub-insight-api fastapi dev apps/younilab-kmindhub-insight-api/src/younilab_kmindhub_insight_api/main.py --host 127.0.0.1 --port 8000
```

## 通用串接規則

除了 `POST /workspaces` 與 `/openapi.json`，其他 runtime API 都要帶：

```text
X-Workspace-Id: <workspace UUID>
```

JSON 欄位使用 `camelCase`。分頁 API 支援：

```text
?limit=&cursor=
```

`limit` 預設 `50`，最小 `1`，最大會被限制為 `100`。

常見錯誤：

```json
{
  "detail": "X-Workspace-Id header is required"
}
```

常見狀態碼：

| 狀態碼 | 情境 |
| --- | --- |
| `200` | 查詢、更新、draft、patch 成功。 |
| `201` | 建立成功。 |
| `204` | 刪除或 replace item 成功，無 response body。 |
| `400` | header、UUID、payload、欄位規則不合法。 |
| `404` | task、item、graph domain 等資源不存在。 |
| `502` | LLM、資料庫或 runtime adapter 失敗。 |

Fixture：

| 名稱 | 值 |
| --- | --- |
| `X-Workspace-Id` | `11111111-1111-4111-8111-111111111111` |
| `fixtureTaskId` | `33333333-3333-4333-8333-333333333333` |

## API 一覽

### Workspace

| Method | Path | 說明 |
| --- | --- | --- |
| `POST` | `/workspaces` | 建立 workspace，回傳 `workspaceId`。 |

Request：

```json
{
  "displayName": "ABC Company"
}
```

Response：

```json
{
  "workspaceId": "workspace UUID"
}
```

`displayName` 不可空白。此 API 目前會建立一筆 tenant，並以 tenant id 作為 workspace id。

### Extraction Tasks

| Method | Path | 說明 |
| --- | --- | --- |
| `POST` | `/extraction-tasks/drafts` | 由文字或檔案產生 task draft，不寫入資料庫。 |
| `POST` | `/extraction-tasks` | 建立 extraction task aggregate。 |
| `GET` | `/extraction-tasks?limit=&cursor=` | 列出 workspace 底下的 tasks，回傳 summary，不含 fields。 |
| `GET` | `/extraction-tasks/{taskId}` | 取得單一 task，含 fields。 |
| `PUT` | `/extraction-tasks/{taskId}` | 取代 task aggregate 與 fields。 |
| `DELETE` | `/extraction-tasks/{taskId}` | soft delete task aggregate。 |

Draft 使用 `multipart/form-data`：

| Field | Type | 說明 |
| --- | --- | --- |
| `texts` | repeated text | 可傳一段或多段文字。 |
| `files` | repeated file | 可傳一個或多個檔案。 |

若 `texts` 與 `files` 都沒有有效內容，回 `400`：`texts or files is required`。

建立 task request：

```json
{
  "name": "invoice extraction",
  "task": "Extract invoice number, invoice date, buyer tax id, and total amount from an invoice.",
  "description": "Invoice extraction schema.",
  "status": "active",
  "fields": [
    {
      "name": "invoiceNo",
      "fieldType": "string",
      "lookupRole": "primary",
      "displayName": "發票號碼",
      "description": "Invoice number.",
      "normalization": {
        "instruction": "Return a normalized invoice number.",
        "regexPattern": "^[A-Z]{2}\\d{8}$"
      },
      "examples": "AB12345678",
      "sortOrder": 0,
      "isVisible": true,
      "isExtracted": true
    }
  ]
}
```

欄位 enum：

| 欄位 | 可用值 |
| --- | --- |
| `status` | `active`、`disabled` |
| `fieldType` | `string`、`int`、`decimal`、`double`、`float`、`boolean`、`date`、`time`、`datetime` |
| `lookupRole` | `primary`、`combined`、`ignored` |

`PUT /extraction-tasks/{taskId}` 是整包 replace。若要保留既有 field，payload 必須帶該 field 的 `id`；若 field name 已存在但沒有帶 `id`，會回 `400`。

### Extraction Preview 與 Commit

| Method | Path | 說明 |
| --- | --- | --- |
| `POST` | `/extractions` | 執行 extraction preview，不寫入 MongoDB。 |
| `POST` | `/extractions/commit` | 將確認後的 items 寫入 MongoDB。 |

Preview 使用 `multipart/form-data`：

| Field | Type | Required | 說明 |
| --- | --- | --- | --- |
| `taskId` | text UUID | Yes | extraction task id。 |
| `text` | text | `file` 擇一 | 直接抽取文字。 |
| `file` | file | `text` 擇一 | 抽取上傳檔案。 |

限制：

- `file` 與 `text` 不可同時提供。
- 至少提供一個有效 `file` 或 `text`。
- 上傳檔案必須有 filename 與 MIME type。
- 程式碼目前沒有讀取 Postman 中的 `sourceId` 或 `mimeType` form 欄位；實際 source id 由 inline text 或 filename 決定。

PowerShell 範例：

```powershell
$form = @{
  taskId = "33333333-3333-4333-8333-333333333333"
  text = "交通違規單號 RU0320，違規日期 2025-05-01，罰鍰 3600 元。"
}

Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/extractions" `
  -Headers @{ "X-Workspace-Id" = "11111111-1111-4111-8111-111111111111" } `
  -Form $form
```

Preview response 重點：

```json
{
  "tenantId": "workspace UUID",
  "taskId": "task UUID",
  "source": {
    "sourceId": "inline-text",
    "mediaType": "text",
    "mimeType": "text/plain"
  },
  "createdAt": "2026-07-01T00:00:00Z",
  "items": [
    {
      "fields": {
        "ticketNo": {
          "value": "RU0320",
          "evidence": []
        }
      },
      "verification": {
        "passed": true,
        "failures": []
      },
      "displayFields": [],
      "candidates": []
    }
  ]
}
```

Commit request：

```json
{
  "taskId": "33333333-3333-4333-8333-333333333333",
  "items": [
    {
      "itemId": null,
      "fields": {
        "ticketNo": {
          "value": "RU0320",
          "evidence": []
        }
      }
    }
  ]
}
```

`itemId: null` 表示新增 item；填入候選 item id 時可更新或合併到既有 item。成功 response 會包含 `commitBatchId` 與 committed item ids。

### Extracted Items

| Method | Path | 說明 |
| --- | --- | --- |
| `POST` | `/extraction-tasks/{taskId}/items` | 直接建立一批 extracted items。 |
| `GET` | `/extraction-tasks/{taskId}/items?limit=&cursor=` | 分頁列出 task items。 |
| `GET` | `/extraction-tasks/{taskId}/items/{itemId}` | 取得單一 item。 |
| `PUT` | `/extraction-tasks/{taskId}/items/{itemId}` | 取代單一 item，成功回 `204`。 |
| `DELETE` | `/extraction-tasks/{taskId}/items/{itemId}` | 刪除單一 item，成功回 `204`。 |

建立 items：

```json
{
  "items": [
    {
      "fields": {
        "invoiceNo": {
          "value": "AB12345678",
          "evidence": []
        }
      }
    }
  ]
}
```

Item response：

```json
{
  "itemId": "item UUID",
  "tenantId": "workspace UUID",
  "commitBatchId": "commit batch UUID",
  "taskId": "task UUID",
  "createdAt": "2026-07-01T00:00:00Z",
  "fields": {},
  "displayFields": []
}
```

### Retrieval

| Method | Path | 說明 |
| --- | --- | --- |
| `POST` | `/retrievals/intention` | 用自然語意查詢已 commit 的 items。 |
| `POST` | `/retrievals/candidates` | 用待比對 item 查詢候選 items。 |

Intention request：

```json
{
  "taskId": "33333333-3333-4333-8333-333333333333",
  "intention": "找出罰鍰金額大於 3000 元的違規單",
  "limit": 10
}
```

Candidates request：

```json
{
  "taskId": "33333333-3333-4333-8333-333333333333",
  "items": [
    {
      "fields": {
        "ticketNo": "RU0320",
        "amount": 3600
      }
    }
  ],
  "limit": 10
}
```

Response 會包含 lookup/semantic criteria、matched candidates、`resolution` 判斷、supporting/conflicting/missing fields。

### Graph Domains

Graph APIs 用來把多個 extraction tasks 建成 graph domain，並定義 task items 之間如何形成 Neo4j 關係。

| Method | Path | 說明 |
| --- | --- | --- |
| `POST` | `/graph-domains/drafts` | 依 task ids 與 instruction 產生新 graph domain draft，不寫入資料庫。 |
| `POST` | `/graph-domains` | 建立 graph domain aggregate，可同時建立 tasks 與 relation rules。 |
| `POST` | `/graph-domains/{graphDomainId}/drafts` | 對既有 graph domain 產生 patch draft，不寫入資料庫。 |
| `PATCH` | `/graph-domains/{graphDomainId}` | 對既有 graph domain 新增 tasks 與 relation rules。 |
| `GET` | `/graph-domains?limit=&cursor=` | 列出 graph domains。 |
| `GET` | `/graph-domains/{graphDomainId}` | 取得 graph domain metadata。 |
| `PUT` | `/graph-domains/{graphDomainId}` | 更新 graph domain metadata。 |
| `DELETE` | `/graph-domains/{graphDomainId}` | soft delete graph domain。 |

Graph domain draft request：

```json
{
  "taskIds": [
    "cpu task UUID",
    "motherboard task UUID"
  ],
  "instruction": "建立組裝電腦相容性 graph"
}
```

Create graph domain aggregate request：

```json
{
  "key": "pc_build",
  "name": "PC Build",
  "description": "PC compatibility graph.",
  "status": "active",
  "tasks": [
    {
      "taskId": "cpu task UUID",
      "nodeLabel": "Artifact",
      "nameField": "model",
      "status": "active"
    },
    {
      "taskId": "motherboard task UUID",
      "nodeLabel": "Artifact",
      "nameField": "model",
      "status": "active"
    }
  ],
  "relationRules": [
    {
      "sourceTaskId": "cpu task UUID",
      "targetTaskId": "motherboard task UUID",
      "relationshipType": "CORRELATES",
      "relationVerb": "compatible_with",
      "context": "CPU socket matches motherboard socket.",
      "fieldMatches": [
        {
          "sourceField": "socket",
          "targetField": "cpu_socket"
        }
      ],
      "status": "active"
    }
  ]
}
```

Graph enum：

| 欄位 | 可用值 |
| --- | --- |
| `nodeLabel` | `Actor`、`Artifact`、`Concept`、`Event`、`Location`、`Time` |
| `relationshipType` | `IS_A`、`PART_OF`、`AFFECTS`、`POSSESSES`、`CORRELATES` |

### Graph Domain Tasks

| Method | Path | 說明 |
| --- | --- | --- |
| `POST` | `/graph-domain-tasks` | 把 extraction task 註冊到 graph domain。 |
| `GET` | `/graph-domain-tasks?graphDomainId=&taskId=&limit=&cursor=` | 查詢 task bindings，可用 graphDomainId 或 taskId 篩選。 |
| `PUT` | `/graph-domain-tasks/{graphDomainTaskId}` | 更新 task binding。 |
| `DELETE` | `/graph-domain-tasks/{graphDomainTaskId}` | soft delete task binding。 |

Request：

```json
{
  "graphDomainId": "graph domain UUID",
  "taskId": "extraction task UUID",
  "nodeLabel": "Artifact",
  "nameField": "model",
  "status": "active"
}
```

驗證規則：

- `graphDomainId` 必須存在於同一個 workspace。
- `taskId` 必須存在於同一個 workspace。
- `nameField` 必須是該 extraction task 已定義的 field name。

### Graph Relation Rules

| Method | Path | 說明 |
| --- | --- | --- |
| `POST` | `/graph-relation-rules` | 建立 graph relation rule。 |
| `GET` | `/graph-relation-rules?graphDomainId=&taskId=&limit=&cursor=` | 查詢 relation rules，可用 graphDomainId 或 taskId 篩選。 |
| `PUT` | `/graph-relation-rules/{graphRelationRuleId}` | 更新 relation rule。 |
| `DELETE` | `/graph-relation-rules/{graphRelationRuleId}` | soft delete relation rule。 |

Request：

```json
{
  "graphDomainId": "graph domain UUID",
  "sourceTaskId": "source task UUID",
  "targetTaskId": "target task UUID",
  "relationshipType": "CORRELATES",
  "relationVerb": "compatible_with",
  "context": "CPU socket must match motherboard CPU socket.",
  "fieldMatches": [
    {
      "sourceField": "socket",
      "targetField": "cpu_socket"
    }
  ],
  "status": "active"
}
```

驗證規則：

- graph domain 必須存在。
- source/target extraction tasks 必須存在。
- source/target tasks 必須已註冊在同一個 graph domain。
- `sourceField` 必須存在於 source task。
- `targetField` 必須存在於 target task。

## Evidence 格式

每個 extracted field 可帶 evidence：

```json
{
  "value": "RU0320",
  "evidence": [
    {
      "source": {
        "sourceId": "inline-text",
        "mediaType": "text"
      },
      "locator": {
        "pageNumber": null,
        "startOffset": 0,
        "endOffset": 10,
        "startSeconds": null,
        "endSeconds": null,
        "boundingBox": null,
        "locatorNote": null
      },
      "excerpt": "交通違規單號 RU0320"
    }
  ]
}
```

`mediaType` 可用值：`text`、`document`、`image`、`audio`、`video`、`table`、`unknown`。

## 建議串接流程

1. 呼叫 `POST /workspaces` 建立 workspace，保存 `workspaceId`。
2. 後續所有 runtime API 都帶 `X-Workspace-Id: <workspaceId>`。
3. 建立 extraction tasks，定義欄位、lookup role、normalization 與 display 設定。
4. 用 `POST /extractions` 產生 preview，檢查 `verification`、`displayFields`、`candidates`。
5. 用 `POST /extractions/commit` 寫入 MongoDB。
6. 用 item CRUD 維護資料，或用 retrieval API 查詢既有 items。
7. 若要做 graph，先建立 graph domain，再把相關 extraction tasks 註冊為 graph domain tasks，最後建立 relation rules。
8. 若需要 LLM 協助設計 graph，可先呼叫 graph draft APIs，再把 draft 調整後送到 create/patch API。

## 開發注意事項

- 新版 API header 是 `X-Workspace-Id`，不是舊版文件中的 `X-Tenant-Id`。
- Response 仍會出現 `tenantId`，目前可視為 workspace id 對應的內部 tenant id。
- `POST /extractions` 只做 preview，不持久化 item。
- `POST /extractions/commit` 與 item CRUD 會寫 MongoDB。
- graph metadata 存 PostgreSQL；graph sync 依賴 Neo4j 設定。
- Graph relation rule 要求 source/target tasks 都已註冊到同一 graph domain。
- 目前未看到對外 API token/API key 驗證；若要公開串接，建議在我們的整合層補授權、rate limit 與 audit log。
- Reference README 仍有部分中文編碼亂碼；本文以 source code、tests、Postman collection 可驗證內容為準。

## 來源檔案

- `references/younilab-kmindhub-develop/apps/younilab-kmindhub-insight-api/src/younilab_kmindhub_insight_api/presentation/http/routes/*.py`
- `references/younilab-kmindhub-develop/apps/younilab-kmindhub-insight-api/src/younilab_kmindhub_insight_api/presentation/http/dtos/*.py`
- `references/younilab-kmindhub-develop/apps/younilab-kmindhub-insight-api/tests/presentation/http/*.py`
- `references/younilab-kmindhub-develop/apps/younilab-kmindhub-insight-api/postman/kmindhub-insight-api.postman_collection.json`
- `references/younilab-kmindhub-develop/apps/younilab-kmindhub-insight-api/.env.example`
