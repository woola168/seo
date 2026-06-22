# GEO Analysis API

GEO Analysis API 提供 Phase 1 的 GEO 專案設定、market、entity、topic、query、platform assignment、schedule 與 query run job orchestration endpoint。此服務目前不負責實際 AI 跑題、AI response 儲存或指標計算。

開發環境可用下列方式啟動：

```powershell
uv run uvicorn younilab_geo_analysis_api.main:app --port 8002 --reload
```

## 前端介接共通規則

- JSON 欄位使用 `camelCase`。
- 目前 Phase 1 API 使用 in-memory store，服務重啟會遺失資料。
- `POST /api/geo/jobs/{jobId}/dispatch` 目前會回 `501`，代表 message publisher adapter 尚未設定。
- `cancel` 與 external callback 目前直接操作 in-memory domain entity；後續接 PostgreSQL repository 後會改走 application use case。
- 錯誤回應使用 `application/problem+json`。

Problem Details 格式：

```json
{
  "type": "about:blank",
  "title": "project not found",
  "status": 404,
  "detail": "project not found",
  "instance": "/api/geo/projects/uuid"
}
```

清單 endpoint 回傳簡化版 `PageResponse`：

```json
{
  "items": [],
  "total": 0
}
```

## Projects

| Method | Path | Request | Response |
| --- | --- | --- | --- |
| `GET` | `/api/geo/projects?customerId={customerId}` | query optional | `PageResponse<ProjectResponse>` |
| `POST` | `/api/geo/projects` | `ProjectRequest` | `201 ProjectResponse` |
| `GET` | `/api/geo/projects/{projectId}` | 無 | `ProjectResponse` |
| `PATCH` | `/api/geo/projects/{projectId}` | `ProjectRequest` | `ProjectResponse` |
| `DELETE` | `/api/geo/projects/{projectId}` | 無 | `204` |

```json
// ProjectRequest
{
  "customerId": "uuid",
  "seoTaskId": "uuid",
  "name": "Acme GEO",
  "defaultRegion": "TW",
  "defaultLanguage": "zh-TW",
  "status": "active",
  "dailyRunBudget": 0
}

// ProjectResponse 會額外包含
{
  "id": "uuid",
  "createdAt": "2026-06-22T10:00:00Z",
  "updatedAt": "2026-06-22T10:00:00Z"
}
```

## Markets

| Method | Path | Request | Response |
| --- | --- | --- | --- |
| `GET` | `/api/geo/projects/{projectId}/markets` | 無 | `PageResponse<MarketResponse>` |
| `POST` | `/api/geo/projects/{projectId}/markets` | `MarketRequest` | `201 MarketResponse` |
| `PATCH` | `/api/geo/markets/{marketId}` | `MarketRequest` | `MarketResponse` |
| `DELETE` | `/api/geo/markets/{marketId}` | 無 | `204` |

```json
// MarketRequest
{
  "region": "TW",
  "language": "zh-TW",
  "marketName": "Taiwan Traditional Chinese",
  "promptLocaleHint": "請使用台灣繁體中文回答",
  "serpGl": "tw",
  "serpHl": "zh-TW",
  "serpLocation": "Taiwan",
  "status": "active"
}
```

## Entities 與 Aliases

| Method | Path | Request | Response |
| --- | --- | --- | --- |
| `GET` | `/api/geo/projects/{projectId}/entities` | 無 | `PageResponse<EntityResponse>` |
| `POST` | `/api/geo/projects/{projectId}/entities` | `EntityRequest` | `201 EntityResponse` |
| `GET` | `/api/geo/entities/{entityId}` | 無 | `EntityResponse` |
| `PATCH` | `/api/geo/entities/{entityId}` | `EntityRequest` | `EntityResponse` |
| `DELETE` | `/api/geo/entities/{entityId}` | 無 | `204` |
| `GET` | `/api/geo/entities/{entityId}/aliases` | 無 | `PageResponse<AliasResponse>` |
| `POST` | `/api/geo/entities/{entityId}/aliases` | `AliasRequest` | `201 AliasResponse` |
| `PATCH` | `/api/geo/entity-aliases/{aliasId}` | `AliasRequest` | `AliasResponse` |
| `DELETE` | `/api/geo/entity-aliases/{aliasId}` | 無 | `204` |

```json
// EntityRequest
{
  "entityType": "brand",
  "name": "Acme",
  "websiteUrl": "https://example.com",
  "description": "主要品牌",
  "status": "active"
}

// AliasRequest
{
  "alias": "Acme Inc.",
  "matchType": "exact"
}
```

## Topics 與 Queries

| Method | Path | Request | Response |
| --- | --- | --- | --- |
| `GET` | `/api/geo/projects/{projectId}/topics` | 無 | `PageResponse<TopicResponse>` |
| `POST` | `/api/geo/projects/{projectId}/topics` | `TopicRequest` | `201 TopicResponse` |
| `PATCH` | `/api/geo/topics/{topicId}` | `TopicRequest` | `TopicResponse` |
| `DELETE` | `/api/geo/topics/{topicId}` | 無 | `204` |
| `GET` | `/api/geo/projects/{projectId}/queries` | 無 | `PageResponse<QueryResponse>` |
| `POST` | `/api/geo/projects/{projectId}/queries` | `QueryRequest` | `201 QueryResponse` |
| `GET` | `/api/geo/queries/{queryId}` | 無 | `QueryResponse` |
| `PATCH` | `/api/geo/queries/{queryId}` | `QueryRequest` | `QueryResponse` |
| `DELETE` | `/api/geo/queries/{queryId}` | 無 | `204` |

```json
// TopicRequest
{
  "name": "供應商評估",
  "description": "採購與比較類問題",
  "status": "active"
}

// QueryRequest
{
  "topicId": "uuid",
  "queryText": "台灣可靠的 O-ring 供應商有哪些？",
  "region": "TW",
  "language": "zh-TW",
  "intent": "commercial",
  "buyerStage": "supplier_evaluation",
  "isBranded": false,
  "priority": "normal",
  "status": "active",
  "metadata": {}
}
```

## Query Platforms 與 Schedules

| Method | Path | Request | Response |
| --- | --- | --- | --- |
| `GET` | `/api/geo/queries/{queryId}/platforms` | 無 | `PageResponse<QueryPlatformResponse>` |
| `PUT` | `/api/geo/queries/{queryId}/platforms` | `QueryPlatformRequest[]` | `PageResponse<QueryPlatformResponse>` |
| `GET` | `/api/geo/queries/{queryId}/schedules` | 無 | `PageResponse<ScheduleResponse>` |
| `POST` | `/api/geo/queries/{queryId}/schedules` | `ScheduleRequest` | `201 ScheduleResponse` |
| `PATCH` | `/api/geo/schedules/{scheduleId}` | `ScheduleRequest` | `ScheduleResponse` |
| `DELETE` | `/api/geo/schedules/{scheduleId}` | 無 | `204` |

```json
// QueryPlatformRequest
{
  "platformId": "uuid",
  "model": "gpt-4.1",
  "status": "active"
}

// ScheduleRequest
{
  "platformId": "uuid",
  "frequency": "daily",
  "priority": "normal",
  "timezone": "Asia/Taipei",
  "nextRunAt": "2026-06-23T00:00:00+08:00",
  "status": "active"
}
```

## Query Run Jobs

| Method | Path | Request | Response |
| --- | --- | --- | --- |
| `POST` | `/api/geo/queries/{queryId}/jobs` | `CreateJobRequest` | `201 JobResponse` |
| `GET` | `/api/geo/projects/{projectId}/jobs` | 無 | `PageResponse<JobResponse>` |
| `GET` | `/api/geo/jobs/{jobId}` | 無 | `JobResponse` |
| `POST` | `/api/geo/jobs/{jobId}/dispatch` | 無 | `501` until publisher adapter exists |
| `POST` | `/api/geo/jobs/{jobId}/cancel` | 無 | `JobResponse` |
| `POST` | `/api/geo/jobs/{jobId}/external-callbacks` | `ExternalCallbackRequest` | `JobResponse` |

```json
// CreateJobRequest
{
  "platformId": "uuid",
  "scheduledFor": "2026-06-23T00:00:00+08:00",
  "priority": "normal",
  "jobType": "manual_run"
}

// ExternalCallbackRequest
{
  "externalRunId": "runner-uuid",
  "status": "running",
  "resultLocation": null,
  "errorCode": null,
  "errorMessage": null
}

// JobResponse
{
  "id": "uuid",
  "projectId": "uuid",
  "queryId": "uuid",
  "platformId": "uuid",
  "scheduleId": null,
  "jobType": "manual_run",
  "priority": "normal",
  "scheduledFor": "2026-06-22T16:00:00Z",
  "status": "pending",
  "attemptCount": 0,
  "maxAttempts": 3,
  "dedupeKey": "project:query:platform:2026-06-22T16:00:00+00:00",
  "dispatchBackend": null,
  "dispatchMessageId": null,
  "externalRunId": null,
  "lastErrorCode": null,
  "lastErrorMessage": null,
  "createdAt": "2026-06-22T10:00:00Z",
  "updatedAt": "2026-06-22T10:00:00Z"
}
```

Job status 目前由 orchestration 控制，常見值包含 `pending`、`publishing`、`published`、`running_external`、`succeeded`、`failed`、`delayed`、`cancelled`。已進入 `succeeded`、`failed`、`cancelled` 的 job 不接受 external callback 改寫，也不可再次 cancel。

## Health

| Method | Path | Auth | Response |
| --- | --- | --- | --- |
| `GET` | `/health` | 不需 Bearer | `{ "status": "ok" }` |

