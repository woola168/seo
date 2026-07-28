# GEO 封存文件

此目錄保存已完成、已被現行實作取代，或不再適合當作 source of truth 的 GEO 文件。內容主要用於追溯早期需求與設計背景；判斷目前行為時，請先閱讀 [`GEO Analysis 現況、架構與 Roadmap`](../../geo-analysis-current-state-and-roadmap.md)，再核對程式碼、migrations 與 runtime 設定。

`docs/architecture/geo-tracking/` 不在本次封存範圍，完整保留於原位置。

## `planning/`

| 文件 | 封存原因 |
| --- | --- |
| `geo-analysis-requirements.md` | 早期 Phase 1～3 產品需求已拆成已完成、部分完成與未完成項目；由新的整合文件維護目前狀態與 roadmap。 |
| `geo-analysis-workflow.md` | 文件仍描述 persistence、queue、worker、result pipeline 與 metrics 尚未實作，已與現況不符。 |
| `geo-analysis-frontend-gaps.md` | 多個曾列為缺少的 platforms、schedules、metrics、trend、topic performance 與 response analysis API 已存在。 |
| `geo-tracking-mvp-tracking.md` | 早期 A／B／C tracker 仍把 shortlist、persistence、queue 與 worker 列為未完成，已被正式 `geo-analysis` workflow 取代。 |
| `geo-analysis-schema.md` | 文件自稱規劃用途，且保留 queue 尚未決定等舊假設；目前 schema 以 `deploy/local/postgresql/*.sql` 與 Postgres models 為準。 |

## `completed/`

| 文件 | 封存原因 |
| --- | --- |
| `geo-project-query-settings-backend-requirements.md` | API、persistence、migration、OpenAPI、測試與新增 Project／Query Research 串接均已完成；未完成的 Project Edit UI 入口已併入新 roadmap。 |
