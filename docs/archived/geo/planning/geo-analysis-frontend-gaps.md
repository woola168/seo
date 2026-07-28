# GEO Analysis 前端缺口紀錄

> 已於 2026-07-27 封存。本文件保留早期前端串接缺口，多個 API 缺口已完成；請改讀 [GEO Analysis 現況、架構與 Roadmap](../../../geo-analysis-current-state-and-roadmap.md)。

> 狀態（2026-07-19）：Project summary、Project Query Settings 與 Project status 後端 API 已完成。前端已串接新增 Project Settings 保存、Query Search 預帶及 Projects 上下架；待辦為列表改用 summary，以及產品確認 Project Edit 的 Settings 編輯入口。其他報表與 denormalized 欄位缺口維持原狀。

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

- 新增 Project 第二步的 Provider、Keywords、市場、受眾、Intent、最大 Query 數與品牌提及規則已透過 Project Query Settings PUT 保存；Query Search 亦會 GET 預帶。完整契約見 [GEO Project Query Settings 後端需求](../completed/geo-project-query-settings-backend-requirements.md)。Project Edit 因新版參考稿未提供設定區塊，仍待產品設計確認。

- `GET /api/geo/projects` 已提供 nullable `customerName` 與 `ownBrand` aliases 聚合 read model；前端尚待移除 Project 列表的逐筆補值請求。
- Project Edit 的完整 competitors 與 aliases 仍沿用既有 entities／aliases CRUD；本次未新增 Project profile aggregate GET／PUT。
- 標準版 Projects 頁已改用 `PATCH /api/geo/projects/{projectId}/status` 上下架，只送出 `active`／`paused`；legacy `archived` 僅保留顯示與恢復上架相容性。
- Query platform assignment 只包含 `platformId` / `model`，缺少 platform display name、provider code、status metadata。
- Job list 目前沒有 query text / platform display name denormalized 欄位，前端需用已載入的 query 與靜態 platform catalog 補顯示名稱。
- Run result references 已有 title / domain / position，但缺少 citation classification、是否引用品牌官網、是否命中 watched URL 等報表需要欄位。

## 前端目前處理方式

- 可用 API 已集中在 `api.geoAnalysis.*` 串接。
- 缺少報表與平台總表 API 的區塊會顯示「示意資料」提示。
- API 不可用時，GEO 分析頁會 fallback 到乾淨 mock data，並明確顯示目前未呼叫 API。
