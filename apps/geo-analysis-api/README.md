# GEO Analysis API

GEO Analysis API 提供 GEO 專案設定、market、entity、topic、query、platform assignment、schedule、query run job orchestration 與 report metrics endpoint。實際 AI 跑題由 `geo-tracking-api` 負責；本服務負責 dispatch、job orchestration、worker 回寫的 raw result / references 保存，以及透過 application use case 讀取已正規化 facts 計算報表指標。

開發環境可用下列方式啟動：

```powershell
uv run uvicorn younilab_geo_analysis_api.main:app --port 8002 --reload
```

## Persistence 模式

- Routes 只負責 HTTP DTO 與 response mapping，實際流程透過 `ManageGeoSetup` 與 `ManageQueryRunJobs` use cases 執行。
- `presentation/http/composition.py` 負責組裝 repository、clock 與 use cases，並掛到 `app.state`。
- 預設未設定資料庫時，API 使用 in-memory `GeoApiStore` 作為測試用 fake repository，適合單元測試與前端 stub 串接，服務重啟會遺失資料。
- 設定 `GEO_ANALYSIS_DATABASE_URL` 後，API 會使用 `PostgresGeoAnalysisRepository` 作為 PostgreSQL infrastructure adapter。
- Local PostgreSQL 初始化 SQL 位於 `deploy/local/postgresql/004_geo_analysis_schema.sql`。
- 既有遠端 DB 若已跑過舊版 schema，需手動執行 `deploy/local/postgresql/005_geo_analysis_query_planning_patch.sql`，補上 Query Planning tables 並解除 `geo_project.customer_id` 的 `NOT NULL` 限制。
- 既有遠端 DB 若尚未 tenant 化，需再手動執行 `deploy/local/postgresql/009_geo_analysis_tenant_patch.sql`，替 `geo_project` 補上 `tenant_id` 並回填 default tenant。
- 既有遠端 DB 若要啟用 KMindHub workspace mapping，需手動執行 `deploy/local/postgresql/010_kmindhub_workspace_mapping_patch.sql`。
- 既有遠端 DB 若要啟用 KMindHub analysis extraction，需手動執行 `deploy/local/postgresql/011_geo_analysis_kmindhub_extraction_patch.sql`。
- 使用者 API 需帶 Access Control Bearer token；GEO Analysis 透過 `/api/me/capabilities` 取得目前使用者 `tenantId`，request 不需要也不允許自行指定 tenant。
- `ProjectResponse` 會回傳 `tenantId`；project list/create/query/job/run result 都以目前 tenant 作為最外層資料邊界。
- `customerId` / `seoTaskId` 維持 nullable reference-only 欄位，不建立跨服務 DB FK；建立或更新 project 時會透過 Resource Catalog 驗證 reference 屬於同 tenant。
- 第一批 persistence 已支援 GEO setup CRUD、query platform、schedule、job、dispatch evidence、external callback reference。
- External callback 由 repository 的 transaction-capable operation 同步更新 job 狀態並寫入 external reference/event。
- RabbitMQ publisher 已支援 `POST /api/geo/jobs/{jobId}/dispatch`；`geo-analysis-worker-gemini` 與 `geo-analysis-worker-google-aio` 會依 provider queue 呼叫 `geo-tracking-api`，並保存 raw result 與 references。Report metrics API 讀取新的 semantic facts / citation facts pipeline；metrics snapshot persistence 與額外 worker trigger 仍屬後續批次。
- KMindHub workspace 採手動優先策略；tenant 第一次使用後續 analysis extraction 前，需先用 API 綁定既有 workspace 或明確 provision workspace。Worker 不會在首次執行時自動建立 workspace，也不會 fallback 到 default workspace。
- KMindHub Insight extraction 的完整流程與欄位定義請參考 `docs/integrations/geo-analysis-kmindhub-insight-extraction.md`。
- 測試可繼續使用 in-memory fake repository 或 mock data，不需要連線真實 PostgreSQL。

範例：

```powershell
$env:GEO_ANALYSIS_DATABASE_URL = "postgresql+asyncpg://resource_catalog:resource_catalog@127.0.0.1:5433/resource_catalog"
$env:GEO_ANALYSIS_ACCESS_CONTROL_URL = "http://127.0.0.1:8000"
$env:GEO_ANALYSIS_RESOURCE_CATALOG_URL = "http://127.0.0.1:8001"
$env:KMINDHUB_INSIGHT_BASE_URL = "http://127.0.0.1:8010"
uv run uvicorn younilab_geo_analysis_api.main:app --port 8002 --reload
```

### KMindHub Workspace Mapping

一個 tenant 只會對應一個 KMindHub workspace。`tenantId` 由 Access Control token 解析，request body 不接受 client 自行指定。

手動綁定既有 workspace：

```http
PUT /api/geo/integrations/kmindhub/workspace
Content-Type: application/json

{
  "workspaceId": "00000000-0000-4000-8000-000000000001",
  "displayName": "Acme Workspace",
  "status": "active"
}
```

明確建立並保存 mapping：

```http
POST /api/geo/integrations/kmindhub/workspace/provision
Content-Type: application/json

{
  "displayName": "Acme Workspace"
}
```

`provision` 僅供 tenant 第一次建立 workspace mapping 使用；若 tenant 已有 mapping 會回 `409`，不會再次呼叫 KMindHub 建立 workspace。更換 workspace 請使用 `PUT /api/geo/integrations/kmindhub/workspace` 手動綁定既有 workspace。

取得目前 tenant mapping：

```http
GET /api/geo/integrations/kmindhub/workspace
```

response：

```json
{
  "id": "00000000-0000-4000-8000-000000000010",
  "tenantId": "00000000-0000-4000-8000-000000000001",
  "workspaceId": "00000000-0000-4000-8000-000000000011",
  "displayName": "Acme Workspace",
  "provisioningMode": "manual",
  "status": "active",
  "createdAt": "2026-07-02T00:00:00Z",
  "updatedAt": "2026-07-02T00:00:00Z"
}
```

### Report Metrics

報表指標由 `CalculateGeoReportMetrics` application use case 計算，API route 只負責授權、query parameter validation 與 response DTO mapping。資料來源是已保存的 completed run results、semantic facts 與 citation normalization facts；API 不會在讀取 metrics 時觸發 worker 或重新分析。

```http
GET /api/geo/projects/{projectId}/metrics?periodStart=2026-06-24T00:00:00Z&periodEnd=2026-06-26T00:00:00Z&comparisonStart=2026-06-22T00:00:00Z&comparisonEnd=2026-06-24T00:00:00Z
Authorization: Bearer <access-token>
```

可選 query parameters：

- `queryId`
- `topicId`
- `provider`
- `region`
- `language`

response：

```json
{
  "periodStart": "2026-06-24T00:00:00Z",
  "periodEnd": "2026-06-26T00:00:00Z",
  "comparisonStart": "2026-06-22T00:00:00Z",
  "comparisonEnd": "2026-06-24T00:00:00Z",
  "metrics": [
    {
      "metricName": "visibility",
      "scopeType": "project",
      "scopeValue": null,
      "scopeLabel": null,
      "value": 100,
      "unit": "percent",
      "numerator": 1,
      "denominator": 1,
      "comparisonValue": 0,
      "delta": 100,
      "deltaUnit": "pp"
    }
  ]
}
```

### 手動建立 AI Platform

遠端部署目前不由 CI/CD 自動執行 DB schema 或 seed。執行 `004_geo_analysis_schema.sql` 後，需手動在 `geo_ai_platform` 寫入可派送的平台資料，後續建立 query platform、schedule、job 時會使用這些 `id`。

建議第一版手動 insert：

```sql
INSERT INTO geo_ai_platform (
    id,
    code,
    display_name,
    provider_type,
    default_model,
    supports_citations,
    supports_grounding,
    status,
    created_at,
    updated_at
) VALUES
(
    '11111111-1111-4111-8111-111111111101',
    'openai',
    'ChatGPT',
    'llm_api',
    'gpt-4.1',
    false,
    true,
    'active',
    now(),
    now()
),
(
    '11111111-1111-4111-8111-111111111102',
    'gemini',
    'Gemini',
    'llm_api',
    'gemini-2.5-pro',
    true,
    true,
    'active',
    now(),
    now()
),
(
    '11111111-1111-4111-8111-111111111103',
    'claude',
    'Claude',
    'llm_api',
    'claude-sonnet-4',
    false,
    false,
    'active',
    now(),
    now()
),
(
    '11111111-1111-4111-8111-111111111104',
    'perplexity',
    'Perplexity',
    'llm_api',
    'sonar',
    true,
    true,
    'active',
    now(),
    now()
),
(
    '11111111-1111-4111-8111-111111111105',
    'google_aio',
    'Google AIO',
    'serp_api',
    'ai-overview',
    true,
    true,
    'active',
    now(),
    now()
)
ON CONFLICT (code) DO UPDATE SET
    display_name = EXCLUDED.display_name,
    provider_type = EXCLUDED.provider_type,
    default_model = EXCLUDED.default_model,
    supports_citations = EXCLUDED.supports_citations,
    supports_grounding = EXCLUDED.supports_grounding,
    status = EXCLUDED.status,
    updated_at = now();
```

### Application Composition

目前 GEO Analysis API 的呼叫路徑：

```text
routes -> application use case -> GeoAnalysisRepository port -> infrastructure adapter
```

- `apps/geo-analysis-api/.../routes.py`：保留 HTTP API contract、Problem Details 與 DTO/response mapping。
- `packages/younilab-seo/.../geo_analysis/application/use_cases/`：依 workflow 分檔放置 application use cases，例如 `setup.py`、`jobs.py`、`dispatch.py`。
- `packages/younilab-seo/.../geo_analysis/application/contracts.py`：定義 application command/result records，避免 API DTO 或 untyped dict 穿越 application boundary。
- `packages/younilab-seo/.../geo_analysis/application/interfaces.py`：定義 `GeoAnalysisRepository` port。
- `packages/younilab-seo/.../geo_analysis/infrastructure/persistence/postgres/repository.py`：實作 PostgreSQL adapter，負責 SQLModel row 與 application/domain model 互轉。
- `packages/younilab-seo/.../geo_analysis/infrastructure/messaging/rabbitmq.py`：實作 RabbitMQ publisher adapter，依 provider 發布到不同 queue。
- `apps/geo-analysis-worker`：消費 provider queue，呼叫 `geo-tracking-api` `/api/v1/geo-tracking/run-requests`，並只回寫 job status/evidence。
- `apps/geo-analysis-api/.../store.py`：僅作為 API tests 與本機 stub 用的 in-memory fake repository。

已移除舊的 `PostgresGeoApiStore` presentation adapter；正式 runtime 直接由 composition 建立 `PostgresGeoAnalysisRepository` 後注入 use cases。

### Future Service Standard

GEO Analysis 目前作為後續服務重構的標準樣板：

```text
apps/{service-api}/src/{service_package}/presentation/http/
  app_factory.py
  composition.py
  routes.py 或 routes/
  dtos.py
  errors.py

packages/younilab-seo/src/younilab_seo/{bounded_context}/
  domain/
  application/
    contracts.py
    interfaces.py
    use_cases/
      __init__.py
      {workflow}.py
  infrastructure/
    persistence/
```

- Routes 不直接使用 repository、SQL session、id generator、queue client 或 provider SDK。
- `composition.py` 是 runtime dependency 組裝入口，並將 application use cases 掛到 `app.state`。
- Application use cases 只依賴 application contracts、domain model 與 application ports。
- Infrastructure adapters 實作 application ports，並負責 row / external payload / SDK object 與 application model 的轉換。
- API tests 使用 fake repository 或 fake port 注入 `create_app()`，不連正式 PostgreSQL 或外部服務。

## 前端介接共通規則

- JSON 欄位使用 `camelCase`。
- 未設定 `GEO_ANALYSIS_DATABASE_URL` 時會使用 in-memory store。
- `customerId` 與 `seoTaskId` 都是 `resource-catalog` 的 reference id，不在 GEO DB 建 FK。兩者皆空、只有 `customerId`、或兩者都有都允許；只有 `seoTaskId` 沒有 `customerId` 會回 `422`。
- `POST /api/geo/jobs/{jobId}/dispatch` 未設定 publisher 時會回 `501`；設定 RabbitMQ publisher 後會將 job 發布到 provider queue。Project 缺少 `seoTaskId` 時會回 `409`，避免 worker 無法呼叫 `geo-tracking-api`。
- `PATCH /api/geo/query-drafts/{draftId}/selection` 只允許尚未 accepted 的 draft；已接受成正式 query 的 draft 再次修改 selection 會回 `409`。
- `cancel` 與 external callback 已可透過 store abstraction 套用到 in-memory 或 PostgreSQL-backed repository。
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

## API 一覽

| Method | Path | 作用 |
| --- | --- | --- |
| `GET` | `/api/geo/integrations/kmindhub/workspace` | 取得目前 tenant 綁定的 KMindHub workspace mapping；未設定回 `404`。 |
| `PUT` | `/api/geo/integrations/kmindhub/workspace` | 手動綁定既有 KMindHub workspace。 |
| `POST` | `/api/geo/integrations/kmindhub/workspace/provision` | 明確建立 KMindHub workspace 並保存 tenant mapping。 |
| `GET` | `/api/geo/projects` | 列出 GEO project，可用 `customerId` 篩選。 |
| `POST` | `/api/geo/projects` | 建立客戶的 GEO project。 |
| `GET` | `/api/geo/projects/{projectId}` | 取得單一 GEO project。 |
| `PATCH` | `/api/geo/projects/{projectId}` | 更新 GEO project 基礎設定。 |
| `DELETE` | `/api/geo/projects/{projectId}` | 刪除 GEO project。PostgreSQL 模式會連動刪除 GEO 子資料。 |
| `GET` | `/api/geo/projects/{projectId}/markets` | 列出 project 的地區與語言市場設定。 |
| `POST` | `/api/geo/projects/{projectId}/markets` | 建立 market locale 與 SERP 參數提示。 |
| `PATCH` | `/api/geo/markets/{marketId}` | 更新 market 設定。 |
| `DELETE` | `/api/geo/markets/{marketId}` | 刪除 market 設定。 |
| `GET` | `/api/geo/projects/{projectId}/entities` | 列出 project 追蹤的品牌、競品或其他 entity。 |
| `POST` | `/api/geo/projects/{projectId}/entities` | 建立 tracked entity。 |
| `GET` | `/api/geo/entities/{entityId}` | 取得單一 tracked entity。 |
| `PATCH` | `/api/geo/entities/{entityId}` | 更新 tracked entity。 |
| `DELETE` | `/api/geo/entities/{entityId}` | 刪除 tracked entity。 |
| `GET` | `/api/geo/entities/{entityId}/aliases` | 列出 entity alias，供 runner 或分析模組參考。 |
| `POST` | `/api/geo/entities/{entityId}/aliases` | 建立 entity alias。 |
| `PATCH` | `/api/geo/entity-aliases/{aliasId}` | 更新 entity alias。 |
| `DELETE` | `/api/geo/entity-aliases/{aliasId}` | 刪除 entity alias。 |
| `GET` | `/api/geo/projects/{projectId}/topics` | 列出 project 的 query topic。 |
| `POST` | `/api/geo/projects/{projectId}/topics` | 建立 query topic。 |
| `PATCH` | `/api/geo/topics/{topicId}` | 更新 query topic。 |
| `DELETE` | `/api/geo/topics/{topicId}` | 刪除 query topic。 |
| `GET` | `/api/geo/projects/{projectId}/queries` | 列出 project 追蹤的自然語言 query。 |
| `POST` | `/api/geo/projects/{projectId}/queries` | 建立 tracked query。 |
| `GET` | `/api/geo/queries/{queryId}` | 取得單一 tracked query。 |
| `PATCH` | `/api/geo/queries/{queryId}` | 更新 tracked query。 |
| `DELETE` | `/api/geo/queries/{queryId}` | 刪除 tracked query。 |
| `POST` | `/api/geo/projects/{projectId}/query-research-runs` | 呼叫 `geo-tracking-api` Query Research 並保存 research context、searched keywords、source URLs。 |
| `GET` | `/api/geo/projects/{projectId}/query-research-runs` | 列出 project 的 Query Research runs。 |
| `GET` | `/api/geo/query-research-runs/{runId}` | 取得單一 Query Research run detail。 |
| `POST` | `/api/geo/projects/{projectId}/query-generation-runs` | 呼叫 `geo-tracking-api` Query Generation 並保存 generated query drafts。 |
| `GET` | `/api/geo/projects/{projectId}/query-generation-runs` | 列出 project 的 Query Generation runs。 |
| `GET` | `/api/geo/query-generation-runs/{runId}` | 取得單一 Query Generation run 與 drafts。 |
| `PATCH` | `/api/geo/query-drafts/{draftId}/selection` | 將 draft 標記為 `shortlisted` 或 `rejected`。 |
| `POST` | `/api/geo/query-drafts/{draftId}/accept` | 將 draft 轉成正式 `geo_query`，回傳既有 `QueryResponse`。 |
| `GET` | `/api/geo/queries/{queryId}/platforms` | 列出 query 要派送的平台設定。 |
| `PUT` | `/api/geo/queries/{queryId}/platforms` | 整批替換 query platform assignment。 |
| `GET` | `/api/geo/queries/{queryId}/schedules` | 列出 query 的週期排程設定。 |
| `POST` | `/api/geo/queries/{queryId}/schedules` | 建立 query/platform 的週期排程。 |
| `PATCH` | `/api/geo/schedules/{scheduleId}` | 更新排程設定。 |
| `DELETE` | `/api/geo/schedules/{scheduleId}` | 刪除排程設定。 |
| `POST` | `/api/geo/queries/{queryId}/jobs` | 建立手動 query run job。 |
| `GET` | `/api/geo/projects/{projectId}/jobs` | 列出 project 的 query run jobs。 |
| `GET` | `/api/geo/projects/{projectId}/run-results` | 列出 project 的 run history raw results。 |
| `GET` | `/api/geo/jobs/{jobId}` | 取得單一 job orchestration 狀態。 |
| `GET` | `/api/geo/jobs/{jobId}/run-results` | 列出單一 job 的 raw results。 |
| `GET` | `/api/geo/run-results/{resultId}` | 取得 run result detail，包含 raw response 與 references。 |
| `POST` | `/api/geo/run-results/{resultId}/analysis-extractions` | 手動重跑或補跑 KMindHub analysis extraction，成功後回傳更新後的 run result analysis 狀態。 |
| `POST` | `/api/geo/jobs/{jobId}/dispatch` | 派送 job 到 message broker。未設定 publisher 時回 `501`；RabbitMQ 啟用後依 provider 發布到 `geo.query-runs.{provider}`。 |
| `POST` | `/api/geo/jobs/{jobId}/cancel` | 取消尚未進入 terminal state 的 job。 |
| `POST` | `/api/geo/jobs/{jobId}/external-callbacks` | 接收外部 runner 狀態 callback，不接收 AI result content。 |
| `GET` | `/health` | 健康檢查。 |

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
  "customerId": "uuid 或 null",
  "seoTaskId": "uuid 或 null",
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

`seoTaskId` 語意上屬於某個 customer，因此不能單獨存在。GEO 不跨服務驗證 reference 是否存在；前端若要顯示 customer/task 名稱，需另外呼叫 Resource Catalog。

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
  "marketType": "b2b_procurement",
  "intent": "commercial",
  "buyerStage": "supplier_evaluation",
  "isBranded": false,
  "priority": "normal",
  "status": "active",
  "metadata": {}
}
```

`marketType` 目前支援 `b2c` 與 `b2b_procurement`。未提供時會使用 `b2b_procurement`，供舊 client 相容。

## Query Research / Generation

這組 API 用於前端 Query Research 頁面，採同步呼叫 `geo-tracking-api` 並保存結果。`google_aio` 只支援 run request，不可用於 research/generation provider。

| Method | Path | Request | Response |
| --- | --- | --- | --- |
| `POST` | `/api/geo/projects/{projectId}/query-research-runs` | `QueryResearchRunRequest` | `201 QueryResearchRunResponse` |
| `GET` | `/api/geo/projects/{projectId}/query-research-runs` | 無 | `PageResponse<QueryResearchRunResponse>` |
| `GET` | `/api/geo/query-research-runs/{runId}` | 無 | `QueryResearchRunResponse` |
| `POST` | `/api/geo/projects/{projectId}/query-generation-runs` | `QueryGenerationRunRequest` | `201 QueryGenerationRunResponse` |
| `GET` | `/api/geo/projects/{projectId}/query-generation-runs` | 無 | `PageResponse<QueryGenerationRunResponse>` |
| `GET` | `/api/geo/query-generation-runs/{runId}` | 無 | `QueryGenerationRunResponse` |
| `PATCH` | `/api/geo/query-drafts/{draftId}/selection` | `QueryDraftSelectionRequest` | `QueryDraftResponse` |
| `POST` | `/api/geo/query-drafts/{draftId}/accept` | `AcceptQueryDraftRequest` | `QueryResponse` |

```json
// QueryResearchRunRequest
{
  "provider": "gemini",
  "brandName": "Acme",
  "competitorBrands": ["Competitor"],
  "keywords": ["erp", "採購系統"],
  "region": "TW",
  "language": "zh-TW",
  "marketType": "b2b_procurement",
  "intents": [
    {
      "category": "commercial_investigation",
      "description": "比較供應商、產品方案或導入條件"
    }
  ],
  "audience": {
    "name": "B2B 採購",
    "description": "正在評估供應商的採購人員"
  },
  "brandMentionRules": {
    "shouldMentionOwnBrand": true,
    "shouldMentionCompetitor": true
  }
}

// QueryResearchRunResponse
{
  "id": "uuid",
  "projectId": "uuid",
  "provider": "gemini",
  "status": "completed",
  "requestPayload": {},
  "result": {
    "researchContext": "市場研究摘要",
    "searchedKeywords": ["erp"],
    "sourceUrls": ["https://example.com/source"]
  },
  "errorCode": null,
  "errorMessage": null,
  "createdAt": "2026-06-27T10:00:00Z",
  "completedAt": "2026-06-27T10:00:00Z"
}
```

```json
// QueryGenerationRunRequest
{
  "seoTaskId": "uuid",
  "provider": "gemini",
  "brandName": "Acme",
  "competitorBrands": ["Competitor"],
  "keywords": ["erp"],
  "region": "TW",
  "language": "zh-TW",
  "marketType": "b2b_procurement",
  "topicNames": ["ERP 導入"],
  "intents": [
    {
      "category": "commercial",
      "description": "比較供應商"
    }
  ],
  "audience": {
    "name": "B2B 採購",
    "description": "正在評估供應商的採購人員"
  },
  "brandMentionRules": {
    "shouldMentionOwnBrand": true,
    "shouldMentionCompetitor": false
  },
  "researchContext": "可選，來自 Query Research result",
  "maxQueries": 12
}

// QueryGenerationRunResponse
{
  "id": "uuid",
  "projectId": "uuid",
  "provider": "gemini",
  "status": "completed",
  "requestPayload": {},
  "errorCode": null,
  "errorMessage": null,
  "createdAt": "2026-06-27T10:00:00Z",
  "completedAt": "2026-06-27T10:00:00Z",
  "drafts": [
    {
      "id": "uuid",
      "generationRunId": "uuid",
      "projectId": "uuid",
      "topicId": null,
      "topicName": "ERP 導入",
      "queryText": "Acme ERP 適合哪些 B2B 採購情境?",
      "keywords": ["erp"],
      "region": "TW",
      "language": "zh-TW",
      "marketType": "b2b_procurement",
      "intent": "commercial",
      "isBranded": true,
      "status": "draft",
      "selectionStatus": null,
      "acceptedQueryId": null,
      "metadata": {},
      "createdAt": "2026-06-27T10:00:00Z",
      "updatedAt": "2026-06-27T10:00:00Z"
    }
  ]
}
```

```json
// QueryDraftSelectionRequest
{
  "selectionStatus": "shortlisted"
}

// AcceptQueryDraftRequest
{
  "createTopicIfMissing": true,
  "status": "active"
}
```

`accept` 會將 draft 轉成正式 `geo_query`。若 draft 只有 `topicName` 而沒有 `topicId`，且 `createTopicIfMissing=true`，API 會在同 project 找同名 topic；找不到時建立 topic 後再建立 query。Accept 不會自動建立 platform、schedule 或 job。

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
| `POST` | `/api/geo/jobs/{jobId}/dispatch` | 無 | `JobResponse`；未設定 publisher 時回 `501` |
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

