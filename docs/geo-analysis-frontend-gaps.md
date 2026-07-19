# GEO Analysis 前端缺口紀錄

本文記錄 `apps/admin-portal` GEO 分析頁切板與 API 串接時，前端已先以示意資料或補值處理的缺口。

## 缺少 API

- 平台總表 API：目前沒有 `GET /api/geo/platforms`，前端暫用 `apps/geo-analysis-api/README.md` 建議 seed 的平台 UUID 與顯示名稱。
- Project-level schedules API：目前只有 `GET /api/geo/queries/{queryId}/schedules`，前端需逐一查詢 query 後聚合。
- 報表 KPI API：Visibility、SOV、Mentions、Citations、Used URL、Share 等彙總尚未提供。
- 趨勢 API：Overview 的 visibility / SOV / mentions time series 尚未提供。
- Topic performance API：topic-level visibility、SOV、query count、best platform 尚未提供。
- Recommendation API：GEO optimization recommendations 尚未提供。
- AI answer analysis API：answer summary、mentioned entities、citations、sentiment、theme、statement 等分析資料尚未提供。

## 缺少或需改善欄位

- 新增 Project 第二步的 Provider、Keywords、市場、受眾、Intent、最大 Query 數與品牌提及規則目前沒有 Project 層級保存 API。完整後端需求與建議契約見 [GEO Project Query Settings 後端需求](./geo-project-query-settings-backend-requirements.md)；API 完成前，前端只保留當次表單狀態並明確提示未保存。

- `GET /api/geo/projects` 只回 `customerId` / `seoTaskId`，前端需再呼叫 `/api/customers` 與 `/api/tasks` 補 `customerName` / `seoTaskName`。
- `GET /api/geo/projects/{projectId}/entities` 不包含 aliases，前端需逐一呼叫 `/api/geo/entities/{entityId}/aliases`。
- Query platform assignment 只包含 `platformId` / `model`，缺少 platform display name、provider code、status metadata。
- Job list 目前沒有 query text / platform display name denormalized 欄位，前端需用已載入的 query 與靜態 platform catalog 補顯示名稱。
- Run result references 已有 title / domain / position，但缺少 citation classification、是否引用品牌官網、是否命中 watched URL 等報表需要欄位。

## 前端目前處理方式

- 可用 API 已集中在 `api.geoAnalysis.*` 串接。
- 缺少報表與平台總表 API 的區塊會顯示「示意資料」提示。
- API 不可用時，GEO 分析頁會 fallback 到乾淨 mock data，並明確顯示目前未呼叫 API。
