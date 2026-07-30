# GEO Analysis API

GEO Analysis API 提供 GEO 專案設定、market、entity、topic、query、platform assignment、query run job orchestration 與 report metrics endpoint。實際 AI 跑題由 `geo-tracking-api` 負責；每日 job 由 `geo-analysis-scheduler` 在固定時間建立，本服務負責內部 manual dispatch、job orchestration、worker 回寫的 raw result / references 保存，以及透過 application use case 讀取已正規化 facts 計算報表指標。

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
- `customerId` 是 nullable reference-only 欄位，不建立跨服務 DB FK；建立或更新 project 時會透過 Resource Catalog 驗證 reference 屬於同 tenant。每日排程流程不再使用 `seoTaskId`。
- Persistence 已支援 GEO setup CRUD、query-platform 相容資源、daily batch、不可變 job snapshot、dispatch evidence 與 external callback reference。Daily scheduler 直接使用 active Query × active Platform，不讀取 query-platform assignment。
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

## Project 列表與 Query Settings

`GET /api/geo/projects` 預設回傳目前 token 在 tenant 與 resource grants 範圍內可存取的全部 Projects。`customerId` 是選用篩選，不是列表必要參數；傳入無權存取的 customer 不會擴大授權範圍。

```http
GET /api/geo/projects
GET /api/geo/projects?customerId=00000000-0000-4000-8000-000000000001
Authorization: Bearer <access-token>
```

```ts
interface GeoProjectSummary {
  id: string;
  tenantId: string;
  customerId: string | null;
  customerName: string | null;
  name: string;
  defaultRegion: string;
  defaultLanguage: string;
  status: string;
  dailyRunBudget: number;
  ownBrand: null | {
    entityId: string;
    websiteUrl: string | null;
    aliases: string[];
  };
  createdAt: string;
  updatedAt: string;
}

const response = await fetch("/api/geo/projects", {
  headers: { Authorization: `Bearer ${accessToken}` },
});
const page: { items: GeoProjectSummary[]; total: number } = await response.json();
```

`customerName` 由 Resource Catalog 批次補值；Catalog 拒絕存取或暫時無法使用時仍回 `200`，欄位為 `null` 並記錄 warning。`ownBrand` 不存在時為 `null`，aliases 永遠為陣列。異常存在多筆 own-brand 時優先選 active，再取 `updatedAt` 最新者。

### Project 上下架狀態

Project 上下架使用獨立 status subresource，不需重送完整 Project：

```http
PATCH /api/geo/projects/{projectId}/status
Authorization: Bearer <access-token>
Content-Type: application/json

{
  "status": "paused"
}
```

response：

```json
{
  "projectId": "00000000-0000-4000-8000-000000000001",
  "status": "paused",
  "updatedAt": "2026-07-19T00:00:00Z"
}
```

- 僅接受 `active` 或 `paused`，未知欄位或其他狀態回 RFC 7807 `422`。
- 需要 `geo.projects.update`；不存在、跨 tenant 或超出 customer scope 一律回 `404`。
- `paused` Project 不會被每日排程選中；切回 `active` 後可參與後續排程。
- 狀態切換不刪除 Project 或子資源、不取消既有 jobs，也不觸發新的 Research、Generation、Query、Job 或 Schedule。
- 相同狀態重複 PATCH 不修改 `updatedAt`。

```ts
await fetch(`/api/geo/projects/${projectId}/status`, {
  method: "PATCH",
  headers: {
    Authorization: `Bearer ${accessToken}`,
    "Content-Type": "application/json",
  },
  body: JSON.stringify({ status: "paused" as "active" | "paused" }),
});
```

```http
GET /api/geo/projects/{projectId}/query-settings
PUT /api/geo/projects/{projectId}/query-settings
Authorization: Bearer <access-token>
Content-Type: application/json
```

```ts
interface GeoProjectQuerySettings {
  projectId: string;
  researchProvider: "gemini";
  runProvider: "gemini";
  keywords: string[];
  marketType: "b2c" | "b2b_procurement";
  maxQueries: number;
  audience: { name: string; description: string };
  intents: Array<{
    category: "navigational" | "informational" | "commercial_investigation" | "transactional";
    description: string;
  }>;
  shouldMentionOwnBrand: boolean;
  shouldMentionCompetitor: boolean;
  updatedAt: string;
}

const settings: Omit<GeoProjectQuerySettings, "projectId" | "updatedAt"> = {
  researchProvider: "gemini",
  runProvider: "gemini",
  keywords: ["ERP", "採購"],
  marketType: "b2b_procurement",
  maxQueries: 20,
  audience: { name: "採購主管", description: "負責供應商評估" },
  intents: [
    { category: "commercial_investigation", description: "比較供應商" },
    { category: "transactional", description: "尋找購買或洽詢方式" },
  ],
  shouldMentionOwnBrand: true,
  shouldMentionCompetitor: false,
};

await fetch(`/api/geo/projects/${projectId}/query-settings`, {
  method: "PUT",
  headers: {
    Authorization: `Bearer ${accessToken}`,
    "Content-Type": "application/json",
  },
  body: JSON.stringify(settings),
});
```

- 列表與 GET settings 需要 `geo.projects.read`；PUT settings 需要 `geo.projects.update`。
- 不存在、跨 tenant 或超出 customer scope 的 Project 一律回 RFC 7807 `404`。Settings 尚未建立時 GET 也回 `404`。
- PUT 是完整替換；相同正規化 payload 不更新 `updatedAt`，且不觸發 Research、Generation、Draft、Query、Job 或 Schedule。
- 未知欄位與驗證失敗回 RFC 7807 `422`，並在 `invalidParams` 提供欄位路徑。
- Provider 目前只允許 `gemini`；keywords 去空白、移除空值與不分大小寫重複值，最多 10 筆且每筆 200 字；`maxQueries` 為 1–40；`marketType` 只允許 `b2c`、`b2b_procurement`。
- 每個 Project 仍只保存一筆 Query Settings；多選 Intent 是該筆設定內的 `intents[]`，不是每個 Intent 各建立一筆設定。
- `intents` 必須選擇 1–4 個不重複的正式分類，`maxQueries` 不得少於所選分類數量。API 暫時接受舊版單一 `intent` request 並正規化，但 response 一律回傳 `intents[]`。
- 既有資料庫需手動執行 `deploy/local/postgresql/019_geo_project_query_settings.sql`；fresh schema 已同步更新 `004_geo_analysis_schema.sql`。
- 已套用舊版 Query Settings schema 的環境，需在部署新版 API 前執行 `deploy/local/postgresql/025_geo_project_query_settings_intents.sql`。
- Rollback 可先停止使用兩支 settings endpoint，再執行 `DROP TABLE geo_project_query_settings;`；這只移除 settings，不影響 Project、Entity、Alias、Topic、Query 或 runs。正式環境 rollback 前應先備份設定資料。
- 舊版前端未呼叫 settings API 時行為不變；列表既有欄位保持相容，只新增 `customerName` 與 `ownBrand`。

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

### Dashboard Report

Dashboard 報表由 `GetGeoDashboardReport` application use case 即時計算 read model，資料來源與 metrics endpoint 相同，都是已保存的 completed run results、semantic facts 與 citation normalization facts。API 不會在讀取 dashboard 時觸發 worker、重新分析或寫入 snapshot。

```http
GET /api/geo/projects/{projectId}/reports/dashboard?periodStart=2026-06-24T00:00:00Z&periodEnd=2026-06-26T00:00:00Z&comparisonStart=2026-06-22T00:00:00Z&comparisonEnd=2026-06-24T00:00:00Z
Authorization: Bearer <access-token>
```

可選 query parameters 與 `/metrics` 相同：

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
  "overview": [
    {
      "metricName": "visibility",
      "label": "Visibility",
      "metric": {
        "value": 100,
        "unit": "percent",
        "numerator": 1,
        "denominator": 1,
        "comparisonValue": 0,
        "delta": 100,
        "deltaUnit": "pp"
      }
    }
  ],
  "entities": [],
  "citationUrls": [],
  "citationDomains": [],
  "sentiments": []
}
```

### GEO Overview Report

正式 Admin Portal Overview 使用獨立 read models，不修改上述 Dashboard Report 沙盒 contract。兩支 endpoint 都只讀取已保存資料，不會觸發跑題或 semantic extraction。

```http
GET /api/geo/projects/{projectId}/reports/overview?periodStart=2026-07-01T00:00:00Z&periodEnd=2026-07-08T00:00:00Z&topicIds=<uuid>&providers=gemini&region=TW&metadataIndustry=保健&metadataType=品牌提及&timeZone=Asia/Taipei
GET /api/geo/projects/{projectId}/reports/overview/responses?periodStart=2026-07-01T00:00:00Z&periodEnd=2026-07-08T00:00:00Z&mentionStatus=all&page=1&pageSize=20
Authorization: Bearer <access-token>
```

- `topicIds`、`providers`、`metadataIndustry`、`metadataType` 可重複傳入；同一維度採 OR，不同維度採 AND。
- 比較期間自動使用目前區間之前的等長期間。
- `timeZone` 用於每日趨勢分組，預設 `Asia/Taipei`。
- Overview report 的 `isPreparing` 會檢查該 Project 在台北當日是否仍有 `pending`、`publishing`、`published`、`running_external` 或 `delayed` 的 daily-slot owner Job；`succeeded`、`failed`、`cancelled` 不計入。
- `mentionStatus` 支援 `all`、`mentioned`、`not_mentioned`。Semantic analysis 尚未完成或失敗時 `mentioned=null`，只會出現在 `all`。
- Report read model 會在 persistence adapter 套用 tenant、期間、Topic、Provider、地區與 metadata 條件，再把 normalized facts 交給既有純 calculator。
- Response read model 會先完成相同篩選與品牌提及狀態判斷，再於資料庫計算 total、排序及 offset pagination；只載入當頁的 reference 與 `own_brand` positive／negative sentiment 計數。
- Entity SOV 為該 entity mentions 除以全部自有品牌與競品 mentions。
- 引用回答比例為至少有一筆 citation 的 completed 回答數除以 completed 回答總數。
- 產業均值、citation content tag、citation page 品牌與競品提及目前沒有資料來源，response 會使用 `null`，前端顯示「尚無資料」或「未分析」。
- 既有資料庫部署前建議執行 `deploy/local/postgresql/024_geo_query_run_job_preparation_lookup.sql`，為 `isPreparing` 的 Project／台北日期查詢建立 partial index；缺少此索引不改變 API 結果，但 Job 資料量增加後會影響 Overview 查詢效能。

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
    'paused',
    now(),
    now()
),
(
    '11111111-1111-4111-8111-111111111102',
    'gemini',
    'Gemini',
    'llm_api',
    'gemini-3.1-flash-lite',
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
    'paused',
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
    'paused',
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
    'paused',
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

`geo_ai_platform.default_model` 是平台顯示與 dispatch evidence 使用的模型快照，
不提供 query-level override。Gemini 實際執行模型由 Geo Tracking deployment 的
`GEMINI_MODEL` 決定；部署時兩者必須維持一致。

### Application Composition

目前 GEO Analysis API 的呼叫路徑：

```text
routes -> application use case -> workflow persistence port -> infrastructure adapter
```

- `apps/geo-analysis-api/.../routes.py`：保留 HTTP API contract、Problem Details 與 DTO/response mapping。
- `packages/younilab-seo/.../geo_analysis/application/use_cases/`：依 workflow 分檔放置 application use cases，例如 `setup.py`、`jobs.py`、`dispatch.py`。
- `packages/younilab-seo/.../geo_analysis/application/contracts.py`：定義 application command/result records，避免 API DTO 或 untyped dict 穿越 application boundary。
- `packages/younilab-seo/.../geo_analysis/application/interfaces/`：依 workflow 定義 persistence ports。閱讀 use case 時，只需要打開同名或相鄰的 interface module。
- `packages/younilab-seo/.../geo_analysis/infrastructure/persistence/postgres/repository.py`：實作 PostgreSQL adapter，負責 SQLModel row 與 application/domain model 互轉。
- `packages/younilab-seo/.../geo_analysis/infrastructure/messaging/rabbitmq.py`：實作 RabbitMQ publisher adapter，依 provider 發布到不同 queue。
- `apps/geo-analysis-worker`：消費 provider queue，呼叫 `geo-tracking-api` `/api/v1/geo-tracking/run-requests`，並只回寫 job status/evidence。
- `apps/geo-analysis-api/.../store.py`：作為 API tests 與本機 stub 用的 in-memory adapter。

已移除 application layer 的 `GeoAnalysisRepository` 大型 façade。正式 runtime 仍建立一個 `PostgresGeoAnalysisRepository`，本機模式仍建立一個 `GeoApiStore`，但 `composition.py` 會把同一個 adapter 明確注入各 workflow port。這樣可重用同一個 session/state kernel，同時避免 use case 看見不相關的 persistence 方法。

目前主要 persistence ports：

- `semantic_analysis.py`：Semantic Analysis context、entity detection 與 analysis 保存。
- `citation_normalization.py`：Citation context、既有 normalization 與 facts 保存。
- `metrics.py`：通用 Metrics formula source。
- `overview_read.py`：`OverviewReportReadModel` 與 `OverviewResponseReadModel`，分別提供報表來源及已分頁回答清單。
- `run_lifecycle.py`：Dispatch、callback、execution、result read、job management 與 scheduler。
- `query_planning.py`：Research、Generation、draft selection 與 draft acceptance。
- `project_setup.py`、`entity_catalog.py`、`query_catalog.py`：Project/Market/Settings、Entity/Alias、Topic/Query/Platform/Schedule。
- `kmindhub_mapping.py`：Workspace mapping、task mapping 與 legacy extraction persistence。

完整決策與取捨見：

- `docs/architecture/geo-tracking/adr/0004-use-workflow-specific-persistence-ports.md`
- `docs/architecture/geo-tracking/adr/0005-use-dedicated-overview-read-models.md`

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
    interfaces/
      __init__.py
      {workflow}.py
    use_cases/
      __init__.py
      {workflow}.py
  infrastructure/
    persistence/
```

- Routes 不直接使用 repository、SQL session、id generator、queue client 或 provider SDK。
- `composition.py` 是 runtime dependency 組裝入口，並將 application use cases 掛到 `app.state`。
- Application use cases 只依賴 application contracts、domain model 與完成該 workflow 所需的最小 application port。
- Persistence port 依 workflow 設計，不依資料表設計；跨表 context load、tenant scope、claim 與原子保存由 adapter 隱藏。
- Infrastructure adapters 實作 application ports，並負責 row / external payload / SDK object 與 application model 的轉換。
- Application tests 優先使用只實作該 workflow port 的小型 fake；API tests 可注入共用 in-memory adapter，不連正式 PostgreSQL 或外部服務。

## 前端介接共通規則

- JSON 欄位使用 `camelCase`。
- 未設定 `GEO_ANALYSIS_DATABASE_URL` 時會使用 in-memory store。
- `customerId` 是 `resource-catalog` 的 nullable reference id，不在 GEO DB 建 FK。舊版 request 的 `seoTaskId` 暫時接受但會忽略，且不會出現在 response。
- `POST /api/geo/jobs/{jobId}/dispatch` 未設定 publisher 時會回 `501`；設定 RabbitMQ publisher 後會將 job 發布到 provider queue，流程不依賴 `seoTaskId`。
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
| `PUT` | `/api/geo/entities/{entityId}/aliases` | 原子替換 entity 的全部 aliases。 |
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
| `GET` | `/api/geo/platforms` | 列出資料庫中的 GEO AI Platform、預設 model 與 active/paused 狀態。 |
| `GET` | `/api/geo/queries/{queryId}/platforms` | 舊版 query-platform 相容資源，不影響 daily scheduler。 |
| `PUT` | `/api/geo/queries/{queryId}/platforms` | 整批替換舊版 query-platform 相容資源。 |
| `GET` | `/api/geo/queries/{queryId}/schedules` | 舊版 schedule 相容 endpoint。 |
| `POST` | `/api/geo/queries/{queryId}/schedules` | 舊版 schedule 相容 endpoint。 |
| `PATCH` | `/api/geo/schedules/{scheduleId}` | 舊版 schedule 相容 endpoint。 |
| `DELETE` | `/api/geo/schedules/{scheduleId}` | 舊版 schedule 相容 endpoint。 |
| `POST` | `/api/geo/queries/{queryId}/jobs` | 建立手動 query run job；同一 Query、Platform 與台北營業日只建立一次。 |
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

過渡期間若舊版 client 傳入 `seoTaskId`，API 會接受並忽略；新 client 不應再傳送此欄位。

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
| `GET` | `/api/geo/entities/{entityId}/aliases` | 無 | `AliasCollectionResponse` |
| `PUT` | `/api/geo/entities/{entityId}/aliases` | `AliasCollectionRequest` | `200 AliasCollectionResponse` |

```json
// EntityRequest
{
  "entityType": "brand",
  "name": "Acme",
  "websiteUrl": "https://example.com",
  "description": "主要品牌",
  "status": "active"
}

// AliasCollectionRequest
{
  "items": [
    {
      "alias": "Acme Inc.",
      "matchType": "exact"
    },
    {
      "alias": "Acme Taiwan",
      "matchType": "contains"
    }
  ]
}
```

Alias PUT 採完整替換並在單一 transaction 內完成。空 `items` 會刪除該 Entity
的全部別名；未變更項目保留原本的 `id` 與 `createdAt`。Alias 會去除前後
空白，完全相同的值不可重複，但大小寫不同仍視為不同值。Entity 不存在或
不在目前 tenant／resource grants 範圍時回 `404`，欄位驗證失敗回 RFC 7807
`422`。trim 與重複驗證只套用於 PUT request；GET 會原樣回傳既有持久化值，
避免舊資料在讀取時被靜默改寫。

```ts
interface GeoEntityAliasInput {
  alias: string;
  matchType: "exact" | "contains" | "domain";
}

interface GeoEntityAliasCollectionRequest {
  items: GeoEntityAliasInput[];
}

interface GeoEntityAliasResource extends GeoEntityAliasInput {
  id: string;
  entityId: string;
  createdAt: string;
}

interface GeoEntityAliasCollectionResponse {
  items: GeoEntityAliasResource[];
  total: number;
}

const response = await fetch(`/api/geo/entities/${entityId}/aliases`, {
  method: "PUT",
  headers: {
    Authorization: `Bearer ${accessToken}`,
    "Content-Type": "application/json",
  },
  body: JSON.stringify({
    items: aliases.map((alias) => ({ alias, matchType: "exact" })),
  } satisfies GeoEntityAliasCollectionRequest),
});
```

`GET` 需要 `geo.projects.read`，`PUT` 需要 `geo.projects.update`。本版已移除
舊版單筆 `POST /entities/{entityId}/aliases` 與
`PATCH／DELETE /entity-aliases/{aliasId}`，屬破壞性契約變更；Admin Portal 與
GEO Analysis API 必須在同一發布批次部署，舊瀏覽器頁面需重新整理後再操作。

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
| `POST` | `/api/geo/queries/{queryId}/jobs` | `CreateJobRequest` | 新建時 `201 CreateJobResponse`；當日已存在時 `200 CreateJobResponse` |
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

// CreateJobResponse；一般 JobResponse 不包含 wasCreated
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
  "updatedAt": "2026-06-22T10:00:00Z",
  "wasCreated": true
}
```

Job status 目前由 orchestration 控制，常見值包含 `pending`、`publishing`、`published`、`running_external`、`succeeded`、`failed`、`delayed`、`cancelled`。已進入 `succeeded`、`failed`、`cancelled` 的 job 不接受 external callback 改寫，也不可再次 cancel。

Job 建立以 `Query + Platform + businessDate` 占用每日執行額度，`businessDate` 固定由 `scheduledFor` 換算為 `Asia/Taipei` 日期。當日已有 Job 時回傳同一筆 Job 與 `wasCreated: false`，不得建立替代 Job。若既有 Job 已是 `query_research_first_run + pending`，呼叫端可 dispatch 同一個 `jobId`；`delayed` 應等待 scheduler 到期重試，其他狀態視為已執行或已排程。Job 即使進入 `failed`、`cancelled` 或 `delayed` 仍占用當日額度，後續只能沿用原 Job 的 retry／reconciliation。

`jobType=query_research_first_run` 專供 Query Research 建立後的首次執行。若 daily slot 已由 `source=manual`、`jobType=manual_run` 且狀態為 `pending`／`delayed` 的 Job 占用，first-run create request 會鎖定並將同一筆 Job 升級為 `query_research_first_run`，回傳 `wasCreated: false`；scheduled 與 terminal Job 不會被改寫。scheduler 會接手 first-run Job 的到期 `pending`／`delayed` 狀態，一般 `manual_run` 不會自動派送。前端 dispatch 回應遺失或 publisher 暫時失敗時，後端仍會沿用同一筆 Job 重試。

既有資料庫不可在舊版 API 或 scheduler writers 仍運作時直接套用 `deploy/local/postgresql/020_geo_query_daily_run_uniqueness.sql`。安全部署需進入維護窗口，先停止 Admin Portal 即時執行、GEO API create-job 流量與 scheduler，確認沒有 Job writer 後執行 migration，再部署新版 GEO API／scheduler；完成 create-job conflict 與 first-run pickup smoke test 後才恢復 writers，最後部署 Admin Portal。Migration 會保留歷史重複資料，只將每組最早 Job 設為 daily slot owner；fresh schema 已同步。

安全 rollback 應先回退 Admin Portal 的即時執行功能，並保留 migration、每日唯一索引、create-job conflict handling 與 scheduler 相容程式。若只回退 scheduler 行為，可停止撿取 `query_research_first_run`，但不可回退 create-job conflict handling。若必須完整回退後端，需先停止 API 與 scheduler writers，再以受控 migration 移除 `ux_geo_query_run_job_daily_slot`、`business_date` 與 `is_daily_slot_owner`，最後才部署舊 API／scheduler；完整回退會恢復同日重複 Job 的風險。不可將舊版 API 與新版每日唯一索引併用，否則同日重複建立會因未處理的唯一衝突回 500。

## Health

| Method | Path | Auth | Response |
| --- | --- | --- | --- |
| `GET` | `/health` | 不需 Bearer | `{ "status": "ok" }` |

